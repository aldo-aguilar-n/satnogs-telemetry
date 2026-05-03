"""
Title: decode.py
Authors: Aldo Aguilar
Date: 2026-05-03
Description: Decode and parser utilities for SatNOGS telemetry.

Functionalities
----------------
- Load decoder mapping from config.toml
- Prompt the user to choose a .ksy decoder when needed
- Compile Kaitai decoders into Python and cache them locally
- Parse raw SatNOGS packets into AX.25 / CCSDS / decoded payload records
- Delete malformed raw rows during parse so they are not retried forever
"""

# System imports
from __future__ import annotations
from dataclasses import dataclass
import csv
import re
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
from types import SimpleNamespace

# Third-party imports
import tomllib
import tomli_w

# Global path constants
CONFIG_PATH = Path("config.toml")
DECODER_SEARCH_ROOT = Path("tools/satnogs-decoders")
DECODERS_DIR = Path("decoders")

CONVERSION_SUFFIX = "_conversions.json"


# Kaitai compiler candidates to look for on PATH, in order of preference
KSC_CANDIDATES = [
    "kaitai-struct-compiler.bat",
    "kaitai-struct-compiler.cmd",
    "kaitai-struct-compiler",
]

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
    Reference to a decoder definition before compilation.
    """
    ksy_path: Path
    root_class: str

@dataclass(slots=True)
class CompiledDecoder:
    """
    Reference to a compiled Python decoder.
    """
    generated_py: Path
    root_class: str
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
    [satellites.98386.decoder]
    ksy_path = "tools/satnogs-decoders/ksy/cosmo.ksy"
    root_class = "Cosmo"
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

        ksy_path = str(decoder.get("ksy_path", "")).strip()
        root_class = str(decoder.get("root_class", "")).strip()

        if ksy_path and root_class:
            result[norad] = {
                "ksy_path": ksy_path,
                "root_class": root_class,
            }

    return result

def save_decoder_mapping(norad_cat_id: int, 
                         ksy_path: str, 
                         root_class: str, 
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
        "ksy_path": ksy_path,
        "root_class": root_class,
    }

    with config_path.open("wb") as f:
        f.write(tomli_w.dumps(data).encode("utf-8"))

def _scan_ksy_files(search_root: Path = DECODER_SEARCH_ROOT) -> list[Path]:
    """
    Find all .ksy files under the decoder tree.
    """
    if not search_root.exists():
        return []

    return sorted(search_root.rglob("*.ksy"))

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
    
def _default_root_class_from_ksy(ksy_path: Path) -> str:
    """
    Derive the default root class from the .ksy filename stem.

    Examples
    --------
    cosmo.ksy  -> Cosmo
    canvas.ksy -> Canvas
    """
    stem = ksy_path.stem.strip()
    if not stem:
        return "Decoder"
    return stem[:1].upper() + stem[1:]

def prompt_for_decoder_choice(norad_cat_id: int) -> tuple[str, str]:
    """
    Prompt the user to choose a .ksy decoder for a satellite.

    The displayed list uses repo-relative paths for readability.
    The root class is inferred automatically from the filename stem.
    """
    ksy_files = _scan_ksy_files()
    if not ksy_files:
        raise FileNotFoundError(f"No .ksy files found under {DECODER_SEARCH_ROOT}")

    print(f"No decoder configured for NORAD {norad_cat_id}.")
    print("Select a decoder:")

    for i, path in enumerate(ksy_files, start=1):
        print(f"{i}) {_repo_relative(path)}")

    while True:
        raw = input("Enter selection number: ").strip()
        try:
            idx = int(raw)
            if 1 <= idx <= len(ksy_files):
                break
        except Exception:
            pass
        print("Invalid selection.")

    selected = ksy_files[idx - 1]
    rel_path = _repo_relative(selected)
    root_class = _default_root_class_from_ksy(selected)

    print(f"Using root class: {root_class}")
    return rel_path, root_class

def _find_kaitai_compiler() -> str:
    """
    Resolve the Kaitai compiler from PATH.

    On Windows, prefer the .bat/.cmd launcher if available.
    """
    for candidate in KSC_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found

    raise FileNotFoundError(
        "Could not find Kaitai Struct Compiler on PATH. "
        "Make sure one of these works in this terminal: "
        "kaitai-struct-compiler, kaitai-struct-compiler.bat"
    )

# ------------------- Engineering Conversion Helpers -------------------

def conversion_lookup_path(norad_cat_id: int) -> Path:
    """
    Return the per-NORAD conversion lookup path.
    """
    return DECODERS_DIR / str(norad_cat_id) / f"{norad_cat_id}{CONVERSION_SUFFIX}"

def _normalize_lookup_field_name(name: str) -> str:
    """
    Normalize field names so CSV ItemName and decoder JSON keys match.
    """
    return str(name or "").strip().upper()

def _clean_units(units: str) -> str:
    """
    Reduce verbose unit labels like 'Volts (V)' to 'V' when possible.
    """
    text = str(units or "").replace(" ", " ").strip()
    if not text:
        return ""
    match = re.search(r"\(([^()]+)\)\s*$", text)
    if match:
        return match.group(1).strip()
    return " ".join(text.split())

def _parse_linear_conversion(conv: str) -> dict[str, float] | None:
    """
    Parse simple linear conversion strings like 'C0=... C1=...'.
    """
    text = str(conv or "").strip()
    if not text or "C1=" not in text:
        return None

    coeffs: dict[str, float] = {}
    for key, value in re.findall(r"(C\d+)\s*=\s*([+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?\d+)?)", text):
        try:
            coeffs[key] = float(value)
        except Exception:
            continue

    if not coeffs or "C1" not in coeffs:
        return None

    return {
        "c0": float(coeffs.get("C0", 0.0)),
        "c1": float(coeffs["C1"]),
    }

def _parse_enum_conversion(conv: str) -> dict[str, str] | None:
    """
    Parse enum strings like '0/IDLE 1/ACTIVE'.
    """
    text = " ".join(str(conv or "").replace(" ", " ").split())
    if not text or "C1=" in text or "/" not in text:
        return None

    pairs = re.findall(r"([+-]?\d+)\s*/\s*([^/]+?)(?=\s+[+-]?\d+\s*/|$)", text)
    if not pairs:
        return None

    enum_map: dict[str, str] = {}
    for raw, name in pairs:
        enum_map[str(int(raw))] = name.strip()
    return enum_map or None

def build_conversion_lookup_from_csv(csv_path: str | Path) -> dict[str, dict[str, Any]]:
    """
    Build a field-name -> conversion lookup table from a beacon CSV.
    """
    lookup: dict[str, dict[str, Any]] = {}
    with Path(csv_path).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            field_name = _normalize_lookup_field_name(row.get("ItemName", ""))
            if not field_name:
                continue

            entry: dict[str, Any] = {
                "units": _clean_units(row.get("Units", "")),
            }

            linear = _parse_linear_conversion(row.get("Conversion", ""))
            enum_map = _parse_enum_conversion(row.get("Conversion", ""))

            if linear is not None:
                entry["kind"] = "linear"
                entry["c0"] = linear["c0"]
                entry["c1"] = linear["c1"]
            elif enum_map is not None:
                entry["kind"] = "enum"
                entry["map"] = enum_map
            else:
                continue

            lookup[field_name] = entry

    return lookup

def save_conversion_lookup(norad_cat_id: int, lookup: dict[str, dict[str, Any]]) -> Path:
    """
    Persist the conversion lookup under decoders/<norad>/.
    """
    outpath = conversion_lookup_path(norad_cat_id)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(lookup, indent=2, ensure_ascii=False), encoding="utf-8")
    return outpath

def load_conversion_lookup(norad_cat_id: int) -> dict[str, dict[str, Any]]:
    """
    Load a previously saved conversion lookup for one NORAD ID.
    """
    path = conversion_lookup_path(norad_cat_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def create_and_save_conversion_lookup(norad_cat_id: int, csv_path: str | Path) -> Path:
    """
    Build and save the per-NORAD conversion lookup from CSV.
    """
    lookup = build_conversion_lookup_from_csv(csv_path)
    return save_conversion_lookup(norad_cat_id=norad_cat_id, lookup=lookup)

def _apply_conversion_entry(raw_value: Any, entry: dict[str, Any]) -> Any:
    """
    Convert one raw leaf value using one lookup entry.
    """
    kind = str(entry.get("kind", "")).strip().lower()

    if kind == "linear" and isinstance(raw_value, (int, float, bool)):
        numeric_raw = int(raw_value) if isinstance(raw_value, bool) else raw_value
        c0 = float(entry.get("c0", 0.0))
        c1 = float(entry.get("c1", 1.0))
        return c0 + (c1 * float(numeric_raw))

    if kind == "enum":
        numeric_raw = int(raw_value) if isinstance(raw_value, bool) else raw_value
        try:
            return entry.get("map", {}).get(str(int(numeric_raw)), raw_value)
        except Exception:
            return raw_value

    return raw_value

def apply_conversions_to_parsed_json(parsed_json: Any, lookup: dict[str, dict[str, Any]]) -> Any:
    """
    Recursively apply field conversions to decoded JSON leaf values.
    """
    if not lookup:
        return parsed_json

    def _convert(node: Any, parent_key: str = "") -> Any:
        if isinstance(node, dict):
            converted: dict[str, Any] = {}
            for key, value in node.items():
                if str(key).startswith("_"):
                    converted[key] = _convert(value, str(key))
                    continue

                if isinstance(value, (dict, list)):
                    converted[key] = _convert(value, str(key))
                    continue

                entry = lookup.get(_normalize_lookup_field_name(key))
                converted[key] = _apply_conversion_entry(value, entry) if entry else value
            return converted

        if isinstance(node, list):
            return [_convert(item, parent_key) for item in node]

        return node

    return _convert(parsed_json)

# -------------------------- Decoder Manager ---------------------------

class DecoderManager:
    """
    Resolve, compile, and cache satellite decoders.
    """

    def __init__(self) -> None:
        DECODERS_DIR.mkdir(parents=True, exist_ok=True)
        self._compiled_cache: dict[int, CompiledDecoder] = {}

    def resolve_decoder(self, norad_cat_id: int) -> DecoderRef | None:
        """
        Resolve a decoder for a NORAD ID.

        If none is configured yet, prompt the user once and persist the 
        mapping.
        """
        mapping = load_decoder_mapping()
        decoder_info = mapping.get(norad_cat_id)

        if not decoder_info:
            rel_ksy_path, root_class = prompt_for_decoder_choice(norad_cat_id)
            save_decoder_mapping(
                norad_cat_id=norad_cat_id,
                ksy_path=rel_ksy_path,
                root_class=root_class,
            )
            decoder_info = {
                "ksy_path": rel_ksy_path,
                "root_class": root_class,
            }

        ksy_path = Path(decoder_info["ksy_path"])
        if not ksy_path.is_absolute():
            # Resolve relative to config.toml / repo root so launching 
            # the app from a different directory does not break decoder
            # paths.
            ksy_path = (CONFIG_PATH.parent / ksy_path).resolve()

        root_class = decoder_info["root_class"].strip()

        if not ksy_path.exists():
            raise FileNotFoundError(f"KSY file not found: {ksy_path}")

        return DecoderRef(
            ksy_path=ksy_path,
            root_class=root_class,
        )

    def ensure_compiled(self, norad_cat_id: int, decoder: DecoderRef) -> CompiledDecoder:
        """
        Compile a decoder if needed, otherwise reuse the cached version.

        This method first checks an in-memory cache for the current 
        process, then checks the on-disk build cache via .buildinfo.json.
        """
        cached = self._compiled_cache.get(norad_cat_id)
        if cached is not None and cached.generated_py.exists() and cached.buildinfo_path.exists():
            return cached

        out_dir = (DECODERS_DIR / str(norad_cat_id)).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        generated_py = (out_dir / f"{decoder.ksy_path.stem}.py").resolve()
        buildinfo_path = (out_dir / ".buildinfo.json").resolve()

        if self._is_cache_valid(decoder, generated_py, buildinfo_path):
            compiled = CompiledDecoder(
                generated_py=generated_py,
                root_class=decoder.root_class,
                buildinfo_path=buildinfo_path,
            )
            self._compiled_cache[norad_cat_id] = compiled
            return compiled

        self._compile_ksy(decoder.ksy_path, out_dir)
        self._write_buildinfo(decoder, generated_py, buildinfo_path)

        compiled = CompiledDecoder(
            generated_py=generated_py,
            root_class=decoder.root_class,
            buildinfo_path=buildinfo_path,
        )
        self._compiled_cache[norad_cat_id] = compiled
        return compiled

    def _compile_ksy(self, ksy_path: Path, out_dir: Path) -> None:
        """
        Invoke Kaitai Struct Compiler from the project root using 
        repo-relative paths.

        On Windows, if the resolved compiler is a .bat/.cmd launcher, 
        run it through cmd.exe so it launches correctly and relative 
        paths work.
        """
        compiler = _find_kaitai_compiler()

        try:
            project_root = CONFIG_PATH.parent.resolve()
            rel_ksy = ksy_path.resolve().relative_to(project_root)
            rel_out = out_dir.resolve().relative_to(project_root)
        except Exception:
            raise RuntimeError(
                "Could not compute repo-relative paths for Kaitai compilation. "
                f"Project root: {CONFIG_PATH.parent.resolve()} | "
                f"KSY path: {ksy_path} | Output dir: {out_dir}"
            )

        compiler_args = [
            compiler,
            "-t",
            "python",
            "-d",
            str(rel_out),
            str(rel_ksy),
        ]

        printable_cmd = subprocess.list2cmdline(compiler_args)

        # Batch launchers need cmd.exe on Windows.
        if compiler.lower().endswith((".bat", ".cmd")):
            cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *compiler_args]
        else:
            cmd = compiler_args

        try:
            print(f"Compiling {rel_ksy} into {rel_out}...", flush=True)

            completed = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=str(project_root),
            )

            if completed.stdout.strip():
                print(completed.stdout, flush=True)

            if completed.stderr.strip():
                print(completed.stderr, flush=True)

        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "Could not launch Kaitai Struct Compiler. "
                f"Resolved compiler path: {compiler!r}. "
                "Make sure it exists and is runnable in this terminal."
            ) from exc

        except subprocess.CalledProcessError as exc:
            stdout = (exc.stdout or "").strip()
            stderr = (exc.stderr or "").strip()

            details = []
            if stdout:
                details.append(f"stdout:\n{stdout}")
            if stderr:
                details.append(f"stderr:\n{stderr}")

            detail_text = "\n\n".join(details) if details else "No compiler output captured."

            raise RuntimeError(
                "Kaitai compilation failed.\n"
                f"Compiler: {compiler}\n"
                f"Command: {printable_cmd}\n"
                f"Exit code: {exc.returncode}\n"
                f"Project root: {project_root}\n"
                f"KSY path: {rel_ksy}\n"
                f"Output dir: {rel_out}\n"
                f"{detail_text}"
            ) from exc

    def _is_cache_valid(self, decoder: DecoderRef, generated_py: Path, 
                        buildinfo_path: Path) -> bool:
        """
        Check whether the cached compiled decoder is still valid.
        """
        if not generated_py.exists():
            return False
        if not buildinfo_path.exists():
            return False
        if not decoder.ksy_path.exists():
            return False

        try:
            info = json.loads(buildinfo_path.read_text(encoding="utf-8"))
        except Exception:
            return False

        return (
            info.get("ksy_path") == str(decoder.ksy_path.resolve())
            and info.get("ksy_mtime_ns") == decoder.ksy_path.stat().st_mtime_ns
            and info.get("generated_py") == str(generated_py.resolve())
            and info.get("root_class") == decoder.root_class
        )

    def _write_buildinfo(self, decoder: DecoderRef, generated_py: Path, 
                         buildinfo_path: Path) -> None:
        """
        Write decoder cache metadata.
        """
        payload = {
            "ksy_path": str(decoder.ksy_path.resolve()),
            "ksy_mtime_ns": decoder.ksy_path.stat().st_mtime_ns,
            "generated_py": str(generated_py.resolve()),
            "root_class": decoder.root_class,
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
    if len(frame) < 14:
        raise ValueError("AX.25 frame must contain destination and source addresses")

    dest = frame[0:7]
    src = frame[7:14]

    if len(dest) < 7 or len(src) < 7:
        raise ValueError("AX.25 frame ended before address section completed")

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
    Dynamic loader for compiled Python decoder modules.
    """

    def __init__(self) -> None:
        self._module_cache: dict[str, Any] = {}
        self._kaitai_property_cache: dict[type, list[str]] = {}

    def parse_with_decoder(self, 
                           parser_path: str, 
                           root_class: str, 
                           packet_hex: str,) -> dict[str, Any]:
        """
        Load the compiled decoder module and parse a packet with it.
        """
        module = self._load_module(parser_path)
        parser_cls = getattr(module, root_class, None)
        if parser_cls is None:
            raise AttributeError(f"Root class '{root_class}' not found "
                                 f"in {parser_path}")

        obj = parser_cls.from_bytes(hex_to_bytes(packet_hex))
        return self._to_builtin(obj)

    def _load_module(self, parser_path: str):
        """
        Import a compiled decoder .py file dynamically.
        """
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

    def _get_kaitai_property_names(self, cls: type) -> list[str]:
        """
        Return public @property names for a Kaitai-generated class.

        Kaitai `instances` are generated as Python @property methods, so they are
        not visible in obj.__dict__ unless accessed. Cache per class to avoid
        repeated dir(type(obj)) scans during bulk decoding.
        """
        cached = self._kaitai_property_cache.get(cls)
        if cached is not None:
            return cached

        names: list[str] = []

        for attr in dir(cls):
            if attr.startswith("_"):
                continue

            prop = getattr(cls, attr, None)
            if isinstance(prop, property):
                names.append(attr)

        self._kaitai_property_cache[cls] = names
        return names

    def _to_builtin(self, value: Any, depth: int = 0) -> Any:
        """
        Convert parsed Kaitai objects into plain Python types suitable 
        for JSON.

        For numeric Kaitai backing fields named *_raw that have a matching
        computed @property without the suffix, emit the computed property in
        the original field position instead of emitting the *_raw value.

        Example
        -------
        bcn_temp_cdh_raw -> bcn_temp_cdh

        This prevents CSV export from skipping the value due to the *_raw
        suffix while keeping the field in the original packet order. The
        numeric check avoids changing structural Kaitai objects such as
        dest_callsign_raw and src_callsign_raw.
        """
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

        # Use __dict__ first so normal Kaitai fields keep the same order
        # in which Kaitai populated the instance attributes.
        for attr, attr_value in list(getattr(value, "__dict__", {}).items()):
            if attr.startswith("_"):
                continue

            if callable(attr_value):
                continue

            # Numeric Kaitai backing fields like bcn_temp_cdh_raw may have
            # a corresponding computed @property named bcn_temp_cdh.
            #
            # If so, do NOT emit the *_raw name. Emit the computed property
            # under the non-raw name at this exact position.
            #
            # The numeric check avoids changing structural objects such as
            # dest_callsign_raw, src_callsign_raw, etc.
            if attr.endswith("_raw") and isinstance(attr_value, (int, float, bool)):
                computed_attr = attr[:-4]
                prop = getattr(type(value), computed_attr, None)

                if isinstance(prop, property):
                    try:
                        computed_value = getattr(value, computed_attr)
                    except Exception:
                        continue

                    if callable(computed_value):
                        continue

                    result[computed_attr] = self._to_builtin(computed_value, depth + 1)
                    continue

            result[attr] = self._to_builtin(attr_value, depth + 1)

        # Kaitai `instances` are generated as @property methods.
        # They are not present in __dict__ until accessed.
        #
        # This catches computed properties that do not have matching numeric
        # *_raw backing fields. Properties already inserted above are skipped,
        # so fields like bcn_temp_cdh are not appended again at the end.
        for attr in self._get_kaitai_property_names(type(value)):
            if attr in result:
                continue

            try:
                attr_value = getattr(value, attr)
            except Exception:
                continue

            if callable(attr_value):
                continue

            result[attr] = self._to_builtin(attr_value, depth + 1)

        return result


# -------------------------- Decoder Service ---------------------------

class DecoderService:
    """
    High-level raw-packet decode service.

    This converts raw SatNOGS rows from the database into parsed rows,
    inserts successful parses, and deletes deterministically malformed 
    rows. It uses the DecoderManager to resolve and compile decoders as 
    needed, and the DecoderLoader to dynamically load and run the 
    compiled decoders to parse packets.
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
        Engineering-unit JSON is generated automatically whenever a
        conversion lookup table exists.

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

        deleted_count = 0

        for idx, row in enumerate(rows, start=1):
            try:
                raw_json = json.loads(row["raw_json"])

                parsed_dict = self.decode_raw_packet(
                    raw_frame_id=int(row["id"]),
                    norad_cat_id=norad_cat_id,
                    raw_json=raw_json
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
                          raw_json: dict[str, Any]) -> dict[str, Any]:
        """
        Decode one raw SatNOGS packet into parsed metadata + payload.

        parsed_json always stores the raw decoded payload.
        parsed_json_eng stores the engineering-unit version when a saved
        conversion lookup table exists. Fields without conversions are
        left as their raw values.
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

        parsed_json: dict[str, Any] | None = None
        parsed_json_eng: dict[str, Any] | None = None
        parser_path = ""
        parser_root_class = ""
        conversion_lookup = load_conversion_lookup(norad_cat_id)

        decoder_ref = self.decoder_manager.resolve_decoder(norad_cat_id)
        if decoder_ref is not None:
            compiled = self.decoder_manager.ensure_compiled(norad_cat_id, decoder_ref)
            parser_path = str(compiled.generated_py)
            parser_root_class = compiled.root_class

            full_ccsds_hex = ax25["raw_ccsds_packet_hex"]
            ccsds_payload_hex = full_ccsds_hex[12:] if len(full_ccsds_hex) >= 12 else ""

            candidates: list[tuple[str, str]] = []

            # First try the full AX.25 frame.
            # Many SatNOGS .ksy decoders expect to start from the AX.25 layer.
            candidates.append(("full_ax25_frame", ax25["raw_ax25_frame_hex"]))

            # Then try the full CCSDS packet.
            if full_ccsds_hex:
                candidates.append(("full_ccsds", full_ccsds_hex))

            # Finally try CCSDS payload only.
            if ccsds_payload_hex:
                candidates.append(("ccsds_payload", ccsds_payload_hex))

            decode_errors: list[str] = []

            for mode, candidate_hex in candidates:
                try:
                    decoded_payload = self.decoder_loader.parse_with_decoder(
                        parser_path=parser_path,
                        root_class=parser_root_class,
                        packet_hex=candidate_hex,
                    )

                    if isinstance(decoded_payload, dict):
                        parsed_json = decoded_payload
                        parsed_json["_decode_mode"] = mode

                        if conversion_lookup:
                            parsed_json_eng = apply_conversions_to_parsed_json(
                                parsed_json,
                                conversion_lookup,
                            )
                    else:
                        parsed_json = {
                            "_decode_mode": mode,
                            "value": decoded_payload,
                        }

                        if conversion_lookup:
                            parsed_json_eng = apply_conversions_to_parsed_json(
                                parsed_json,
                                conversion_lookup,
                            )
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