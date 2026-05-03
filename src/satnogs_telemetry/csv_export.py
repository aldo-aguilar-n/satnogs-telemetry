"""
Title: csv_export.py
Authors: Aldo Aguilar
Date: 2026-05-03
Description: CSV export helpers for parsed telemetry.

This module exports two CSVs per APID when conversion lookup tables are
available:
- apid_XXX_raw.csv from parsed_json
- apid_XXX_eng.csv from parsed_json_eng or converted parsed_json fallback

If no conversion lookup table exists for the NORAD ID, only raw CSVs are
written because engineering CSVs would be exact copies.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .decode import (
    apply_conversions_to_parsed_json,
    load_conversion_lookup,
)

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

def _load_json_payload(text: Any) -> dict[str, Any] | None:
    if not text:
        return None

    try:
        payload = json.loads(text)
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None

def _is_usable_payload(parsed: dict[str, Any] | None) -> bool:
    if not isinstance(parsed, dict):
        return False

    if parsed.get("_decode_error") is True:
        return False

    return get_ccsds_space_packet(parsed) is not None

def build_row_from_payload(
    row: Any,
    parsed: dict[str, Any],
) -> tuple[dict[str, Any], list[str]] | None:
    if not _is_usable_payload(parsed):
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

def build_raw_row_from_db_row(row: Any) -> tuple[dict[str, Any], list[str]] | None:
    parsed = _load_json_payload(row["parsed_json"])
    if parsed is None:
        return None

    return build_row_from_payload(row, parsed)

def build_eng_row_from_db_row(
    row: Any,
    conversion_lookup: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]] | None:
    parsed_eng = None

    if "parsed_json_eng" in row.keys():
        parsed_eng = _load_json_payload(row["parsed_json_eng"])

    if parsed_eng is None:
        parsed_raw = _load_json_payload(row["parsed_json"])
        if parsed_raw is None:
            return None

        parsed_eng = apply_conversions_to_parsed_json(
            parsed_raw,
            conversion_lookup,
        )

    return build_row_from_payload(row, parsed_eng)

def order_columns(
    rows: list[dict[str, Any]],
    ordered_column_lists: list[list[str]],
) -> list[str]:
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

def _write_grouped_csvs(
    grouped: dict[str, list[dict[str, Any]]],
    grouped_order_lists: dict[str, list[list[str]]],
    output_dir: Path,
    suffix: str,
) -> list[str]:
    written_files: list[str] = []

    for apid_key, apid_rows in sorted(grouped.items(), key=lambda kv: kv[0]):
        columns = order_columns(apid_rows, grouped_order_lists.get(apid_key, []))
        outpath = output_dir / f"apid_{apid_key}_{suffix}.csv"

        with outpath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in apid_rows:
                writer.writerow(row)

        written_files.append(str(outpath))

    return written_files

def _add_row_to_group(
    row: Any,
    built: tuple[dict[str, Any], list[str]] | None,
    grouped: dict[str, list[dict[str, Any]]],
    grouped_order_lists: dict[str, list[list[str]]],
) -> None:
    if built is None:
        return

    csv_row, ordered_columns = built
    apid = row["ccsds_apid"]
    apid_key = f"{int(apid):03d}" if apid is not None else "unknown"

    grouped.setdefault(apid_key, []).append(csv_row)
    grouped_order_lists.setdefault(apid_key, []).append(ordered_columns)

def export_apid_csvs(db, norad_cat_id: int, outdir: str) -> list[str]:
    rows = db.iter_parsed_rows()
    conversion_lookup = load_conversion_lookup(norad_cat_id)

    raw_grouped: dict[str, list[dict[str, Any]]] = {}
    raw_order_lists: dict[str, list[list[str]]] = {}

    eng_grouped: dict[str, list[dict[str, Any]]] = {}
    eng_order_lists: dict[str, list[list[str]]] = {}

    for row in rows:
        _add_row_to_group(
            row,
            build_raw_row_from_db_row(row),
            raw_grouped,
            raw_order_lists,
        )

        if conversion_lookup:
            _add_row_to_group(
                row,
                build_eng_row_from_db_row(row, conversion_lookup),
                eng_grouped,
                eng_order_lists,
            )

    output_dir = Path(outdir) / str(norad_cat_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: list[str] = []
    written_files.extend(
        _write_grouped_csvs(
            raw_grouped,
            raw_order_lists,
            output_dir,
            suffix="raw",
        )
    )

    if conversion_lookup:
        written_files.extend(
            _write_grouped_csvs(
                eng_grouped,
                eng_order_lists,
                output_dir,
                suffix="eng",
            )
        )

    return written_files

# ----------------------------------------------------------------------