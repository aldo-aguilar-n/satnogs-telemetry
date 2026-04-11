"""
Shared utility helpers.

This module contains:
- time helpers
- JSON serialization
- hex conversion
- raw SatNOGS field extraction
- AX.25 extraction
- CCSDS primary header parsing
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any


def utc_now_iso() -> str:
    """Return the current UTC time as ISO-8601 ending in 'Z'."""
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def ensure_utc_iso(value: str) -> str:
    """Normalize a datetime string into UTC ISO-8601 format."""
    value = value.strip()
    if value.endswith("Z"):
        return value

    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)

    return (
        parsed.astimezone(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def json_dumps(value: Any) -> str:
    """Serialize a Python object to JSON text with stable key ordering."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def hex_to_bytes(hex_string: str) -> bytes:
    """Convert a hex string into bytes, ignoring whitespace."""
    return bytes.fromhex("".join(hex_string.split()))


def extract_raw_fields_for_indexing(packet: dict[str, Any]) -> tuple[str, str]:
    """
    Extract timestamp and observer from a full raw SatNOGS packet.

    This does not trim the raw packet for storage.
    """
    timestamp = packet.get("timestamp")
    if timestamp is None:
        raise ValueError("Raw packet is missing 'timestamp'")

    observer = str(packet.get("observer") or "")
    return ensure_utc_iso(str(timestamp)), observer


def flatten_dict(data: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dictionaries/lists into dotted keys."""
    out: dict[str, Any] = {}

    if isinstance(data, dict):
        for key, value in data.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            out.update(flatten_dict(value, child_prefix))
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            child_prefix = f"{prefix}[{idx}]"
            out.update(flatten_dict(value, child_prefix))
    else:
        out[prefix] = data

    return out


def decode_ax25_callsign(address_field: bytes) -> str:
    """
    Decode one 7-byte AX.25 address field into a callsign string.
    """
    if len(address_field) != 7:
        raise ValueError("AX.25 address field must be exactly 7 bytes")

    callsign = "".join(chr(b >> 1) for b in address_field[:6]).strip()
    ssid = (address_field[6] >> 1) & 0x0F

    if ssid:
        return f"{callsign}-{ssid}"
    return callsign


def extract_ax25_and_ccsds(frame_hex: str) -> dict[str, Any]:
    """
    Extract AX.25 callsigns and raw CCSDS packet from an AX.25 frame.

    Assumptions:
    - destination and source are standard AX.25 addresses
    - any optional digipeater addresses continue until extension bit is set
    - the information field is a CCSDS packet
    """
    frame_bytes = hex_to_bytes(frame_hex)
    if len(frame_bytes) < 16:
        raise ValueError("AX.25 frame is too short")

    addr_chunks: list[bytes] = []
    idx = 0

    while True:
        if idx + 7 > len(frame_bytes):
            raise ValueError("AX.25 frame ended before address section completed")

        chunk = frame_bytes[idx : idx + 7]
        addr_chunks.append(chunk)
        idx += 7

        # AX.25 extension bit: low bit set means this is the last address.
        if chunk[6] & 0x01:
            break

    if len(addr_chunks) < 2:
        raise ValueError("AX.25 frame must contain destination and source addresses")

    dest_callsign = decode_ax25_callsign(addr_chunks[0])
    src_callsign = decode_ax25_callsign(addr_chunks[1])

    if idx + 2 > len(frame_bytes):
        raise ValueError("AX.25 frame missing control/PID bytes")

    control = frame_bytes[idx]
    pid = frame_bytes[idx + 1]
    idx += 2

    info_field = frame_bytes[idx:]
    if not info_field:
        raise ValueError("AX.25 frame has empty information field")

    return {
        "dest_callsign": dest_callsign,
        "src_callsign": src_callsign,
        "raw_ax25_frame_hex": frame_hex.strip().upper(),
        "control": control,
        "pid": pid,
        "raw_ccsds_packet_hex": info_field.hex().upper(),
    }


def parse_ccsds_primary_header(packet_hex: str) -> dict[str, int]:
    """
    Parse the CCSDS primary header from a raw CCSDS packet.

    CCSDS primary header is 6 bytes:
    - bytes 0-1: version/type/sec_hdr_flag/APID
    - bytes 2-3: sequence flags + sequence count
    - bytes 4-5: packet length
    """
    packet = hex_to_bytes(packet_hex)
    if len(packet) < 6:
        raise ValueError("CCSDS packet is too short to contain a primary header")

    word1 = (packet[0] << 8) | packet[1]
    word2 = (packet[2] << 8) | packet[3]
    word3 = (packet[4] << 8) | packet[5]

    apid = word1 & 0x07FF
    sequence_count = word2 & 0x3FFF
    packet_length = word3

    return {
        "apid": apid,
        "sequence_count": sequence_count,
        "packet_length": packet_length,
    }
