"""
Plotting helpers for decoded telemetry fields.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def _flatten_dict(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """
    Flatten a nested dictionary into dotted-key paths.
    """
    flat: dict[str, Any] = {}

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)

        if isinstance(value, dict):
            flat.update(_flatten_dict(value, full_key))
        else:
            flat[full_key] = value

    return flat


def _short_field_name(field_name: str) -> str:
    """
    Return only the last component of a dotted field path.
    """
    return field_name.split(".")[-1]


def _parse_utc_timestamp(ts: str) -> datetime:
    """
    Convert an ISO UTC timestamp like '2026-04-12T03:02:41Z' to datetime.
    """
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _numeric_series_from_rows(rows: list[Any], field_name: str) -> tuple[list[datetime], list[float]]:
    """
    Extract timestamps and numeric values for one flattened field.
    """
    times: list[datetime] = []
    values: list[float] = []

    for row in rows:
        parsed_json = row["parsed_json"]
        if not parsed_json:
            continue

        try:
            parsed = json.loads(parsed_json)
        except Exception:
            continue

        if not isinstance(parsed, dict):
            continue

        flat = _flatten_dict(parsed)
        value = flat.get(field_name)

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                times.append(_parse_utc_timestamp(row["timestamp_utc"]))
                values.append(float(value))
            except Exception:
                continue

    return times, values


def plot_field_to_png(
    db,
    field_name: str,
    output_path: str,
    apid: int | None = None,
) -> str:
    """
    Plot one numeric decoded field vs timestamp and save to PNG.
    """
    rows = db.get_recent_parsed_rows(limit=100000)

    if apid is not None:
        rows = [row for row in rows if row["ccsds_apid"] == apid]

    times, values = _numeric_series_from_rows(rows, field_name)

    if not times or not values:
        raise ValueError(f"No numeric data found for field: {field_name}")

    # Sort by timestamp so the time series draws correctly.
    paired = sorted(zip(times, values), key=lambda x: x[0])
    times = [p[0] for p in paired]
    values = [p[1] for p in paired]

    output = Path(output_path)

    # Create output directory if needed.
    if output.parent and str(output.parent) not in ("", "."):
        output.parent.mkdir(parents=True, exist_ok=True)

    short_name = _short_field_name(field_name)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(times, values)

    ax.set_title(short_name)
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Eng Units")

    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return str(output)