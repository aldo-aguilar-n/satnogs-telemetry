"""
Title: generate_decoder.py
Authors: Aldo Aguilar
Date: 2026-06-17
Description: Telemetry dictionary spreadsheet-backed decoder generator.

The user-selected telemetry dictionary workbook is expected to provide a
packet table with packet name/APID and a telemetry table with
item name/type/packet/location/conversions (see example_ctdb.xlsx).

The generated module exposes 'Decoder.from_bytes(...)' for raw decoded
JSON and 'Decoder.from_bytes_eng(...)' for engineering JSON when
conversions exist.
"""

# System imports
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pformat
import re
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

# Global constants
GENERATOR_VERSION = 1
XLSX_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XLSX_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

# ---------------------------- Data Classes ----------------------------

@dataclass(slots=True)
class FieldDef:
    name: str
    packet: str
    description: str
    type_name: str
    location: str
    bit_offset: int
    bit_length: int
    signed: bool = False
    float_bits: int | None = None
    conversion: dict[str, Any] | None = None

@dataclass(slots=True)
class PacketDef:
    name: str
    apid: int
    byte_size: int | None = None
    fields: list[FieldDef] = field(default_factory=list)
    
# ------------------------- Decoder Generator --------------------------

def _col_to_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", str(cell_ref).upper())
    if not match:
        return 0
    col = 0
    for ch in match.group(1):
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return col - 1

def _shared_strings(zf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out: list[str] = []
    for si in root.findall(f"{{{XLSX_MAIN_NS}}}si"):
        out.append("".join(t.text or "" for t in si.findall(f".//{{{XLSX_MAIN_NS}}}t")))
    return out

def _cell_value(cell: ET.Element, shared: list[str]) -> Any:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(f".//{{{XLSX_MAIN_NS}}}t")).strip()

    value_node = cell.find(f"{{{XLSX_MAIN_NS}}}v")
    if value_node is None or value_node.text is None:
        return None

    raw = value_node.text
    if cell_type == "s":
        try:
            return shared[int(raw)].strip()
        except Exception:
            return raw.strip()
    return raw.strip()

def _read_sheet(zf: ZipFile, target: str, shared: list[str]) -> list[list[Any]]:
    target = target.lstrip("/")
    if not target.startswith("xl/"):
        target = "xl/" + target
    root = ET.fromstring(zf.read(target))
    rows: list[list[Any]] = []
    for row in root.findall(f"{{{XLSX_MAIN_NS}}}sheetData/{{{XLSX_MAIN_NS}}}row"):
        values: dict[int, Any] = {}
        for cell in row.findall(f"{{{XLSX_MAIN_NS}}}c"):
            values[_col_to_index(cell.attrib.get("r", "A"))] = _cell_value(cell, shared)
        if values:
            rows.append([values.get(i) for i in range(max(values) + 1)])
    return rows

def _read_workbook(path: str | Path) -> dict[str, list[list[Any]]]:
    with ZipFile(path) as zf:
        shared = _shared_strings(zf)
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall(f"{{{PKG_REL_NS}}}Relationship")
        }
        sheets: dict[str, list[list[Any]]] = {}
        for sheet in workbook.findall(f"{{{XLSX_MAIN_NS}}}sheets/{{{XLSX_MAIN_NS}}}sheet"):
            name = sheet.attrib.get("name", "Sheet")
            rid = sheet.attrib.get(f"{{{XLSX_REL_NS}}}id")
            if rid in targets:
                sheets[name] = _read_sheet(zf, targets[rid], shared)
        return sheets

def _norm_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")

def _rows_by_header(rows: list[list[Any]], required: set[str]) -> list[dict[str, Any]]:
    for idx, row in enumerate(rows):
        headers = [_norm_header(v) for v in row]
        if required.issubset(set(headers)):
            out: list[dict[str, Any]] = []
            for raw_row in rows[idx + 1:]:
                item = {headers[i]: raw_row[i] if i < len(raw_row) else None for i in range(len(headers)) if headers[i]}
                if any(str(v or "").strip() for v in item.values()):
                    out.append(item)
            return out
    raise ValueError(f"Could not find worksheet headers: {sorted(required)}")

def _parse_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text, 0)
    except Exception:
        try:
            return int(float(text))
        except Exception:
            return None

def _type_info(type_name: str) -> tuple[int, bool, int | None]:
    text = str(type_name or "").strip().upper()
    match = re.search(r"(\d+)", text)
    if not match:
        raise ValueError(f"Type has no bit width: {type_name!r}")
    bits = int(match.group(1))
    signed = text.startswith(("S", "I"))
    float_bits = bits if text.startswith("F") else None
    return bits, signed, float_bits

def _parse_location(location: str, default_bits: int) -> tuple[int, int]:
    text = str(location or "").strip()
    match = re.match(r"^/?(\d+)(?::(\d+)(?:-(\d+))?)?$", text)
    if not match:
        raise ValueError(f"Unsupported location: {location!r}")
    byte_offset = int(match.group(1))
    bit_start = int(match.group(2) or 0)
    if match.group(2) is None:
        bit_length = default_bits
    elif match.group(3) is None:
        bit_length = 1
    else:
        bit_end = int(match.group(3))
        bit_length = bit_end - bit_start + 1
    if bit_length <= 0:
        raise ValueError(f"Invalid bit range: {location!r}")
    return byte_offset * 8 + bit_start, bit_length

def _parse_conversion(value: Any) -> dict[str, Any] | None:
    text = " ".join(str(value or "").replace("\u00a0", " ").split())
    if not text:
        return None

    coeffs = {
        int(k[1:]): float(v)
        for k, v in re.findall(
            r"(C\d+)\s*=\s*([+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?\d+)?)",
            text,
            flags=re.IGNORECASE,
        )
    }
    if coeffs:
        return {"kind": "polynomial", "coeffs": dict(sorted(coeffs.items()))}

    pairs = re.findall(r"([+-]?\d+)\s*/\s*([^/]+?)(?=\s+[+-]?\d+\s*/|$)", text)
    if pairs:
        return {"kind": "enum", "map": {str(int(raw)): name.strip() for raw, name in pairs}}
    return None

def _group(field: FieldDef) -> str:
    desc = field.description.lower()
    if "primary header" in desc or field.bit_offset < 48:
        return "primary_header"
    if "secondary header" in desc or 48 <= field.bit_offset < 96:
        return "secondary_header"
    return "user_data"

def _load_spec(source_path: str | Path) -> dict[int, dict[str, Any]]:
    sheets = _read_workbook(source_path)
    packet_rows: list[dict[str, Any]] | None = None
    field_rows: list[dict[str, Any]] | None = None
    for rows in sheets.values():
        headers = {_norm_header(v) for row in rows[:1] for v in row}
        if {"packet_name", "apid"}.issubset(headers):
            packet_rows = _rows_by_header(rows, {"packet_name", "apid"})
        if {"item_name", "type", "packet", "location"}.issubset(headers):
            field_rows = _rows_by_header(rows, {"item_name", "type", "packet", "location"})
    if packet_rows is None or field_rows is None:
        raise ValueError("Telemetry dictionary must include packet and telemetry tables")

    packets_by_name: dict[str, PacketDef] = {}
    for row in packet_rows:
        name = str(row.get("packet_name") or "").strip()
        apid = _parse_int(row.get("apid"))
        if not name or apid is None:
            continue
        packets_by_name[name] = PacketDef(
            name=name,
            apid=apid,
            byte_size=_parse_int(row.get("byte_size")),
        )

    for row in field_rows:
        name = str(row.get("item_name") or "").strip()
        packet_name = str(row.get("packet") or "").strip()
        type_name = str(row.get("type") or "").strip()
        location = str(row.get("location") or "").strip()
        if not name or packet_name not in packets_by_name or not type_name or not location:
            continue
        bits, signed, float_bits = _type_info(type_name)
        bit_offset, bit_length = _parse_location(location, bits)
        packets_by_name[packet_name].fields.append(
            FieldDef(
                name=name,
                packet=packet_name,
                description=str(row.get("description") or ""),
                type_name=type_name,
                location=location,
                bit_offset=bit_offset,
                bit_length=bit_length,
                signed=signed,
                float_bits=float_bits,
                conversion=_parse_conversion(row.get("conversions")),
            )
        )

    spec: dict[int, dict[str, Any]] = {}
    for packet in packets_by_name.values():
        spec[packet.apid] = {
            "name": packet.name,
            "byte_size": packet.byte_size,
            "fields": [
                {
                    "name": field.name,
                    "group": _group(field),
                    "bit_offset": field.bit_offset,
                    "bit_length": field.bit_length,
                    "signed": field.signed,
                    "float_bits": field.float_bits,
                    "conversion": field.conversion,
                }
                for field in packet.fields
            ],
        }
    if not spec:
        raise ValueError(f"No packet definitions found in telemetry dictionary: {source_path}")
    return spec


GENERATED_BODY = r'''
import struct
from typing import Any


def _extract_unsigned(packet: bytes, bit_offset: int, bit_length: int) -> int:
    total_bits = len(packet) * 8
    if bit_offset < 0 or bit_length <= 0 or bit_offset + bit_length > total_bits:
        raise ValueError(f"Invalid bit range offset={bit_offset}, length={bit_length}, packet_bits={total_bits}")
    as_int = int.from_bytes(packet, byteorder="big", signed=False)
    shift = total_bits - (bit_offset + bit_length)
    return (as_int >> shift) & ((1 << bit_length) - 1)


def _decode_field(packet: bytes, field_def: dict[str, Any]) -> Any:
    bit_offset = int(field_def["bit_offset"])
    bit_length = int(field_def["bit_length"])
    if field_def.get("float_bits") is not None:
        if bit_offset % 8:
            raise ValueError("Floating-point field must be byte-aligned")
        byte_offset = bit_offset // 8
        if bit_length == 32:
            return float(struct.unpack(">f", packet[byte_offset:byte_offset + 4])[0])
        if bit_length == 64:
            return float(struct.unpack(">d", packet[byte_offset:byte_offset + 8])[0])
        raise ValueError(f"Unsupported float width: {bit_length}")
    value = _extract_unsigned(packet, bit_offset, bit_length)
    if field_def.get("signed"):
        sign_bit = 1 << (bit_length - 1)
        if value & sign_bit:
            value -= 1 << bit_length
    return value


def _apply_conversion(value: Any, conversion: dict[str, Any] | None) -> Any:
    if conversion is None:
        return value
    kind = str(conversion.get("kind", "")).lower()
    if kind in ("linear", "polynomial") and isinstance(value, (int, float, bool)):
        numeric = int(value) if isinstance(value, bool) else float(value)
        coeffs = conversion.get("coeffs")
        if coeffs is not None:
            return sum(
                float(coeff) * (numeric ** int(power))
                for power, coeff in coeffs.items()
            )
        return float(conversion.get("c0", 0.0)) + float(conversion.get("c1", 1.0)) * numeric
    if kind == "enum":
        try:
            return conversion.get("map", {}).get(str(int(value)), value)
        except Exception:
            return value
    return value


def _primary_header(packet: bytes) -> dict[str, int]:
    if len(packet) < 6:
        raise ValueError("CCSDS packet is too short to contain a primary header")
    first = int.from_bytes(packet[0:2], "big")
    seq = int.from_bytes(packet[2:4], "big")
    return {
        "version": (first >> 13) & 0x7,
        "type": (first >> 12) & 0x1,
        "secondary_header_flag": (first >> 11) & 0x1,
        "apid": first & 0x07FF,
        "sequence_flags": (seq >> 14) & 0x3,
        "sequence_count": seq & 0x3FFF,
        "packet_length": int.from_bytes(packet[4:6], "big"),
    }


def _make_unique(target: dict[str, Any], key: str) -> str:
    if key not in target:
        return key
    idx = 2
    while f"{key}__{idx}" in target:
        idx += 1
    return f"{key}__{idx}"


def _decode(packet: bytes | bytearray | memoryview, engineering: bool = False) -> tuple[dict[str, Any], bool]:
    packet_bytes = bytes(packet)
    header = _primary_header(packet_bytes)
    apid = int(header["apid"])
    packet_def = PACKETS_BY_APID.get(apid)
    if packet_def is None:
        raise ValueError(f"No decoder database packet definition found for APID {apid}")

    primary: dict[str, Any] = {}
    secondary: dict[str, Any] = {}
    user: dict[str, Any] = {}
    has_conversions = False

    for field_def in packet_def.get("fields", []):
        raw_value = _decode_field(packet_bytes, field_def)
        value = raw_value
        if engineering:
            conversion = field_def.get("conversion")
            value = _apply_conversion(raw_value, conversion)
            if conversion is not None:
                has_conversions = True
        target = {
            "primary_header": primary,
            "secondary_header": secondary,
        }.get(field_def.get("group"), user)
        target[_make_unique(target, str(field_def["name"]))] = value

    payload = {
        "ccsds_space_packet": {
            "packet_primary_header": primary or header,
            "data_section": {
                "secondary_header": secondary,
                "user_data_field": {str(packet_def["name"]): user},
            },
        }
    }
    return payload, has_conversions


class Decoder:
    @classmethod
    def from_bytes(cls, packet: bytes | bytearray | memoryview) -> dict[str, Any]:
        payload, _ = _decode(packet, engineering=False)
        return payload

    @classmethod
    def from_bytes_eng(cls, packet: bytes | bytearray | memoryview) -> dict[str, Any] | None:
        payload, has_conversions = _decode(packet, engineering=True)
        return payload if has_conversions else None
'''


def write_decoder_module(source_path: str | Path, output_path: str | Path) -> Path:
    spec = _load_spec(source_path)
    outpath = Path(output_path)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    packets_literal = pformat(spec, width=100, sort_dicts=False)
    header = (
        '"""Auto-generated decoder. Do not edit by hand.\n'
        'Regenerate by updating the telemetry dictionary and reparsing.\n"""\n\n'
        'from __future__ import annotations\n\n'
        f'GENERATOR_VERSION = {GENERATOR_VERSION}\n'
        f'SOURCE_PATH = {str(source_path)!r}\n'
        f'PACKETS_BY_APID = {packets_literal}\n'
    )
    outpath.write_text(header + GENERATED_BODY, encoding="utf-8")
    return outpath

# ----------------------------------------------------------------------