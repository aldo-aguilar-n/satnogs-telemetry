"""
Title: csv_export.py
Authors: Aldo Aguilar
Date: 2026-04-12
Description: CSV export helpers for parsed telemetry.

This module exports one CSV per APID directly from the parsed SQLite
rows. The CSV columns are flattened from the decoded JSON and ordered as
follows:
- Timestamp (UTC observation time as original SatNOGS string)
- Observer (SatNOGS ground station identifier)
- CCSDS primary header fields
- CCSDS secondary header fields
- User data fields

Only decoded payloads that actually contain a usable
'ccsds_space_packet' are included.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


# ------------------------------ Helpers -------------------------------

def flatten_dict(
    obj: Any,
    parent_key: str = "",
    sep: str = ".",
    skip_leaf=None,
) -> dict[str, Any]:
    """
    Flatten nested dict/list structures into a one-level mapping.

    Dict keys become dotted paths, and list indices are appended as
    numeric path components.
    """
    items: dict[str, Any] = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
            items.update(flatten_dict(value, new_key, sep=sep, skip_leaf=skip_leaf))
        return items

    if isinstance(obj, list):
        for i, value in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.update(flatten_dict(value, new_key, sep=sep, skip_leaf=skip_leaf))
        return items

    if parent_key and skip_leaf and skip_leaf(parent_key, obj):
        return items

    items[parent_key] = obj
    return items


def flatten_keys_in_order(
    obj: Any,
    parent_key: str = "",
    sep: str = ".",
    skip_leaf=None,
) -> list[str]:
    """
    Return flattened key paths in encounter order, preserving the order
    from the decoded JSON structure.
    """
    keys: list[str] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
            keys.extend(flatten_keys_in_order(value, new_key, sep=sep, skip_leaf=skip_leaf))
        return keys

    if isinstance(obj, list):
        for i, value in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            keys.extend(flatten_keys_in_order(value, new_key, sep=sep, skip_leaf=skip_leaf))
        return keys

    if parent_key and skip_leaf and skip_leaf(parent_key, obj):
        return keys

    keys.append(parent_key)
    return keys


def _skip_payload_raw_leaf(path: str, value: Any) -> bool:
    """
    Skip payload raw engineering duplicates such as '*_raw'.
    """
    leaf = str(path).split(".")[-1].lower()
    return leaf.endswith("_raw")


def _find_first_key_recursive(obj: Any, target_key: str) -> Any | None:
    """
    Recursively search nested dict/list structures for the first
    matching key.
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
    Retrieve the decoded CCSDS space packet from a parsed payload.
    """
    found = _find_first_key_recursive(parsed, "ccsds_space_packet")
    return found if isinstance(found, dict) else None


def get_primary_header_obj(ccsds_packet: dict[str, Any]) -> dict[str, Any]:
    primary_header = ccsds_packet.get("packet_primary_header", {})
    return primary_header if isinstance(primary_header, dict) else {}


def get_secondary_header_obj(ccsds_packet: dict[str, Any]) -> dict[str, Any]:
    try:
        secondary_header = ccsds_packet["data_section"]["secondary_header"]
    except Exception:
        secondary_header = {}
    return secondary_header if isinstance(secondary_header, dict) else {}


def get_user_data_obj(ccsds_packet: dict[str, Any]) -> Any:
    try:
        user_data = ccsds_packet["data_section"]["user_data_field"]
    except Exception:
        user_data = {}

    if isinstance(user_data, dict) and len(user_data) == 1:
        only_value = next(iter(user_data.values()))
        if isinstance(only_value, dict):
            user_data = only_value

    return user_data


def flatten_primary_header(ccsds_packet: dict[str, Any]) -> dict[str, Any]:
    return flatten_dict(get_primary_header_obj(ccsds_packet))


def flatten_secondary_header(ccsds_packet: dict[str, Any]) -> dict[str, Any]:
    return flatten_dict(get_secondary_header_obj(ccsds_packet))


def flatten_user_data(ccsds_packet: dict[str, Any]) -> dict[str, Any]:
    return flatten_dict(get_user_data_obj(ccsds_packet), skip_leaf=_skip_payload_raw_leaf)


def primary_header_keys_in_order(ccsds_packet: dict[str, Any]) -> list[str]:
    return flatten_keys_in_order(get_primary_header_obj(ccsds_packet))


def secondary_header_keys_in_order(ccsds_packet: dict[str, Any]) -> list[str]:
    return flatten_keys_in_order(get_secondary_header_obj(ccsds_packet))


def user_data_keys_in_order(ccsds_packet: dict[str, Any]) -> list[str]:
    return flatten_keys_in_order(get_user_data_obj(ccsds_packet), skip_leaf=_skip_payload_raw_leaf)


def choose_timestamp_from_observation_time(row_timestamp_utc: Any) -> str:
    """
    Use only the original SatNOGS observation timestamp string for CSV
    export.
    """
    return str(row_timestamp_utc or "").strip()


def build_row_from_db_row(row: Any) -> tuple[dict[str, Any], list[str]] | None:
    """
    Build one flattened CSV row from one parsed SQLite row together with
    the exact column order implied by the decoded JSON structure.

    Rows that only contain decode-error/debug metadata are skipped.
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

    if parsed.get("_decode_error") is True:
        return None

    ccsds_packet = get_ccsds_space_packet(parsed)
    if ccsds_packet is None:
        return None

    primary = flatten_primary_header(ccsds_packet)
    secondary = flatten_secondary_header(ccsds_packet)
    user_data = flatten_user_data(ccsds_packet)

    out: dict[str, Any] = {}
    out["timestamp"] = choose_timestamp_from_observation_time(row["timestamp_utc"])
    out["observer"] = row["observer"]
    out.update(primary)
    out.update(secondary)
    out.update(user_data)

    ordered_columns = (
        ["timestamp", "observer"]
        + primary_header_keys_in_order(ccsds_packet)
        + secondary_header_keys_in_order(ccsds_packet)
        + user_data_keys_in_order(ccsds_packet)
    )

    return out, ordered_columns


def order_columns(rows: list[dict[str, Any]], ordered_column_lists: list[list[str]]) -> list[str]:
    """
    Order CSV columns strictly by first-seen decoder/JSON order across
    rows. No alphabetical sorting is performed.
    """
    final_columns: list[str] = []
    seen: set[str] = set()

    for base_col in ["timestamp", "observer"]:
        if base_col not in seen:
            seen.add(base_col)
            final_columns.append(base_col)

    for ordered_cols in ordered_column_lists:
        for col in ordered_cols:
            if col not in seen:
                seen.add(col)
                final_columns.append(col)

    for row in rows:
        for col in row.keys():
            if col not in seen:
                seen.add(col)
                final_columns.append(col)

    return final_columns


def export_apid_csvs(db, norad_cat_id: int, outdir: str) -> list[str]:
    """
    Export one CSV per APID for a satellite.
    """
    rows = list(reversed(db.get_recent_parsed_rows(limit=1_000_000)))

    grouped: dict[str, list[dict[str, Any]]] = {}
    grouped_order_lists: dict[str, list[list[str]]] = {}

    for row in rows:
        built = build_row_from_db_row(row)
        if built is None:
            continue

        csv_row, ordered_columns = built
        apid = row["ccsds_apid"]
        apid_key = f"{int(apid):03d}" if apid is not None else "unknown"
        grouped.setdefault(apid_key, []).append(csv_row)
        grouped_order_lists.setdefault(apid_key, []).append(ordered_columns)

    output_dir = Path(outdir) / str(norad_cat_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: list[str] = []
    for apid_key, apid_rows in sorted(grouped.items(), key=lambda kv: kv[0]):
        columns = order_columns(apid_rows, grouped_order_lists.get(apid_key, []))
        outpath = output_dir / f"apid_{apid_key}.csv"

        with outpath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in apid_rows:
                writer.writerow(row)

        written_files.append(str(outpath))

    return written_files


# ----------------------------------------------------------------------
