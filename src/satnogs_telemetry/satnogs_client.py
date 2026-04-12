"""
HTTP client for the SatNOGS telemetry API.
"""

from __future__ import annotations

import time
from typing import Any

import requests


class SatNOGSClient:
    """
    Minimal HTTP client for SatNOGS telemetry.
    """

    def __init__(
        self,
        base_url: str,
        timeout_s: int = 60,
        api_token: str = "",
        page_delay_s: float = 0.75,
        max_retries: int = 5,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout_s = timeout_s
        self.api_token = api_token.strip()
        self.page_delay_s = page_delay_s
        self.max_retries = max_retries
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"
        return headers

    def _get_with_retry(
        self,
        url: str,
        params: dict[str, Any] | None,
        page_num: int,
    ) -> requests.Response:
        attempt = 0

        while True:
            response = self.session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self.timeout_s,
            )

            if response.status_code != 429:
                response.raise_for_status()
                return response

            attempt += 1
            if attempt > self.max_retries:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    sleep_s = float(retry_after)
                except ValueError:
                    sleep_s = min(2 ** attempt, 60)
            else:
                sleep_s = min(2 ** attempt, 60)

            print(f"Rate limited on page {page_num}, retrying in {sleep_s:.1f}s...", flush=True)
            time.sleep(sleep_s)

    def fetch_telemetry(
        self,
        norad_cat_id: int,
        start_utc: str | None = None,
        end_utc: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch telemetry packets for a NORAD ID and optional time range.
        """
        params: dict[str, Any] = {
            "satellite": norad_cat_id,
            "format": "json",
        }

        if start_utc:
            params["start"] = start_utc
        if end_utc:
            params["end"] = end_utc

        if start_utc and end_utc:
            print(f"Starting SatNOGS download for NORAD {norad_cat_id} from {start_utc} to {end_utc}", flush=True)
        elif start_utc:
            print(f"Starting SatNOGS download for NORAD {norad_cat_id} from {start_utc}", flush=True)
        elif end_utc:
            print(f"Starting SatNOGS download for NORAD {norad_cat_id} up to {end_utc}", flush=True)
        else:
            print(f"Starting SatNOGS download for NORAD {norad_cat_id}", flush=True)

        url: str | None = self.base_url
        results: list[dict[str, Any]] = []
        is_first_request = True
        page_num = 1

        while url:
            response = self._get_with_retry(
                url=url,
                params=params if is_first_request else None,
                page_num=page_num,
            )
            payload = response.json()

            if isinstance(payload, list):
                page_results = payload
                results.extend(page_results)
                print(
                    f"Page {page_num}: received {len(page_results)} frames "
                    f"(total so far: {len(results)})",
                    flush=True,
                )
                break

            page_results = payload.get("results", [])
            results.extend(page_results)

            print(
                f"Page {page_num}: received {len(page_results)} frames "
                f"(total so far: {len(results)})",
                flush=True,
            )

            url = payload.get("next")
            is_first_request = False

            if url:
                print(f"Waiting {self.page_delay_s:.2f}s before next request...", flush=True)
                time.sleep(self.page_delay_s)

            page_num += 1

        print(f"Finished download. Total frames fetched: {len(results)}", flush=True)
        return results