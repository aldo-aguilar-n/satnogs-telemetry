"""
Parsing pipeline for turning raw SatNOGS packets into parsed rows.

This includes:
- raw metadata extraction
- AX.25 address extraction
- CCSDS primary header parsing
- optional APID-based payload decoding using satnogs-decoders
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from typing import Any

from .config import AppConfig
from .models import DecoderSpec, ParsedPacket, SatelliteConfig
from .utils import (
    extract_ax25_and_ccsds,
    extract_raw_fields_for_indexing,
    flatten_dict,
    hex_to_bytes,
    parse_ccsds_primary_header,
)


class DecoderLoader:
    """
    Loader for APID-specific parser modules.

    Supports:
    - Python decoder modules (`type = "python"`)
    - Kaitai `.ksy` files compiled on demand (`type = "ksy"`)
    """

    def __init__(self, build_dir: str | Path = ".generated") -> None:
        self._module_cache: dict[str, Any] = {}
        self.build_dir = Path(build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def parse_with_decoder(self, spec: DecoderSpec, packet_hex: str) -> dict[str, Any]:
        """Decode a raw packet using the configured decoder spec."""
        data = hex_to_bytes(packet_hex)
        if spec.strip_ccsds_primary_header:
            if len(data) < 6:
                raise ValueError("Packet too short to strip CCSDS primary header")
            data = data[6:]

        module = self._load_module_for_spec(spec)
        parser_cls = getattr(module, spec.root_class, None)
        if parser_cls is None:
            raise AttributeError(f"Root class '{spec.root_class}' not found for decoder")

        obj = parser_cls.from_bytes(data)
        parsed = self._to_builtin(obj)

        # Flattening is handled downstream in the DB layer, but converting here
        # ensures parser outputs are normal built-in Python objects.
        _ = flatten_dict(parsed) if isinstance(parsed, dict) else None
        return parsed

    def _load_module_for_spec(self, spec: DecoderSpec):
        if spec.decoder_type == "python":
            if not spec.parser_path:
                raise ValueError("Python decoder spec requires parser_path")
            return self._load_module_from_path(spec.parser_path)

        if spec.decoder_type == "ksy":
            if not spec.ksy_path:
                raise ValueError("KSY decoder spec requires ksy_path")
            generated_py = self._compile_ksy_to_python(spec.ksy_path)
            return self._load_module_from_path(generated_py)

        raise ValueError(f"Unsupported decoder type: {spec.decoder_type}")

    def _compile_ksy_to_python(self, ksy_path: str) -> str:
        """
        Compile a Kaitai schema into Python code using `ksc`.

        The generated module is cached on disk under `.generated/`.
        """
        path = Path(ksy_path)
        if not path.exists():
            raise FileNotFoundError(f"KSY file not found: {path}")

        out_dir = self.build_dir / path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        generated_py = out_dir / f"{path.stem}.py"

        if generated_py.exists():
            return str(generated_py)

        cmd = ["ksc", "-t", "python", "-d", str(out_dir), str(path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Could not find 'ksc'. Install the Kaitai Struct compiler and make sure it is on PATH."
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"ksc failed for {path}: {exc.stderr}") from exc

        if not generated_py.exists():
            raise RuntimeError(f"Expected generated parser not found: {generated_py}")

        return str(generated_py)

    def _load_module_from_path(self, parser_path: str):
        if parser_path in self._module_cache:
            return self._module_cache[parser_path]

        path = Path(parser_path)
        if not path.exists():
            raise FileNotFoundError(f"Decoder file not found: {path}")

        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load decoder module from: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._module_cache[parser_path] = module
        return module

    def _to_builtin(self, value: Any, depth: int = 0) -> Any:
        """Convert parser objects recursively into built-in Python types."""
        if depth > 25:
            return str(value)

        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, bytes):
            return value.hex().upper()

        if isinstance(value, list):
            return [self._to_builtin(v, depth + 1) for v in value]

        if isinstance(value, tuple):
            return [self._to_builtin(v, depth + 1) for v in value]

        if isinstance(value, dict):
            return {str(k): self._to_builtin(v, depth + 1) for k, v in value.items()}

        result: dict[str, Any] = {}
        for attr in dir(value):
            if attr.startswith("_"):
                continue
            try:
                attr_value = getattr(value, attr)
            except Exception:
                continue
            if callable(attr_value):
                continue
            result[attr] = self._to_builtin(attr_value, depth + 1)

        return result


class PacketParser:
    """
    Converts one raw SatNOGS packet into one ParsedPacket.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.decoder_loader = DecoderLoader()

    def parse_raw_packet(
        self,
        raw_frame_id: int,
        norad_cat_id: int,
        raw_json: dict[str, Any],
    ) -> ParsedPacket:
        """
        Parse one full raw SatNOGS packet into a ParsedPacket.

        The decoder, if any, is chosen from config based on satellite metadata
        and then APID.
        """
        timestamp_utc, observer = extract_raw_fields_for_indexing(raw_json)

        frame = raw_json.get("frame")
        if frame is None:
            raise ValueError("Raw packet is missing 'frame'")

        frame_hex = str(frame).strip().upper()
        sat_cfg: SatelliteConfig | None = self.config.resolve_satellite_config(raw_json, norad_cat_id)

        if sat_cfg is not None and sat_cfg.frame_protocol != "ax25_ccsds":
            raise ValueError(f"Unsupported frame protocol: {sat_cfg.frame_protocol}")

        ax25 = extract_ax25_and_ccsds(frame_hex)
        ccsds = parse_ccsds_primary_header(ax25["raw_ccsds_packet_hex"])

        apid = ccsds["apid"]
        sequence_count = ccsds["sequence_count"]

        parsed_json: dict[str, Any] | None = None
        parser_path = ""
        parser_root_class = ""

        if sat_cfg is not None:
            decoder_spec = sat_cfg.apid_decoders.get(apid)
            if decoder_spec is not None:
                parser_path = decoder_spec.parser_path or decoder_spec.ksy_path
                parser_root_class = decoder_spec.root_class
                parsed_json = self.decoder_loader.parse_with_decoder(
                    spec=decoder_spec,
                    packet_hex=ax25["raw_ccsds_packet_hex"],
                )

        return ParsedPacket(
            raw_frame_id=raw_frame_id,
            norad_cat_id=norad_cat_id,
            timestamp_utc=timestamp_utc,
            observer=observer,
            dest_callsign=ax25["dest_callsign"],
            src_callsign=ax25["src_callsign"],
            raw_ax25_frame_hex=ax25["raw_ax25_frame_hex"],
            ccsds_apid=apid,
            ccsds_sequence_count=sequence_count,
            raw_ccsds_packet_hex=ax25["raw_ccsds_packet_hex"],
            parsed_json=parsed_json,
            parser_path=parser_path,
            parser_root_class=parser_root_class,
        )
