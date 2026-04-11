"""
Command-line interface for the SatNOGS telemetry backend.
"""

from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .db import TelemetryDB
from .ingest import IngestService
from .plotting import plot_field_to_png


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="satnogs-telemetry",
        description="Headless SatNOGS raw/parsed telemetry backend with one DB per satellite",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init-db", help="Initialize the satellite SQLite database schema")
    _add_common_satellite_args(p_init)

    p_sync_latest = subparsers.add_parser("sync-raw-latest", help="Download only new raw packets")
    _add_common_satellite_args(p_sync_latest)

    p_sync_range = subparsers.add_parser("sync-raw-range", help="Download raw packets in a time range")
    _add_common_satellite_args(p_sync_range)
    p_sync_range.add_argument("--start", required=True, help="UTC start time")
    p_sync_range.add_argument("--end", required=False, help="UTC end time")

    p_parse = subparsers.add_parser("parse-unparsed", help="Parse raw rows that do not yet have parsed rows")
    _add_common_satellite_args(p_parse)

    p_show_raw = subparsers.add_parser("show-recent-raw", help="Show recent raw rows")
    _add_common_satellite_args(p_show_raw)
    p_show_raw.add_argument("--limit", type=int, default=20)

    p_show_parsed = subparsers.add_parser("show-recent-parsed", help="Show recent parsed rows")
    _add_common_satellite_args(p_show_parsed)
    p_show_parsed.add_argument("--limit", type=int, default=20)

    p_list = subparsers.add_parser("list-fields", help="List numeric decoded fields available for plotting")
    _add_common_satellite_args(p_list)
    p_list.add_argument("--apid", required=False, type=int)

    p_plot = subparsers.add_parser("plot", help="Plot one decoded numeric field to PNG")
    _add_common_satellite_args(p_plot)
    p_plot.add_argument("--field", required=True)
    p_plot.add_argument("--output", required=True)
    p_plot.add_argument("--apid", required=False, type=int)

    return parser


def _add_common_satellite_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments needed to resolve the per-satellite DB path."""
    parser.add_argument("--norad", required=True, type=int, help="NORAD catalog ID")
    parser.add_argument("--config", required=False, help="Path to config TOML file")


def _load_runtime(args: argparse.Namespace) -> tuple[TelemetryDB, IngestService]:
    """
    Load config, resolve the DB path for the requested NORAD ID,
    and create the database/service objects.
    """
    config = load_config(args.config)
    db_path = config.db_path_for_norad(args.norad)
    db = TelemetryDB(db_path)
    service = IngestService(config=config, db=db, norad_cat_id=args.norad)
    return db, service


def _print(msg: str) -> None:
    """Flush-print helper."""
    print(msg, flush=True)


def cmd_init_db(args: argparse.Namespace) -> int:
    db, _service = _load_runtime(args)
    try:
        db.init_schema()
        _print(f"Initialized database: {db.path}")
        return 0
    finally:
        db.close()


def cmd_sync_raw_latest(args: argparse.Namespace) -> int:
    db, service = _load_runtime(args)
    try:
        db.init_schema()
        result = service.sync_raw_latest(log=_print)
        _print(json.dumps(result.__dict__, indent=2))
        return 0 if not result.errors else 1
    finally:
        db.close()


def cmd_sync_raw_range(args: argparse.Namespace) -> int:
    db, service = _load_runtime(args)
    try:
        db.init_schema()
        result = service.sync_raw_range(start_utc=args.start, end_utc=args.end, log=_print)
        _print(json.dumps(result.__dict__, indent=2))
        return 0 if not result.errors else 1
    finally:
        db.close()


def cmd_parse_unparsed(args: argparse.Namespace) -> int:
    db, service = _load_runtime(args)
    try:
        db.init_schema()
        result = service.parse_unparsed(log=_print)
        _print(json.dumps(result.__dict__, indent=2))
        return 0 if not result.errors else 1
    finally:
        db.close()


def cmd_show_recent_raw(args: argparse.Namespace) -> int:
    db, _service = _load_runtime(args)
    try:
        rows = db.get_recent_raw_rows(limit=args.limit)
        for row in rows:
            print("-" * 80)
            print(f"id         : {row['id']}")
            print(f"norad      : {row['norad_cat_id']}")
            print(f"timestamp  : {row['timestamp_utc']}")
            print(f"observer   : {row['observer']}")
            print(f"raw_json   : {row['raw_json']}")
        return 0
    finally:
        db.close()


def cmd_show_recent_parsed(args: argparse.Namespace) -> int:
    db, _service = _load_runtime(args)
    try:
        rows = db.get_recent_parsed_rows(limit=args.limit)
        for row in rows:
            print("-" * 80)
            print(f"id                   : {row['id']}")
            print(f"norad                : {row['norad_cat_id']}")
            print(f"timestamp            : {row['timestamp_utc']}")
            print(f"observer             : {row['observer']}")
            print(f"dest_callsign        : {row['dest_callsign']}")
            print(f"src_callsign         : {row['src_callsign']}")
            print(f"raw_ax25_frame_hex   : {row['raw_ax25_frame_hex']}")
            print(f"ccsds_apid           : {row['ccsds_apid']}")
            print(f"ccsds_sequence_count : {row['ccsds_sequence_count']}")
            print(f"raw_ccsds_packet_hex : {row['raw_ccsds_packet_hex']}")
            print(f"parsed_json          : {row['parsed_json'] or ''}")
        return 0
    finally:
        db.close()


def cmd_list_fields(args: argparse.Namespace) -> int:
    db, _service = _load_runtime(args)
    try:
        fields = db.get_available_numeric_fields(apid=args.apid)
        for field in fields:
            print(field)
        return 0
    finally:
        db.close()


def cmd_plot(args: argparse.Namespace) -> int:
    db, _service = _load_runtime(args)
    try:
        output = plot_field_to_png(db=db, field_name=args.field, output_path=args.output, apid=args.apid)
        _print(f"Saved plot: {output}")
        return 0
    finally:
        db.close()


def main() -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        return cmd_init_db(args)
    if args.command == "sync-raw-latest":
        return cmd_sync_raw_latest(args)
    if args.command == "sync-raw-range":
        return cmd_sync_raw_range(args)
    if args.command == "parse-unparsed":
        return cmd_parse_unparsed(args)
    if args.command == "show-recent-raw":
        return cmd_show_recent_raw(args)
    if args.command == "show-recent-parsed":
        return cmd_show_recent_parsed(args)
    if args.command == "list-fields":
        return cmd_list_fields(args)
    if args.command == "plot":
        return cmd_plot(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
