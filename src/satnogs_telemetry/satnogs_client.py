"""
HTTP client for the SatNOGS telemetry API.
"""

from __future__ import annotations

from typing import Any

import requests


class SatNOGSClient:
    """Minimal HTTP client for SatNOGS telemetry."""

    def __init__(self, base_url: str, timeout_s: int = 60) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout_s = timeout_s
        self.session = requests.Session()

    def fetch_telemetry(
        self,
        norad_cat_id: int,
        start_utc: str | None = None,
        end_utc: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch telemetry packets for a NORAD ID and optional time range."""
        params: dict[str, Any] = {
            "satellite__norad_cat_id": norad_cat_id,
            "format": "json",
        }

        if start_utc:
            params["timestamp__gte"] = start_utc
        if end_utc:
            params["timestamp__lte"] = end_utc

        url: str | None = self.base_url
        results: list[dict[str, Any]] = []

        while url:
            response = self.session.get(
                url,
                params=params if url == self.base_url else None,
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            payload = response.json()

            if isinstance(payload, list):
                results.extend(payload)
                break

            results.extend(payload.get("results", []))
            url = payload.get("next")
            params = None

        return results
