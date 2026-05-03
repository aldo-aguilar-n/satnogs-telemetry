"""
Title: cli.py
Authors: Aldo Aguilar
Date: 2026-05-03
Description: Entry point for the SatNOGS telemetry downloader and parser
application. This application allows the user to:
- Download raw telemetry packets from the SatNOGS API for a specified
  NORAD ID
- Parse the raw packets into structured data using satnogs-decoders
- Store raw and parsed telemetry in a local SQLite database
- Export parsed data to CSV files
- Plot decoded numeric fields to PNG files
"""

# System imports
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
import sys

# Third-party imports
from dotenv import load_dotenv

# Local imports
from .csv_export import export_apid_csvs
from .database import TelemetryDB
from .decode import (
    DecoderManager,
    DecoderService,
    create_and_save_conversion_lookup,
    load_decoder_mapping,
)
from .download import DownloadService
from .plotting import plot_field_to_png

# ------------------------------ Helpers -------------------------------

def _result_errors(obj):
    """
    Return the 'errors' field from either a dataclass result object or a
    dict.
    """
    if isinstance(obj, dict):
        return obj.get("errors", [])
    return getattr(obj, "errors", [])

def _print(msg: str) -> None:
    """
    Flush-print helper used for progress updates.
    """
    print(msg, flush=True)

# -------------------------- Arguments Parser --------------------------

def _build_parser() -> argparse.ArgumentParser:
    """
    Build the top-level CLI parser and all subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="satnogs-telemetry",
        description="SatNOGS telemetry downloader and parser",
    )

    # Global argument
    parser.add_argument("--norad", type=int, 
                        help="NORAD catalog ID")
    
    # Subparsers for specific commands
    subparsers = parser.add_subparsers(dest="command")

    # Arguments for the 'sync-raw-latest' command
    p_sync_latest = subparsers.add_parser(
        "sync-raw-latest", 
        help="Download only new raw packets"
    )
    p_sync_latest.add_argument("--norad", required=True, type=int, 
                               help="NORAD catalog ID")

    # Arguments for the 'sync-raw-range' command
    p_sync_range = subparsers.add_parser(
        "sync-raw-range", 
        help="Download raw packets in a specific time range. Useful for" \
        " backfilling or re-downloading specific periods."
    )
    p_sync_range.add_argument("--norad", required=True, type=int, 
                              help="NORAD catalog ID")
    p_sync_range.add_argument("--start", required=True, 
                              help="UTC start time, e.g. 2026-04-11T00:00:00Z")
    p_sync_range.add_argument("--end", required=False, 
                              help="UTC end time, e.g. 2026-04-12T00:00:00Z")

    # Arguments for the 'parse-unparsed' command
    p_parse = subparsers.add_parser(
        "parse-unparsed", 
        help="Parse raw rows that do not yet have parsed rows"
    )
    p_parse.add_argument("--norad", required=True, type=int, 
                         help="NORAD catalog ID")
    p_parse.add_argument("--start", required=False,
                         help="Optional UTC start time, e.g. 2026-04-11T00:00:00Z")
    p_parse.add_argument("--end", required=False,
                         help="Optional UTC end time, e.g. 2026-04-12T00:00:00Z")

    # Arguments for the 'reparse-all' command
    p_reparse_all = subparsers.add_parser(
        "reparse-all",
        help="Delete existing parsed rows and rebuild them from raw rows",
    )
    p_reparse_all.add_argument("--norad", required=True, type=int, 
                               help="NORAD catalog ID")

    # Arguments for the 'reparse-range' command
    p_reparse_range = subparsers.add_parser(
        "reparse-range",
        help="Delete and rebuild parsed rows within a specific timestamp range",
    )
    p_reparse_range.add_argument("--norad", required=True, type=int, 
                                 help="NORAD catalog ID")
    p_reparse_range.add_argument("--start", required=True,
                                 help="UTC start time, e.g. 2026-04-11T00:00:00Z")
    p_reparse_range.add_argument("--end", required=False,
                                 help="UTC end time, e.g. 2026-04-12T00:00:00Z")

    # Arguments for the 'load-conversions' command
    p_load_conversions = subparsers.add_parser(
        "load-conversions",
        help="Load a beacon definition CSV and save a conversion lookup table"
    )
    p_load_conversions.add_argument("--norad", required=True, type=int,
                                    help="NORAD catalog ID")
    p_load_conversions.add_argument("--input", required=True,
                                    help="Input beacon definition CSV")

    # Arguments for the 'export-csv' command
    p_export_csv = subparsers.add_parser(
        "export-csv", 
        help="Export one CSV per APID"
    )
    p_export_csv.add_argument("--norad", required=True, type=int, 
                              help="NORAD catalog ID")
    p_export_csv.add_argument("--outdir", default="csv", 
                              help="Output directory for APID CSV files")

    # Arguments for the 'dump-parsed-json' command
    p_dump_json = subparsers.add_parser(
        "dump-parsed-json",
        help="Dump compact parsed-frame archive JSON"
    )
    p_dump_json.add_argument("--norad", required=True, type=int,
                             help="NORAD catalog ID")
    p_dump_json.add_argument("--output", required=True,
                             help="Output JSON file")
    p_dump_json.add_argument("--start", required=False,
                             help="Optional UTC start time, e.g. 2026-04-11T00:00:00Z")
    p_dump_json.add_argument("--end", required=False,
                             help="Optional UTC end time, e.g. 2026-04-12T00:00:00Z")

    # Arguments for the 'show-recent-raw' command
    p_show_raw = subparsers.add_parser(
        "show-recent-raw", 
        help="Show recent raw rows"
    )
    p_show_raw.add_argument("--norad", required=True, type=int, 
                            help="NORAD catalog ID")
    p_show_raw.add_argument("--limit", type=int, default=5,
                            help="Number of recent rows to show")

    # Arguments for the 'show-recent-parsed' command
    p_show_parsed = subparsers.add_parser(
        "show-recent-parsed", 
        help="Show recent parsed rows"
    )
    p_show_parsed.add_argument("--norad", required=True, type=int, 
                               help="NORAD catalog ID")
    p_show_parsed.add_argument("--limit", type=int, default=5,
                               help="Number of recent rows to show")

    # Arguments for the 'list-fields' command
    p_list = subparsers.add_parser(
        "list-fields", 
        help="List numeric decoded fields available for plotting"
    )
    p_list.add_argument("--norad", required=True, type=int, 
                        help="NORAD catalog ID")
    p_list.add_argument("--apid", required=False, type=int,
                        help="Optional APID to filter fields by")

    # Arguments for the 'plot' command
    p_plot = subparsers.add_parser(
        "plot", 
        help="Plot one decoded numeric field to PNG"
    )
    p_plot.add_argument("--norad", required=True, type=int, 
                        help="NORAD catalog ID")
    p_plot.add_argument("--field", required=True,
                        help="Field to plot")
    p_plot.add_argument("--output", required=True,
                        help="Output PNG file")
    p_plot.add_argument("--apid", required=False, type=int, 
                        help="Optional APID to filter by")

    return parser

# ---------------------------- CLI Commands ----------------------------

def _open_services(args: argparse.Namespace) -> tuple[TelemetryDB, 
                                                      DownloadService, 
                                                      DecoderService]:
    """
    Open the DB plus the download/decode services needed by most 
    commands.

    'load_dotenv()' happens here so every command sees the SatNOGS
    token from the local '.env' file.
    """
    load_dotenv()

    # Open database service (create database if it doesn't exist)
    db = TelemetryDB(args.norad)
    db.init_schema()

    # Open download service
    download_service = DownloadService(db)

    # Open decoder service
    decoder_service = DecoderService(db)

    return db, download_service, decoder_service

def _ensure_decoder_selected(norad_cat_id: int) -> None:
    """
    Ensure a decoder mapping exists for this NORAD ID.

    If a mapping is already present in config.toml, do nothing.
    If not, either prompt the user to choose one.
    """
    mapping = load_decoder_mapping()
    if norad_cat_id in mapping:
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
        print("ERROR: --norad is required")
        return 2

    # Open services (DB, downloader, decoder)
    db, downloader, decoder = _open_services(args)
    try:
        _print(f"Using database: {db.path}")

        # Ensure a decoder is selected for this NORAD ID before 
        # downloading
        _ensure_decoder_selected(args.norad)

        # Sync new raw packets from SatNOGS
        raw_result = downloader.sync_raw_latest(norad_cat_id=args.norad, 
                                                log=_print)
        _print("Raw sync result:")
        _print(json.dumps(asdict(raw_result), indent=2))

        # Parse unparsed raw rows
        parse_result = decoder.parse_unparsed(norad_cat_id=args.norad, 
                                              log=_print)
        _print("Parse result:")
        _print(json.dumps(parse_result, indent=2))

        # Return exit code
        had_errors = bool(_result_errors(raw_result) or 
                          _result_errors(parse_result))
        return 1 if had_errors else 0
    finally:
        db.close()

def cmd_sync_raw_latest(args: argparse.Namespace) -> int:
    """
    Sync only packets newer than the latest stored raw row.
    """
    # Open services (DB, downloader)
    db, downloader, _ = _open_services(args)
    try:
        # Sync new raw packets from SatNOGS
        result = downloader.sync_raw_latest(norad_cat_id=args.norad, 
                                            log=_print)
        _print("Raw sync latest result:")
        _print(json.dumps(asdict(result), indent=2))
        # Return exit code
        return 0 if not _result_errors(result) else 1
    finally:    
        db.close()

def cmd_sync_raw_range(args: argparse.Namespace) -> int:
    """
    Sync packets within an explicit time range. This is useful for
    backfilling or re-downloading specific periods.
    """
    # Open services (DB, downloader)
    db, downloader, _ = _open_services(args)
    try:
        # Sync raw packets from SatNOGS in the requested time range
        result = downloader.sync_raw_range(
            norad_cat_id=args.norad,
            start_utc=args.start,
            end_utc=args.end,
            log=_print,
        )
        _print("Raw sync range result:")
        _print(json.dumps(asdict(result), indent=2))
        # Return exit code
        return 0 if not _result_errors(result) else 1
    finally:
        db.close()

def cmd_parse_unparsed(args: argparse.Namespace) -> int:
    """
    Parse only raw rows that do not already have parsed rows.
    """
    # Open services (DB, decoder)
    db, _, decoder = _open_services(args)
    try:
        # Ensure a decoder is selected for this NORAD ID before 
        # downloading
        _ensure_decoder_selected(args.norad)
        # Parse unparsed raw rows
        result = decoder.parse_unparsed(norad_cat_id=args.norad, 
                                        log=_print,
                                        start_utc=args.start,
                                        end_utc=args.end)
        _print(json.dumps(result, indent=2))
        # Return exit code
        return 0 if not _result_errors(result) else 1
    finally:
        db.close()

def cmd_reparse_all(args: argparse.Namespace) -> int:
    """
    Delete existing parsed rows for this NORAD and rebuild them from raw
    rows.
    """
    db, _, decoder = _open_services(args)
    try:
        # Ensure a decoder is selected for this NORAD ID before 
        # downloading
        _ensure_decoder_selected(args.norad)
        # Delete existing parsed rows for this NORAD ID before reparsing
        deleted = db.delete_parsed_rows()
        _print(f"Deleted {deleted} existing parsed rows for NORAD "
               f"{args.norad}")
        # Reparse all raw rows
        result = decoder.parse_unparsed(norad_cat_id=args.norad, 
                                        log=_print)
        _print(json.dumps(result, indent=2))
        # Return exit code
        return 0 if not _result_errors(result) else 1
    finally:
        db.close()

def cmd_reparse_range(args: argparse.Namespace) -> int:
    """
    Delete existing parsed rows in a timestamp range and rebuild them
    from raw rows in the same range.
    """
    db, _, decoder = _open_services(args)
    try:
        # Ensure a decoder is selected for this NORAD ID before 
        # reparsing.
        _ensure_decoder_selected(args.norad)
        # Delete existing parsed rows in this timestamp range.
        deleted = db.delete_parsed_rows(start_utc=args.start,
                                                  end_utc=args.end)
        _print(
            f"Deleted {deleted} parsed rows for NORAD {args.norad} "
            f"from {args.start or '-inf'} to {args.end or '+inf'}"
        )
        # Reparse raw rows in this timestamp range.
        result = decoder.parse_unparsed(norad_cat_id=args.norad,
                                        log=_print,
                                        start_utc=args.start,
                                        end_utc=args.end)
        _print(json.dumps(result, indent=2))
        # Return exit code
        return 0 if not _result_errors(result) else 1
    finally:
        db.close()

def cmd_load_conversions(args: argparse.Namespace) -> int:
    """
    Load a beacon definition CSV and save the per-NORAD conversion lookup.
    """
    outpath = create_and_save_conversion_lookup(
        norad_cat_id=args.norad,
        csv_path=args.input,
    )
    _print(f"Saved conversion lookup: {outpath}")
    return 0

def cmd_export_csv(args: argparse.Namespace) -> int:
    """
    Export one CSV per APID for the requested NORAD ID.
    """
    # Open services (DB)
    db, _, _ = _open_services(args)
    try:
        # Export CSV files for this NORAD ID
        written = export_apid_csvs(db=db, norad_cat_id=args.norad, 
                                   outdir=args.outdir)
        _print(f"Wrote {len(written)} CSV files to {args.outdir}")
        for path in written:
            _print(path)
        return 0
    finally:
        db.close()

def cmd_dump_parsed_json(args: argparse.Namespace) -> int:
    """
    Dump compact parsed-frame archive JSON.

    Each record contains only:
    - timestamp_utc
    - observer
    - raw_ccsds_packet_hex
    """
    # Open services (DB)
    db, _, _ = _open_services(args)
    try:
        # Dump compact archive JSON for this NORAD ID.
        outpath = db.dump_parsed_archive_json(output_path=args.output,
                                              start_utc=args.start,
                                              end_utc=args.end)
        _print(f"Wrote parsed archive JSON: {outpath}")
        return 0
    finally:
        db.close()

def cmd_show_recent_raw(args: argparse.Namespace) -> int:
    """
    Print a few recent raw rows for inspection/debugging.
    """
    # Open services (DB)
    db, _, _ = _open_services(args)
    try:
        # Fetch and print recent raw rows for this NORAD ID
        rows = db.get_recent_raw_rows(limit=args.limit)
        for row in rows:
            print("-" * 80)
            print(f"id         : {row['id']}")
            print(f"timestamp  : {row['timestamp_utc']}")
            print(f"observer   : {row['observer']}")
            print(f"raw_json   : {row['raw_json']}")
        return 0
    finally:
        db.close()

def cmd_show_recent_parsed(args: argparse.Namespace) -> int:
    """
    Print a few recent parsed rows for inspection/debugging.
    """
    # Open services (DB)
    db, _, _ = _open_services(args)
    try:
        # Fetch and print recent parsed rows for this NORAD ID
        rows = db.get_recent_parsed_rows(limit=args.limit)
        for row in rows:
            print("-" * 80)
            print(f"raw_frame_id         : {row['raw_frame_id']}")
            print(f"timestamp            : {row['timestamp_utc']}")
            print(f"observer             : {row['observer']}")
            print(f"dest_callsign        : {row['dest_callsign']}")
            print(f"src_callsign         : {row['src_callsign']}")
            print(f"raw_ax25_frame_hex   : {row['raw_ax25_frame_hex']}")
            print(f"ccsds_apid           : {row['ccsds_apid']}")
            print(f"ccsds_sequence_count : {row['ccsds_sequence_count']}")
            print(f"raw_ccsds_packet_hex : {row['raw_ccsds_packet_hex']}")
            print(f"parsed_json          : {row['parsed_json'] or ''}")
            print(f"parsed_json_eng      : {row['parsed_json_eng'] or ''}")
        return 0
    finally:
        db.close()

def cmd_list_fields(args: argparse.Namespace) -> int:
    """
    Print the numeric decoded field names available for plotting.
    """
    # Open services (DB)
    db, _, _ = _open_services(args)
    try:
        # Fetch and print available numeric decoded fields for NORAD ID
        fields = db.get_available_numeric_fields(apid=args.apid)
        for field in fields:
            print(field)
        return 0
    finally:
        db.close()

def cmd_plot(args: argparse.Namespace) -> int:
    """
    Plot one decoded field and write it to a PNG file.
    """
    # Open services (DB)
    db, _, _ = _open_services(args)
    try:
        # Plot the requested field and save to the requested output path
        output = plot_field_to_png(db=db, 
                                   field_name=args.field, 
                                   output_path=args.output, 
                                   apid=args.apid)
        _print(f"Saved plot: {output}")
        return 0
    finally:
        db.close()

# -------------------------- Main Entry Point --------------------------

def main() -> int:
    """
    CLI entry point
    """
    parser = _build_parser()
    args = parser.parse_args()

    # Default execution route
    if args.command is None:
        return cmd_default_run(args)
    
    # Subcommand execution routes
    if args.command == "sync-raw-latest":
        return cmd_sync_raw_latest(args)
    if args.command == "sync-raw-range":
        return cmd_sync_raw_range(args)
    if args.command == "parse-unparsed":
        return cmd_parse_unparsed(args)
    if args.command == "reparse-all":
        return cmd_reparse_all(args)
    if args.command == "reparse-range":
        return cmd_reparse_range(args)
    if args.command == "load-conversions":
        return cmd_load_conversions(args)
    if args.command == "export-csv":
        return cmd_export_csv(args)
    if args.command == "dump-parsed-json":
        return cmd_dump_parsed_json(args)
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

# ----------------------------------------------------------------------