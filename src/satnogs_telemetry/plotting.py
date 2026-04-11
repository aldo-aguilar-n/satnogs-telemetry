"""
Headless plotting helpers.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

# Use a non-interactive backend for headless environments.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .db import TelemetryDB


def plot_field_to_png(
    db: TelemetryDB,
    field_name: str,
    output_path: str | Path,
    apid: int | None = None,
) -> Path:
    """Plot one decoded numeric field to a PNG file."""
    xs, ys = db.get_series_points(field_name=field_name, apid=apid)
    if not xs:
        raise ValueError(f"No numeric samples found for field: {field_name}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots()
    ax.plot(xs, ys)
    ax.set_title(field_name if apid is None else f"APID {apid}: {field_name}")
    ax.set_xlabel("Timestamp (UTC)")
    ax.set_ylabel(field_name)
    ax.grid(True)

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return output
