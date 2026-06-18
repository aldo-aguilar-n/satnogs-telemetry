"""
Title: decode.py
Authors: Aldo Aguilar
Date: 2026-06-17
Description: Decode and parser utilities for SatNOGS telemetry.

Functionalities
----------------
- Load decoder mapping from config.toml
- Prompt the user to choose a telemetry dictionary when needed
- Generate Python decoder from selected telemetry dictionary and cache 
  it locally
- Parse raw SatNOGS packets into AX.25 / CCSDS / decoded payload records
- Delete malformed raw rows during parse so they are not retried forever
"""

# System imports
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from typing import Any
from types import SimpleNamespace

# Third-party imports
import tomllib
try:
    import tomli_w
except ImportError:
    tomli_w = None

# Custom imports
from .generate_decoder import GENERATOR_VERSION, write_decoder_module

# Global path constants
CONFIG_PATH = Path("config.toml")
DECODER_SEARCH_ROOT = Path("ctdb")                                      # Command and telemetry database
DECODERS_DIR = Path("decoders")

# Deterministic malformed-frame errors. If one of these occurs, the raw
# row can safely be deleted because it will never become parseable.
MALFORMED_FRAME_ERRORS = (
    "AX.25 frame is too short",
    "AX.25 frame must contain destination and source addresses",
    "AX.25 frame ended before address section completed",
    "AX.25 frame has empty information field",
    "CCSDS packet is too short to contain a primary header",
)

# ---------------------------- Data classes ----------------------------

@dataclass(slots=True)
class DecoderRef:
    """
    Reference to a decoder source before generation.
    """
    source_path: Path

@dataclass(slots=True)
class GeneratedDecoder:
    """
    Reference to a generated Python decoder.
    """
    generated_py: Path
    buildinfo_path: Path

# ----------------------------- UTC Helper -----------------------------

def utc_now_iso() -> str:
    """
    Return the current UTC time in ISO-8601 format with trailing Z.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# -------------------------- Decoder Helpers ---------------------------

def load_decoder_mapping(config_path: Path = CONFIG_PATH) -> dict[int, dict[str, str]]:
    """
    Load the NORAD -> decoder mapping from config.toml.

    Expected format
    ---------------
    [satellites.68460.decoder]
    source_path = "ctdb/example_ctdb.xlsx"
    """
    if not config_path.exists():
        return {}

    with config_path.open("rb") as f:
        data = tomllib.load(f)

    satellites = data.get("satellites", {})
    result: dict[int, dict[str, str]] = {}

    for norad_str, sat_entry in satellites.items():
        try:
            norad = int(norad_str)
        except Exception:
            continue

        decoder = sat_entry.get("decoder")
        if not isinstance(decoder, dict):
            continue

        source_path = str(decoder.get("source_path", "")).strip()

        if source_path:
            result[norad] = {
                "source_path": source_path
            }

    return result

def save_decoder_mapping(norad_cat_id: int, 
                         source_path: str,
                         config_path: Path = CONFIG_PATH) -> None:
    """
    Save one NORAD -> decoder mapping into config.toml.
    """
    if config_path.exists():
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    else:
        data = {}

    satellites = data.setdefault("satellites", {})
    sat_entry = satellites.setdefault(str(norad_cat_id), {})
    sat_entry["decoder"] = {
        "source_path": source_path
    }

    if tomli_w is not None:
        with config_path.open("wb") as f:
            f.write(tomli_w.dumps(data).encode("utf-8"))
    else:
        lines: list[str] = []
        for norad, sat_entry in sorted(data.get("satellites", {}).items()):
            decoder = sat_entry.get("decoder", {})
            source_path = str(decoder.get("source_path", "")).replace("\\", "\\\\").replace("\"", "\\\"")
            if source_path:
                lines.append(f"[satellites.{norad}.decoder]")
                lines.append(f"source_path = \"{source_path}\"")
                lines.append("")
        config_path.write_text("\n".join(lines), encoding="utf-8")

def _scan_decoder_sources(search_root: Path = DECODER_SEARCH_ROOT) -> list[Path]:
    """
    Find candidate decoder database spreadsheets.
    """
    if not search_root.exists():
        return []

    candidates: list[Path] = []
    for pattern in ("*.xlsx", "*.xlsm"):
        candidates.extend(search_root.rglob(pattern))
    return sorted(path for path in candidates if not path.name.startswith("~$"))

def _repo_relative(path: Path) -> str:
    """
    Return a path relative to the current working directory when 
    possible.

    This keeps the interactive decoder list short and readable.
    """
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(path)

def prompt_for_decoder_choice(norad_cat_id: int) -> str:
    """
    Prompt the user to choose a decoder database for a satellite.
    """
    sources = _scan_decoder_sources()

    print(f"No decoder configured for NORAD {norad_cat_id}.")

    if sources:
        print("Select a decoder database:")
        for i, path in enumerate(sources, start=1):
            print(f"{i}) {_repo_relative(path)}")
        print("Or enter a decoder database path directly.")
    else:
        print(f"No decoder database files found under {DECODER_SEARCH_ROOT}.")

    while True:
        raw = input("Enter selection number or decoder database path: ").strip().strip('"')
        try:
            idx = int(raw)
            if 1 <= idx <= len(sources):
                return _repo_relative(sources[idx - 1])
        except Exception:
            pass

        if raw:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = (CONFIG_PATH.parent / path).resolve()
            if path.exists() and path.suffix.lower() in {".xlsx", ".xlsm"}:
                return _repo_relative(path)

        print("Invalid selection.")

# -------------------------- Decoder Manager ---------------------------

class DecoderManager:
    """
    Resolve, generate, and cache satellite decoders.
    """

    def __init__(self) -> None:
        DECODERS_DIR.mkdir(parents=True, exist_ok=True)
        self._generated_cache: dict[int, GeneratedDecoder] = {}

    def resolve_decoder(self, norad_cat_id: int) -> DecoderRef | None:
        """
        Resolve a decoder for a NORAD ID.

        If none is configured yet, prompt the user once and persist the 
        mapping.
        """
        mapping = load_decoder_mapping()
        decoder_info = mapping.get(norad_cat_id)

        if not decoder_info:
            rel_source_path = prompt_for_decoder_choice(norad_cat_id)
            save_decoder_mapping(
                norad_cat_id=norad_cat_id,
                source_path=rel_source_path
            )
            decoder_info = {
                "source_path": rel_source_path
            }

        source_path = Path(decoder_info["source_path"])
        if not source_path.is_absolute():
            # Resolve relative to config.toml / repo root so launching 
            # the app from a different directory does not break decoder
            # paths.
            source_path = (CONFIG_PATH.parent / source_path).resolve()

        if not source_path.exists():
            raise FileNotFoundError(f"Decoder source file not found: {source_path}")

        return DecoderRef(
            source_path=source_path
        )

    def ensure_generated(self, norad_cat_id: int, decoder: DecoderRef) -> GeneratedDecoder:
        """
        Generate a decoder if needed, otherwise reuse the cached version.

        This method first checks an in-memory cache for the current 
        process, then checks the on-disk build cache via .buildinfo.json.
        """
        cached = self._generated_cache.get(norad_cat_id)
        if cached is not None and cached.generated_py.exists() and cached.buildinfo_path.exists():
            return cached

        out_dir = (DECODERS_DIR / str(norad_cat_id)).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        generated_py = (out_dir / "decoder.py").resolve()
        buildinfo_path = (out_dir / ".buildinfo.json").resolve()

        if self._is_cache_valid(decoder, generated_py, buildinfo_path):
            generated = GeneratedDecoder(
                generated_py=generated_py,
                buildinfo_path=buildinfo_path,
            )
            self._generated_cache[norad_cat_id] = generated
            return generated

        write_decoder_module(decoder.source_path, generated_py)
        self._write_buildinfo(decoder, generated_py, buildinfo_path)

        generated = GeneratedDecoder(
            generated_py=generated_py,
            buildinfo_path=buildinfo_path,
        )
        self._generated_cache[norad_cat_id] = generated
        return generated

    def _is_cache_valid(self, decoder: DecoderRef, generated_py: Path, 
                        buildinfo_path: Path) -> bool:
        """
        Check whether the cached generated decoder is still valid.
        """
        if not generated_py.exists():
            return False
        if not buildinfo_path.exists():
            return False
        if not decoder.source_path.exists():
            return False

        try:
            info = json.loads(buildinfo_path.read_text(encoding="utf-8"))
        except Exception:
            return False

        return (
            info.get("generator_version") == GENERATOR_VERSION
            and info.get("source_path") == str(decoder.source_path.resolve())
            and info.get("source_mtime_ns") == decoder.source_path.stat().st_mtime_ns
            and info.get("generated_py") == str(generated_py.resolve())
        )

    def _write_buildinfo(self, decoder: DecoderRef, generated_py: Path, 
                         buildinfo_path: Path) -> None:
        """
        Write decoder cache metadata.
        """
        payload = {
            "generator_version": GENERATOR_VERSION,
            "source_path": str(decoder.source_path.resolve()),
            "source_mtime_ns": decoder.source_path.stat().st_mtime_ns,
            "generated_py": str(generated_py.resolve())
        }
        buildinfo_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

# ------------------ Low-level packet parsing helpers ------------------

def hex_to_bytes(hex_str: str) -> bytes:
    """
    Convert a hex string into raw bytes.
    """
    return bytes.fromhex(hex_str)

def extract_raw_fields_for_indexing(raw_json: dict[str, Any]) -> tuple[str, str]:
    """
    Extract the raw metadata fields we keep from SatNOGS packets.
    """
    timestamp_utc = str(raw_json.get("timestamp", "")).strip()
    observer = str(raw_json.get("observer", "")).strip()

    if not timestamp_utc:
        raise ValueError("Raw packet is missing timestamp")
    if not observer:
        observer = ""

    return timestamp_utc, observer

def _decode_ax25_callsign(addr_bytes: bytes) -> str:
    """
    Decode one 7-byte AX.25 address field into a callsign string.
    """
    if len(addr_bytes) != 7:
        raise ValueError("AX.25 address field must be 7 bytes long")

    callsign = "".join(chr(b >> 1) for b in addr_bytes[:6]).strip()
    ssid = (addr_bytes[6] >> 1) & 0x0F

    if ssid:
        return f"{callsign}-{ssid}"
    return callsign

def extract_ax25_and_ccsds(frame_hex: str) -> dict[str, str]:
    """
    Extract AX.25 metadata and CCSDS payload from a raw AX.25 frame.

    Returns
    -------
    dict with:
    - dest_callsign
    - src_callsign
    - raw_ax25_frame_hex
    - raw_ccsds_packet_hex
    """
    frame = hex_to_bytes(frame_hex)

    if len(frame) < 16:
        raise ValueError("AX.25 frame is too short")

    dest = frame[0:7]
    src = frame[7:14]
    dest_callsign = _decode_ax25_callsign(dest)
    src_callsign = _decode_ax25_callsign(src)

    # Skip control byte and PID byte.
    info_field = frame[16:]
    if len(info_field) == 0:
        raise ValueError("AX.25 frame has empty information field")

    return {
        "dest_callsign": dest_callsign,
        "src_callsign": src_callsign,
        "raw_ax25_frame_hex": frame_hex,
        "raw_ccsds_packet_hex": info_field.hex().upper(),
    }

def parse_ccsds_primary_header(packet_hex: str) -> dict[str, int]:
    """
    Parse the 6-byte CCSDS primary header.

    Returns
    -------
    dict with:
    - apid
    - sequence_count
    """
    packet = hex_to_bytes(packet_hex)

    if len(packet) < 6:
        raise ValueError("CCSDS packet is too short to contain a primary header")

    first_two = int.from_bytes(packet[0:2], byteorder="big")
    seq_two = int.from_bytes(packet[2:4], byteorder="big")

    apid = first_two & 0x07FF
    sequence_count = seq_two & 0x3FFF

    return {
        "apid": apid,
        "sequence_count": sequence_count,
    }

# --------------------------- Decoder Loader ---------------------------

class DecoderLoader:
    """
    Dynamic loader for generated Python decoder modules.
    """

    def __init__(self) -> None:
        self._module_cache: dict[str, Any] = {}

    def parse_with_decoder(self, 
                           parser_path: str,
                           packet_hex: str) -> Any:
        """
        Load the generated decoder module and parse a packet with it.
        """
        module = self._load_module(parser_path)
        
        decoder_cls = getattr(module, "Decoder", None)
        if decoder_cls is None:
            raise AttributeError(f"Decoder class not found "
                                 f"in {parser_path}")

        packet_bytes = hex_to_bytes(packet_hex)
        
        raw_data = decoder_cls.from_bytes(packet_bytes)
        eng_data = decoder_cls.from_bytes_eng(packet_bytes)
        
        return raw_data, eng_data

    def _load_module(self, parser_path: str):
        """
        Import a generated decoder .py file dynamically.
        """
        if parser_path in self._module_cache:
            return self._module_cache[parser_path]

        path = Path(parser_path)
        if not path.exists():
            raise FileNotFoundError(f"Generated decoder file not found: {path}")

        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load decoder module from: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self._module_cache[parser_path] = module
        return module

# -------------------------- Decoder Service ---------------------------

class DecoderService:
    """
    High-level raw-packet decode service.

    This converts raw SatNOGS rows from the database into parsed rows,
    inserts successful parses, and deletes deterministically malformed 
    rows. It uses the DecoderManager to resolve and generate decoders as 
    needed, and the DecoderLoader to dynamically load and run the 
    generated decoders to parse packets.
    """

    def __init__(self, db) -> None:
        """
        Parameters
        ----------
        db
            An instance of the SQLite database helper class.
        """
        self.db = db
        self.decoder_loader = DecoderLoader()
        self.decoder_manager = DecoderManager()

    def parse_unparsed(self, norad_cat_id: int, 
                       log=print,
                       start_utc: str | None = None,
                       end_utc: str | None = None) -> dict[str, Any]:
        """
        Parse raw rows for this NORAD that do not yet have parsed rows.

        Optional start/end timestamps limit parsing to a timestamp range.

        Returns a dict summary.
        """
        result = {
            "total_seen": 0,
            "raw_inserted": 0,
            "raw_existing": 0,
            "parsed_inserted": 0,
            "parsed_skipped_existing": 0,
            "parse_errors": 0,
            "errors": [],
        }

        rows = self.db.iter_unparsed_raw_rows(start_utc=start_utc,
                                              end_utc=end_utc)
        result["total_seen"] = len(rows)

        if log:
            range_text = ""
            if start_utc or end_utc:
                range_text = f" from {start_utc or '-inf'} to {end_utc or '+inf'}"
            log(f"Parsing {len(rows)} unparsed raw rows for NORAD {norad_cat_id}{range_text}")

        # Resolve and generate the decoder once for this NORAD instead
        # of re-reading config.toml for every packet in the loop.
        parser_path = ""
        decoder_ref = self.decoder_manager.resolve_decoder(norad_cat_id)
        if decoder_ref is not None:
            generated = self.decoder_manager.ensure_generated(norad_cat_id, decoder_ref)
            parser_path = str(generated.generated_py)

        deleted_count = 0

        for idx, row in enumerate(rows, start=1):
            try:
                raw_json = json.loads(row["raw_json"])

                parsed_dict = self.decode_raw_packet(
                    raw_frame_id=int(row["id"]),
                    norad_cat_id=norad_cat_id,
                    raw_json=raw_json,
                    parser_path=parser_path,
                )

                parsed = SimpleNamespace(**parsed_dict)
                inserted = self.db.insert_parsed_packet(parsed=parsed)
                if inserted:
                    result["parsed_inserted"] += 1
                else:
                    result["parsed_skipped_existing"] += 1

                if log and idx % 100 == 0:
                    suffix = f" | deleted malformed={deleted_count}" if deleted_count else ""
                    log(f"Parsed {idx}/{len(rows)} rows | inserted={result['parsed_inserted']}{suffix}")

            except Exception as exc:
                result["parse_errors"] += 1
                err_text = str(exc)
                result["errors"].append(f"Parse row {row['id']}: {err_text}")

                if self._is_malformed_frame_error(err_text):
                    self.db.delete_raw_packet_by_id(int(row["id"]))
                    deleted_count += 1

        if log and deleted_count:
            log(f"Deleted {deleted_count} malformed raw rows")

        return result

    def decode_raw_packet(self,
                          raw_frame_id: int,
                          norad_cat_id: int,
                          raw_json: dict[str, Any],
                          parser_path: str | None = None) -> dict[str, Any]:
        """
        Decode one raw SatNOGS packet into parsed JSON dictionaries.

        'parser_path' is the generated decoder path. When omitted, the
        decoder is resolved on the spot (kept for standalone use);
        parse_unparsed() supplies it so resolution happens once per run.
        """
        timestamp_utc, observer = extract_raw_fields_for_indexing(raw_json)

        frame = raw_json.get("frame")
        if frame is None:
            raise ValueError("Raw packet is missing 'frame'")

        frame_hex = str(frame).strip().upper()

        ax25 = extract_ax25_and_ccsds(frame_hex)
        ccsds = parse_ccsds_primary_header(ax25["raw_ccsds_packet_hex"])

        apid = ccsds["apid"]
        sequence_count = ccsds["sequence_count"]

        # Resolve only if the caller didn't already hand us a path.
        if parser_path is None:
            parser_path = ""
            decoder_ref = self.decoder_manager.resolve_decoder(norad_cat_id)
            if decoder_ref is not None:
                generated = self.decoder_manager.ensure_generated(norad_cat_id, decoder_ref)
                parser_path = str(generated.generated_py)

        parsed_json: dict[str, Any] | None = None
        parsed_json_eng: dict[str, Any] | None = None
        if parser_path:
            full_ccsds_hex = ax25["raw_ccsds_packet_hex"]

            try:
                # Extract data from CCSDS packet
                parsed_json, parsed_json_eng = self.decoder_loader.parse_with_decoder(
                    parser_path=parser_path,
                    packet_hex=full_ccsds_hex,
                )
                
                # Additions for backwards compatibility
                if parsed_json is not None:
                    parsed_json["_decode_mode"] = "full_ccsds"
                if parsed_json_eng is not None:
                    parsed_json_eng["_decode_mode"] = "full_ccsds"
                    
            except Exception as exc:
                parsed_json = {
                    "_decode_error": True,
                    "_parser_path": parser_path,
                    "_tried_modes": ["full_ccsds"],
                    "_errors": [f"full_ccsds: {type(exc).__name__}: {exc}"],
                }
                parsed_json_eng = None

        return {
            "raw_frame_id": raw_frame_id,
            "timestamp_utc": timestamp_utc,
            "observer": observer,
            "dest_callsign": ax25["dest_callsign"],
            "src_callsign": ax25["src_callsign"],
            "raw_ax25_frame_hex": ax25["raw_ax25_frame_hex"],
            "ccsds_apid": apid,
            "ccsds_sequence_count": sequence_count,
            "raw_ccsds_packet_hex": ax25["raw_ccsds_packet_hex"],
            "parsed_json": parsed_json,
            "parsed_json_eng": parsed_json_eng,
        }

    @staticmethod
    def _is_malformed_frame_error(err_text: str) -> bool:
        """
        Return True only for deterministic malformed-frame errors that are
        safe to delete from the raw queue.
        """
        return any(token in err_text for token in MALFORMED_FRAME_ERRORS)
    
# ----------------------------------------------------------------------