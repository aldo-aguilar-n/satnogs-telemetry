"""
CSV export helpers for parsed telemetry stored in SQLite.

Behavior:
- Writes one CSV per APID.
- Orders rows by metadata timestamp from oldest to newest.
- Keeps only:
  - timestamp
  - observer
  - CCSDS primary header fields
  - CCSDS secondary header fields
  - CCSDS user data fields
- Uses shortened column names instead of full nested paths.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def flatten_dict(obj: Any, parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    """
    Flatten nested dict/list structures into a single-level dict.
    """
    items: dict[str, Any] = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
            items.update(flatten_dict(value, new_key, sep=sep))
        return items

    if isinstance(obj, list):
        for i, value in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.update(flatten_dict(value, new_key, sep=sep))
        return items

    items[parent_key] = obj
    return items


def _find_first_key_recursive(obj: Any, target_key: str) -> Any | None:
    """
    Recursively search nested dict/list structures for the first occurrence
    of a given key and return its value.
    """
    if isinstance(obj, dict):
        if target_key in obj:
            return obj[target_key]
        for value in obj.values():
            found = _find_first_key_recursive(value, target_key)
            if found is not None:
                return found

    if isinstance(obj, list):
        for value in obj:
            found = _find_first_key_recursive(value, target_key)
            if found is not None:
                return found

    return None


def get_ccsds_space_packet(parsed: dict[str, Any]) -> dict[str, Any] | None:
    """
    Retrieve the decoded CCSDS space packet from parsed_json.
    """
    found = _find_first_key_recursive(parsed, "ccsds_space_packet")
    return found if isinstance(found, dict) else None


def flatten_primary_header(ccsds_packet: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten the CCSDS primary header using only field names as column names.
    """
    primary_header = ccsds_packet.get("packet_primary_header", {})
    return flatten_dict(primary_header)


def flatten_secondary_header(ccsds_packet: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten the CCSDS secondary header using only field names as column names.
    """
    try:
        secondary_header = ccsds_packet["data_section"]["secondary_header"]
    except Exception:
        secondary_header = {}
    return flatten_dict(secondary_header)


def flatten_user_data(ccsds_packet: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten the CCSDS user data field using only field names as column names.

    If the user data field contains a single wrapper object such as beacon_t,
    unwrap it so the CSV columns are the actual field names.
    """
    try:
        user_data = ccsds_packet["data_section"]["user_data_field"]
    except Exception:
        user_data = {}

    if isinstance(user_data, dict) and len(user_data) == 1:
        only_value = next(iter(user_data.values()))
        if isinstance(only_value, dict):
            user_data = only_value

    return flatten_dict(user_data)


def build_row_from_db_row(row: Any) -> dict[str, Any] | None:
    """
    Build one CSV row from a parsed SQLite row.
    """
    parsed_json = row["parsed_json"]
    if not parsed_json:
        return None

    try:
        parsed = json.loads(parsed_json)
    except Exception:
        return None

    if not isinstance(parsed, dict):
        return None

    # Skip decoder failures that only contain debug/error info.
    if parsed.get("_decode_error") is True:
        return None

    ccsds_packet = get_ccsds_space_packet(parsed)
    if ccsds_packet is None:
        return None

    out: dict[str, Any] = {}
    out["timestamp"] = row["timestamp_utc"]
    out["observer"] = row["observer"]

    out.update(flatten_primary_header(ccsds_packet))
    out.update(flatten_secondary_header(ccsds_packet))
    out.update(flatten_user_data(ccsds_packet))

    return out


def order_columns(rows: list[dict[str, Any]]) -> list[str]:
    """
    Order CSV columns as:
    - timestamp
    - observer
    - primary header fields
    - secondary header fields
    - user data fields
    """
    all_columns: set[str] = set()
    for row in rows:
        all_columns.update(row.keys())

    leading = [c for c in ["timestamp", "observer"] if c in all_columns]

    primary_order = [
        "ccsds_version",
        "packet_type",
        "secondary_header_flag",
        "is_stored_data",
        "application_process_id",
        "grouping_flag",
        "sequence_count",
        "packet_length",
    ]
    secondary_order = [
        "time_stamp_seconds",
        "sub_seconds",
        "padding",
    ]

    primary_present = [c for c in primary_order if c in all_columns]
    secondary_present = [c for c in secondary_order if c in all_columns]

    already_used = set(leading + primary_present + secondary_present)
    user_data_columns = sorted(c for c in all_columns if c not in already_used)

    return leading + primary_present + secondary_present + user_data_columns


def export_apid_csvs(
    db,
    norad_cat_id: int,
    outdir: str,
) -> list[str]:
    """
    Export one CSV per APID for a NORAD ID from parsed SQLite rows.
    """
    rows = db.get_recent_parsed_rows(limit=1_000_000)

    # Keep only the requested NORAD and rows with parsed_json content.
    rows = [row for row in rows if int(row["norad_cat_id"]) == int(norad_cat_id)]

    grouped: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        csv_row = build_row_from_db_row(row)
        if csv_row is None:
            continue

        apid = row["ccsds_apid"]
        apid_key = f"{int(apid):03d}" if apid is not None else "unknown"
        grouped.setdefault(apid_key, []).append(csv_row)

    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: list[str] = []

    for apid_key, apid_rows in sorted(grouped.items(), key=lambda kv: kv[0]):
        apid_rows = sorted(
            apid_rows,
            key=lambda r: (r.get("timestamp") is None, r.get("timestamp", "")),
        )

        columns = order_columns(apid_rows)
        outpath = output_dir / f"apid_{apid_key}.csv"

        with outpath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in apid_rows:
                writer.writerow(row)

        written_files.append(str(outpath))

    return written_files