"""
Command-line interface for the SatNOGS telemetry backend.

The CLI is intentionally thin.  It only:
- defines commands and arguments
- opens the needed service objects
- prints human-readable progress and summaries
- routes the command to the correct module
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
import sys

from dotenv import load_dotenv

from .csv_export import export_apid_csvs
from .database import TelemetryDB
from .decode import DecoderManager, DecoderService
from .download import DownloadService
from .plotting import plot_field_to_png

def _result_errors(obj):
    """
    Return the 'errors' field from either a dataclass result object or a dict.
    """
    if isinstance(obj, dict):
        return obj.get("errors", [])
    return getattr(obj, "errors", [])

def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser and all subcommands."""
    parser = argparse.ArgumentParser(
        prog="satnogs-telemetry",
        description="Headless SatNOGS telemetry backend",
    )
    parser.add_argument("--norad", type=int, help="NORAD catalog ID")
    parser.add_argument("--no-prompt", action="store_true", help="Do not ask interactively for decoder selection")
    subparsers = parser.add_subparsers(dest="command")

    p_init = subparsers.add_parser("init-db", help="Initialize the satellite SQLite database schema")
    _add_satellite_args(p_init)

    p_sync_latest = subparsers.add_parser("sync-raw-latest", help="Download only new raw packets")
    _add_satellite_args(p_sync_latest)

    p_sync_range = subparsers.add_parser("sync-raw-range", help="Download raw packets in a specific time range")
    _add_satellite_args(p_sync_range)
    p_sync_range.add_argument("--start", required=True, help="UTC start time, e.g. 2026-04-11T00:00:00Z")
    p_sync_range.add_argument("--end", required=False, help="UTC end time, e.g. 2026-04-12T00:00:00Z")

    p_parse = subparsers.add_parser("parse-unparsed", help="Parse raw rows that do not yet have parsed rows")
    _add_satellite_args(p_parse)

    p_reparse_all = subparsers.add_parser(
        "reparse-all",
        help="Delete existing parsed rows and rebuild them from raw rows",
    )
    _add_satellite_args(p_reparse_all)

    p_export_csv = subparsers.add_parser("export-csv", help="Export one CSV per APID")
    _add_satellite_args(p_export_csv)
    p_export_csv.add_argument("--outdir", default="csv", help="Output directory for APID CSV files")

    p_show_raw = subparsers.add_parser("show-recent-raw", help="Show recent raw rows")
    _add_satellite_args(p_show_raw)
    p_show_raw.add_argument("--limit", type=int, default=20)

    p_show_parsed = subparsers.add_parser("show-recent-parsed", help="Show recent parsed rows")
    _add_satellite_args(p_show_parsed)
    p_show_parsed.add_argument("--limit", type=int, default=20)

    p_list = subparsers.add_parser("list-fields", help="List numeric decoded fields available for plotting")
    _add_satellite_args(p_list)
    p_list.add_argument("--apid", required=False, type=int)

    p_plot = subparsers.add_parser("plot", help="Plot one decoded numeric field to PNG")
    _add_satellite_args(p_plot)
    p_plot.add_argument("--field", required=True)
    p_plot.add_argument("--output", required=True)
    p_plot.add_argument("--apid", required=False, type=int)

    return parser


def _add_satellite_args(parser: argparse.ArgumentParser) -> None:
    """Add the common NORAD-related arguments shared by most subcommands."""
    parser.add_argument("--norad", required=True, type=int, help="NORAD catalog ID")
    parser.add_argument("--no-prompt", action="store_true", help="Do not ask interactively for decoder selection")


def _print(msg: str) -> None:
    """Flush-print helper used for progress updates."""
    print(msg, flush=True)


def _open_services(args: argparse.Namespace) -> tuple[TelemetryDB, DownloadService, DecoderService]:
    """
    Open the DB plus the download/decode services needed by most commands.

    ``load_dotenv()`` happens here so every command sees the SatNOGS token from
    the local ``.env`` file.
    """
    load_dotenv()
    db = TelemetryDB(args.norad)
    db.init_schema()
    download_service = DownloadService(db)
    decoder_service = DecoderService(db)
    return db, download_service, decoder_service


def _ensure_decoder_selected(norad_cat_id: int, no_prompt: bool) -> None:
    """
    Ensure a decoder mapping exists for this NORAD ID.

    If a mapping is already present in config.toml, do nothing.
    If not, either prompt the user to choose one or skip prompting when
    --no-prompt was requested.
    """
    from .decode import load_decoder_mapping

    mapping = load_decoder_mapping()

    if norad_cat_id in mapping:
        return

    if no_prompt:
        _print(f"No decoder configured for NORAD {norad_cat_id}; continuing without prompt.")
        return

    manager = DecoderManager()
    manager.resolve_decoder(norad_cat_id)
    _print(f"Decoder configured for NORAD {norad_cat_id}.")


def cmd_default_run(args: argparse.Namespace) -> int:
    """
    Default command used when no subcommand is provided.

    This performs the normal day-to-day workflow:
    1. sync new raw packets
    2. parse unparsed raw rows
    """
    if args.norad is None:
        print("error: --norad is required")
        return 2

    db, downloader, decoder = _open_services(args)
    try:
        _print(f"Using database: {db.path}")
        _ensure_decoder_selected(args.norad, args.no_prompt)

        raw_result = downloader.sync_raw_latest(norad_cat_id=args.norad, log=_print)
        _print("Raw sync result:")
        _print(json.dumps(asdict(raw_result), indent=2))

        parse_result = decoder.parse_unparsed(norad_cat_id=args.norad, log=_print)
        _print("Parse result:")
        _print(json.dumps(parse_result, indent=2))

        had_errors = bool(_result_errors(raw_result) or _result_errors(parse_result))
        return 1 if had_errors else 0
    finally:
        db.close()


def cmd_init_db(args: argparse.Namespace) -> int:
    """Create/open the NORAD database and initialize the schema."""
    db, _downloader, _decoder = _open_services(args)
    try:
        _print(f"Initialized database: {db.path}")
        return 0
    finally:
        db.close()


def cmd_sync_raw_latest(args: argparse.Namespace) -> int:
    """Sync only packets newer than the latest stored raw row."""
    db, downloader, _decoder = _open_services(args)
    try:
        result = downloader.sync_raw_latest(norad_cat_id=args.norad, log=_print)
        _print(json.dumps(asdict(result), indent=2))
        return 0 if not _result_errors(result) else 1
    finally:
        db.close()


def cmd_sync_raw_range(args: argparse.Namespace) -> int:
    """Sync packets within an explicit time range."""
    db, downloader, _decoder = _open_services(args)
    try:
        result = downloader.sync_raw_range(
            norad_cat_id=args.norad,
            start_utc=args.start,
            end_utc=args.end,
            log=_print,
        )
        _print(json.dumps(asdict(result), indent=2))
        return 0 if not _result_errors(result) else 1
    finally:
        db.close()


def cmd_parse_unparsed(args: argparse.Namespace) -> int:
    """Parse only raw rows that do not already have parsed rows."""
    db, _downloader, decoder = _open_services(args)
    try:
        _ensure_decoder_selected(args.norad, args.no_prompt)
        result = decoder.parse_unparsed(norad_cat_id=args.norad, log=_print)
        _print(json.dumps(result, indent=2))
        return 0 if not _result_errors(result) else 1
    finally:
        db.close()


def cmd_reparse_all(args: argparse.Namespace) -> int:
    """
    Delete existing parsed rows for this NORAD and rebuild them from raw rows.
    """
    db, _downloader, decoder = _open_services(args)
    try:
        _ensure_decoder_selected(args.norad, args.no_prompt)
        deleted = db.delete_parsed_rows_for_norad(args.norad)
        _print(f"Deleted {deleted} existing parsed rows for NORAD {args.norad}")
        result = decoder.parse_unparsed(norad_cat_id=args.norad, log=_print)
        _print(json.dumps(result, indent=2))
        return 0 if not _result_errors(result) else 1
    finally:
        db.close()


def cmd_export_csv(args: argparse.Namespace) -> int:
    """Export one CSV per APID for the requested NORAD ID."""
    db, _downloader, _decoder = _open_services(args)
    try:
        written = export_apid_csvs(db=db, norad_cat_id=args.norad, outdir=args.outdir)
        _print(f"Wrote {len(written)} CSV files to {args.outdir}")
        for path in written:
            _print(path)
        return 0
    finally:
        db.close()


def cmd_show_recent_raw(args: argparse.Namespace) -> int:
    """Print a few recent raw rows for inspection/debugging."""
    db, _downloader, _decoder = _open_services(args)
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
    """Print a few recent parsed rows for inspection/debugging."""
    db, _downloader, _decoder = _open_services(args)
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
    """Print the numeric decoded field names available for plotting."""
    db, _downloader, _decoder = _open_services(args)
    try:
        fields = db.get_available_numeric_fields(apid=args.apid)
        for field in fields:
            print(field)
        return 0
    finally:
        db.close()


def cmd_plot(args: argparse.Namespace) -> int:
    """Plot one decoded field and write it to a PNG file."""
    db, _downloader, _decoder = _open_services(args)
    try:
        output = plot_field_to_png(db=db, field_name=args.field, output_path=args.output, apid=args.apid)
        _print(f"Saved plot: {output}")
        return 0
    finally:
        db.close()


def main() -> int:
    """CLI entry point used by the Poetry script definition."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        return cmd_default_run(args)
    if args.command == "init-db":
        return cmd_init_db(args)
    if args.command == "sync-raw-latest":
        return cmd_sync_raw_latest(args)
    if args.command == "sync-raw-range":
        return cmd_sync_raw_range(args)
    if args.command == "parse-unparsed":
        return cmd_parse_unparsed(args)
    if args.command == "reparse-all":
        return cmd_reparse_all(args)
    if args.command == "export-csv":
        return cmd_export_csv(args)
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
