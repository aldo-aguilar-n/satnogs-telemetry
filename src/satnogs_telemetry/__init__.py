"""
satnogs_telemetry package.

Backend-first toolkit for:
- downloading SatNOGS telemetry
- storing full raw SatNOGS packets as-is
- extracting AX.25 and CCSDS metadata during parsing
- optionally decoding CCSDS payloads by APID
- storing one SQLite database per satellite
- exporting simple headless plots
"""

from .config import AppConfig
from .db import TelemetryDB
from .ingest import IngestService

__all__ = ["AppConfig", "TelemetryDB", "IngestService"]

__version__ = "0.1.0"
