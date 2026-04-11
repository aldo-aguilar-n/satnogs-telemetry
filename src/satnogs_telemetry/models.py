"""
Dataclasses used across the backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RawPacket:
    """
    Represents one full raw SatNOGS packet as received from the API.
    """

    norad_cat_id: int
    timestamp_utc: str
    observer: str
    raw_json: dict[str, Any]


@dataclass(slots=True)
class ParsedPacket:
    """
    Represents the parsed result derived from one raw packet.
    """

    raw_frame_id: int
    norad_cat_id: int
    timestamp_utc: str
    observer: str
    dest_callsign: str
    src_callsign: str
    raw_ax25_frame_hex: str
    ccsds_apid: int
    ccsds_sequence_count: int
    raw_ccsds_packet_hex: str
    parsed_json: dict[str, Any] | None
    parser_path: str = ""
    parser_root_class: str = ""


@dataclass(slots=True)
class DecoderSpec:
    """
    APID-specific decoder configuration.
    """

    apid: int
    decoder_type: str
    parser_path: str = ""
    ksy_path: str = ""
    root_class: str = ""
    strip_ccsds_primary_header: bool = False


@dataclass(slots=True)
class SatelliteConfig:
    """
    Satellite-specific matching and decoder registry.
    """

    norad_cat_id: int
    frame_protocol: str = "ax25_ccsds"
    transmitter: str = ""
    sat_id: str = ""
    apid_decoders: dict[int, DecoderSpec] = field(default_factory=dict)


@dataclass(slots=True)
class SyncResult:
    """
    Summary of one sync or parse run.
    """

    total_seen: int = 0
    raw_inserted: int = 0
    raw_existing: int = 0
    parsed_inserted: int = 0
    parsed_skipped_existing: int = 0
    parse_errors: int = 0
    errors: list[str] = field(default_factory=list)
