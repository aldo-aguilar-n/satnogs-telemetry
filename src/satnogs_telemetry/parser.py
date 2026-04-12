"""
Parsing pipeline for turning raw SatNOGS packets into parsed rows.

This includes:
- raw metadata extraction
- AX.25 address extraction
- CCSDS primary header parsing
- optional satellite-level payload decoding
- first-use compilation of .ksy decoders
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .config import AppConfig
from .decoder_manager import DecoderManager
from .models import ParsedPacket
from .utils import (
    extract_ax25_and_ccsds,
    extract_raw_fields_for_indexing,
    hex_to_bytes,
    parse_ccsds_primary_header,
)


class DecoderLoader:
    """
    Loader for compiled Python parser modules.
    """

    def __init__(self) -> None:
        self._module_cache: dict[str, Any] = {}

    def parse_with_decoder(
        self,
        parser_path: str,
        root_class: str,
        packet_hex: str,
    ) -> dict[str, Any]:
        module = self._load_module(parser_path)
        parser_cls = getattr(module, root_class, None)
        if parser_cls is None:
            raise AttributeError(f"Root class '{root_class}' not found in {parser_path}")

        obj = parser_cls.from_bytes(hex_to_bytes(packet_hex))
        return self._to_builtin(obj)

    def _load_module(self, parser_path: str):
        if parser_path in self._module_cache:
            return self._module_cache[parser_path]

        path = Path(parser_path)
        if not path.exists():
            raise FileNotFoundError(f"Compiled decoder file not found: {path}")

        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load decoder module from: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._module_cache[parser_path] = module
        return module

    def _to_builtin(self, value: Any, depth: int = 0) -> Any:
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
        self.decoder_manager = DecoderManager(config)

    def parse_raw_packet(
        self,
        raw_frame_id: int,
        norad_cat_id: int,
        raw_json: dict[str, Any],
    ) -> ParsedPacket:
        timestamp_utc, observer = extract_raw_fields_for_indexing(raw_json)

        frame = raw_json.get("frame")
        if frame is None:
            raise ValueError("Raw packet is missing 'frame'")

        frame_hex = str(frame).strip().upper()

        ax25 = extract_ax25_and_ccsds(frame_hex)
        ccsds = parse_ccsds_primary_header(ax25["raw_ccsds_packet_hex"])

        apid = ccsds["apid"]
        sequence_count = ccsds["sequence_count"]

        parsed_json: dict[str, Any] | None = None
        parser_path = ""
        parser_root_class = ""

        decoder_ref = self.decoder_manager.resolve_decoder(norad_cat_id)
        if decoder_ref is not None:
            compiled = self.decoder_manager.ensure_compiled(norad_cat_id, decoder_ref)
            parser_path = str(compiled.generated_py)
            parser_root_class = compiled.root_class

            full_ccsds_hex = ax25["raw_ccsds_packet_hex"]
            ccsds_payload_hex = full_ccsds_hex[12:] if len(full_ccsds_hex) >= 12 else ""

            # AX.25 information field = everything after destination/src/control/PID.
            # extract_ax25_and_ccsds already verified AX.25 enough to get the CCSDS packet,
            # so a simple fallback candidate here is CCSDS packet with the leading PID removed.
            # Since raw_ccsds_packet_hex already starts after PID, we also keep a copy of the
            # full AX.25 frame for debugging context.
            candidates: list[tuple[str, str]] = []

            if ccsds_payload_hex:
                candidates.append(("ccsds_payload", ccsds_payload_hex))
            if full_ccsds_hex:
                candidates.append(("full_ccsds", full_ccsds_hex))

            # Last resort: try the whole AX.25 frame in case the schema is more complete
            # than expected.
            candidates.append(("full_ax25_frame", ax25["raw_ax25_frame_hex"]))

            decode_errors: list[str] = []

            for mode, candidate_hex in candidates:
                try:
                    parsed_json = self.decoder_loader.parse_with_decoder(
                        parser_path=parser_path,
                        root_class=parser_root_class,
                        packet_hex=candidate_hex,
                    )

                    # Tag which candidate succeeded for debugging.
                    if isinstance(parsed_json, dict):
                        parsed_json["_decode_mode"] = mode
                    else:
                        parsed_json = {
                            "_decode_mode": mode,
                            "value": parsed_json,
                        }
                    break

                except Exception as exc:
                    decode_errors.append(f"{mode}: {type(exc).__name__}: {exc}")

            if parsed_json is None:
                parsed_json = {
                    "_decode_error": True,
                    "_parser_path": parser_path,
                    "_root_class": parser_root_class,
                    "_tried_modes": [mode for mode, _ in candidates],
                    "_errors": decode_errors,
                }

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