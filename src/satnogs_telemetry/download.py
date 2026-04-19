"""
Title: download.py
Authors: Aldo Aguilar
Date: 2026-04-12
Description: This module incorporates two classes:
- SatNOGSClient: a minimal HTTP client for the SatNOGS DB API
- DownloadService: a service object that orchestrates downloading 
  packets from SatNOGS (via a SatNOGSClient) and inserting them into the
  raw database table.
"""

# System imports
from __future__ import annotations
from datetime import datetime, timedelta
import os
import time
from typing import Any, Callable

# Third-party imports
import requests

# Local imports
from .database import RawPacket, SyncResult, TelemetryDB
from .decode import extract_raw_fields_for_indexing

# Global constants
SATNOGS_BASE_URL = "https://db.satnogs.org/api/telemetry/"
REQUEST_TIMEOUT_S = 60
PAGE_DELAY_S = 0.75
MAX_RETRIES = 5
LogFunc = Callable[[str], None]

# ------------------------- SatNOGS API Client -------------------------

class SatNOGSClient:
    """
    Minimal HTTP client for the SatNOGS DB telemetry endpoint.

    The API token is loaded from 'SATNOGS_API_TOKEN' in the environment.
    The project README instructs users to place it in '.env', and 
    'cli.py' ensures that file is loaded before commands run.
    """

    def __init__(self) -> None:
        self.base_url = SATNOGS_BASE_URL.rstrip("/") + "/"
        self.timeout_s = REQUEST_TIMEOUT_S
        self.api_token = os.getenv("SATNOGS_API_TOKEN", "").strip()
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        """
        Build request headers, adding authorization when a token is 
        present.
        """
        headers: dict[str, str] = {}
        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"
        return headers

    def _get_with_retry(self, 
                        url: str, 
                        params: dict[str, Any] | None, 
                        page_num: int) -> requests.Response:
        """
        Execute one GET request with retry/backoff on HTTP 429.

        SatNOGS can rate-limit large historical downloads. This helper 
        retries using either the server-provided 'Retry-After' header or 
        a simple exponential backoff.
        """
        attempt = 0
        while True:
            response = self.session.get(url, params=params, 
                                        headers=self._headers(), 
                                        timeout=self.timeout_s)
            if response.status_code != 429:
                response.raise_for_status()
                return response

            attempt += 1
            if attempt > MAX_RETRIES:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            try:
                sleep_s = float(retry_after) if retry_after is not None else min(2 ** attempt, 60)
            except ValueError:
                sleep_s = min(2 ** attempt, 60)

            print(f"Rate limited on page {page_num}, "
                  f"retrying in {sleep_s:.1f}s...", flush=True)
            time.sleep(sleep_s)

    def fetch_telemetry(self, 
                        norad_cat_id: int, 
                        start_utc: str | None = None, 
                        end_utc: str | None = None) -> list[dict[str, Any]]:
        """
        Fetch SatNOGS telemetry packets for one NORAD ID and optional 
        time range.

        The method follows SatNOGS pagination until all pages are 
        collected. Progress is printed page-by-page so long downloads 
        are visible to the user.
        """
        params: dict[str, Any] = {"satellite": norad_cat_id, 
                                  "format": "json"}
        if start_utc:
            params["start"] = start_utc
        if end_utc:
            params["end"] = end_utc

        if start_utc and end_utc:
            print(f"Starting SatNOGS download for NORAD "
                  f"{norad_cat_id} from {start_utc} to {end_utc}", 
                  flush=True)
        elif start_utc:
            print(f"Starting SatNOGS download for NORAD "
                  f"{norad_cat_id} from {start_utc}", flush=True)
        elif end_utc:
            print(f"Starting SatNOGS download for NORAD "
                  f"{norad_cat_id} up to {end_utc}", flush=True)
        else:
            print(f"Starting SatNOGS download for NORAD "
                  f"{norad_cat_id}", flush=True)

        url: str | None = self.base_url
        results: list[dict[str, Any]] = []
        is_first_request = True
        page_num = 1

        while url:
            # Only the first request carries explicit query parameters.
            # Later pages use the 'next' URL returned by the API.
            response = self._get_with_retry(url=url, 
                                            params=params if is_first_request else None, 
                                            page_num=page_num)
            payload = response.json()

            if isinstance(payload, list):
                page_results = payload
                results.extend(page_results)
                print(
                    f"Page {page_num}: received {len(page_results)} "
                    f"frames (total so far: {len(results)})",
                    flush=True,
                )
                break

            page_results = payload.get("results", [])
            results.extend(page_results)
            print(
                f"Page {page_num}: received {len(page_results)} "
                f"frames (total so far: {len(results)})",
                flush=True,
            )

            url = payload.get("next")
            is_first_request = False
            if url:
                print(f"Waiting {PAGE_DELAY_S:.2f}s before next request...", 
                      flush=True)
                time.sleep(PAGE_DELAY_S)
            page_num += 1

        print(f"Finished download. Total frames fetched: {len(results)}", 
              flush=True)
        
        return results

# -------------------------- Download Service --------------------------

class DownloadService:
    """
    Service object that syncs SatNOGS API packets into the raw database
    table.
    """

    def __init__(self, db: TelemetryDB) -> None:
        self.db = db
        self.client = SatNOGSClient()

    def sync_raw_latest(self, 
                        norad_cat_id: int, 
                        log: LogFunc | None = None) -> SyncResult:
        """
        Incrementally sync packets newer than the latest stored raw 
        timestamp.
        """
        start_utc = None
        last_ts = self.db.get_last_raw_timestamp()
        if last_ts:
            # Add one second so the previously stored packet is not
            # requested again unnecessarily.
            last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            start_utc = (last_dt + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
            if log:
                log(f"Resuming raw download after latest stored "
                    f"packet: {start_utc}")
                
        result = self.sync_raw_range(norad_cat_id=norad_cat_id, 
                                     start_utc=start_utc, 
                                     end_utc=None, 
                                     log=log)
        return result

    def sync_raw_range(self, 
                       norad_cat_id: int, 
                       start_utc: str | None, 
                       end_utc: str | None, 
                       log: LogFunc | None = None) -> SyncResult:
        """
        Download packets in the requested time range and store them as 
        raw rows.
        """
        result = SyncResult()
        if log:
            log(f"Fetching raw SatNOGS telemetry for NORAD {norad_cat_id}...")

        packets = self.client.fetch_telemetry(norad_cat_id=norad_cat_id, 
                                              start_utc=start_utc, 
                                              end_utc=end_utc)
        result.total_seen = len(packets)

        if log:
            log(f"Fetched {len(packets)} raw packets")

        for idx, packet in enumerate(packets, start=1):
            try:
                timestamp_utc, observer = extract_raw_fields_for_indexing(packet)
                raw = RawPacket(
                    timestamp_utc=timestamp_utc,
                    observer=observer,
                    raw_json=packet,
                )
                _, inserted = self.db.insert_raw_packet(raw=raw)
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

# ----------------------------------------------------------------------