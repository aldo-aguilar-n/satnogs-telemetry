"""
Ingest and parse orchestration for a single-satellite database.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Callable

from .config import AppConfig
from .db import TelemetryDB
from .models import RawPacket, SyncResult
from .parser import PacketParser
from .satnogs_client import SatNOGSClient
from .utils import extract_raw_fields_for_indexing, utc_now_iso


LogFunc = Callable[[str], None]


class IngestService:
    """
    High-level service for downloading raw telemetry and parsing stored rows.

    This service is intended to operate on one satellite database at a time.
    """

    def __init__(self, config: AppConfig, db: TelemetryDB, norad_cat_id: int) -> None:
        self.config = config
        self.db = db
        self.norad_cat_id = norad_cat_id
        self.client = SatNOGSClient(
            base_url=config.satnogs_base_url,
            timeout_s=config.request_timeout_s,
        )
        self.packet_parser = PacketParser(config)

    def sync_raw_latest(self, log: LogFunc | None = None) -> SyncResult:
        """Download and store only raw packets newer than the latest row already stored."""
        start_utc = None
        last_ts = self.db.get_last_raw_timestamp()

        if last_ts:
            last_dt = dt.datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            start_utc = (last_dt + dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z")

            if log:
                log(f"Resuming raw download after latest stored packet: {start_utc}")

        return self.sync_raw_range(start_utc=start_utc, end_utc=None, log=log)

    def sync_raw_range(
        self,
        start_utc: str | None,
        end_utc: str | None,
        log: LogFunc | None = None,
    ) -> SyncResult:
        """Download raw SatNOGS packets and store them unchanged."""
        result = SyncResult()

        if log:
            log(f"Fetching raw SatNOGS telemetry for NORAD {self.norad_cat_id}...")

        packets = self.client.fetch_telemetry(
            norad_cat_id=self.norad_cat_id,
            start_utc=start_utc,
            end_utc=end_utc,
        )
        result.total_seen = len(packets)

        if log:
            log(f"Fetched {len(packets)} raw packets")

        for idx, packet in enumerate(packets, start=1):
            try:
                timestamp_utc, observer = extract_raw_fields_for_indexing(packet)

                raw = RawPacket(
                    norad_cat_id=self.norad_cat_id,
                    timestamp_utc=timestamp_utc,
                    observer=observer,
                    raw_json=packet,
                )

                _, inserted = self.db.insert_raw_packet(
                    raw=raw,
                    inserted_utc=utc_now_iso(),
                    source=self.config.source_name,
                )

                if inserted:
                    result.raw_inserted += 1
                else:
                    result.raw_existing += 1

                if log and idx % 100 == 0:
                    log(
                        f"Stored {idx}/{len(packets)} raw packets | "
                        f"new={result.raw_inserted} existing={result.raw_existing}"
                    )

            except Exception as exc:
                result.errors.append(f"Raw packet {idx}: {exc}")

        return result

    def parse_unparsed(self, log: LogFunc | None = None) -> SyncResult:
        """Parse raw rows in this satellite DB that do not yet have parsed entries."""
        result = SyncResult()
        rows = self.db.iter_unparsed_raw_rows()
        result.total_seen = len(rows)

        if log:
            log(f"Parsing {len(rows)} unparsed raw rows for NORAD {self.norad_cat_id}")

        for idx, row in enumerate(rows, start=1):
            try:
                raw_json = json.loads(row["raw_json"])

                parsed = self.packet_parser.parse_raw_packet(
                    raw_frame_id=int(row["id"]),
                    norad_cat_id=self.norad_cat_id,
                    raw_json=raw_json,
                )

                self.db.insert_parsed_packet(parsed=parsed, inserted_utc=utc_now_iso())
                result.parsed_inserted += 1

                if log and idx % 100 == 0:
                    log(f"Parsed {idx}/{len(rows)} rows | inserted={result.parsed_inserted}")

            except Exception as exc:
                result.parse_errors += 1
                result.errors.append(f"Parse row {row['id']}: {exc}")

        return result
