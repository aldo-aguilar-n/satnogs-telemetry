"""
Title: database.py
Authors: Aldo Aguilar
Date: 2026-05-03
Description: SQLite database layer for SatNOGS telemetry.

This module owns all direct interaction with SQLite. The rest of the 
project treats this class as the single place where database schema and 
queries live.

Design notes
------------
- One database file is created per NORAD ID.
- Raw SatNOGS packets are stored unchanged in 'raw_frames'.
- Parsed/decoded rows are stored separately in 'parsed_frames'.
- The parsed table points back to the raw table through 'raw_frame_id'
  so reparsing can be done later without redownloading packets.
"""

# System imports
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any

# All per-satellite SQLite files are stored under this folder.
DATA_DIR = Path("data")

# -----------------------__--- Data Classes ------__--------------------

@dataclass(slots=True)
class RawPacket:
    """
    In-memory representation of one raw SatNOGS packet before insertion.

    Parameters
    ----------
    timestamp_utc
        Metadata timestamp reported by SatNOGS.
    observer
        SatNOGS observer / station name.
    raw_json
        Full raw SatNOGS JSON packet. This is stored as-is in the 
        database.
    """
    timestamp_utc: str
    observer: str
    raw_json: dict[str, Any]

@dataclass(slots=True)
class ParsedPacket:
    """
    In-memory representation of one parsed packet row.

    This structure holds both transport/header metadata and the optional
    decoded payload. The payload may be 'None' when header extraction
    succeeded but mission-specific decoding failed.
    """
    raw_frame_id: int
    timestamp_utc: str
    observer: str
    dest_callsign: str
    src_callsign: str
    raw_ax25_frame_hex: str
    ccsds_apid: int | None
    ccsds_sequence_count: int | None
    raw_ccsds_packet_hex: str
    parsed_json: dict[str, Any] | None
    parsed_json_eng: dict[str, Any] | None = None

@dataclass(slots=True)
class SyncResult:
    """
    Small status object used by download/parse commands.

    The CLI serializes this object to JSON for human-readable progress
    reports.
    """
    total_seen: int = 0
    raw_inserted: int = 0
    raw_existing: int = 0
    parsed_inserted: int = 0
    parsed_skipped_existing: int = 0
    parse_errors: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        """
        Ensure 'errors' is always a mutable list.
        """
        if self.errors is None:
            self.errors = []

# ------------------------- Telemetry Database -------------------------

class TelemetryDB:
    """
    Thin wrapper around the per-satellite SQLite database.

    Each instance points to exactly one NORAD-specific database file
    such as 'data/98386.sqlite3'.
    """

    def __init__(self, norad_cat_id: int) -> None:
        """
        Open or create the database for one satellite.

        The parent 'data/' directory is created automatically when 
        needed.
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.path = DATA_DIR / f"{norad_cat_id}.sqlite3"
        self.conn = sqlite3.connect(self.path)
        # Returning rows as mapping-like objects makes the rest of the 
        # code easier to read than tuple indexing.
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """
        Close the SQLite connection.
        """
        self.conn.close()

    def init_schema(self) -> None:
        """
        Create database tables and indexes if they do not already exist.

        'raw_frames' stores the raw SatNOGS packet JSON exactly as 
        received.
        'parsed_frames' stores extracted AX.25/CCSDS metadata plus
        decoded payload information.
        """
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                observer TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                UNIQUE(timestamp_utc, observer, raw_json)
            );

            CREATE TABLE IF NOT EXISTS parsed_frames (
                raw_frame_id INTEGER PRIMARY KEY,
                timestamp_utc TEXT NOT NULL,
                observer TEXT NOT NULL,
                dest_callsign TEXT NOT NULL,
                src_callsign TEXT NOT NULL,
                raw_ax25_frame_hex TEXT NOT NULL,
                ccsds_apid INTEGER,
                ccsds_sequence_count INTEGER,
                raw_ccsds_packet_hex TEXT NOT NULL,
                parsed_json TEXT,
                parsed_json_eng TEXT,
                FOREIGN KEY(raw_frame_id) REFERENCES raw_frames(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_raw_timestamp ON raw_frames(timestamp_utc);
            CREATE INDEX IF NOT EXISTS idx_parsed_timestamp ON parsed_frames(timestamp_utc);
            CREATE INDEX IF NOT EXISTS idx_parsed_apid ON parsed_frames(ccsds_apid);
            """
        )
        # Migration for existing databases created before parsed_json_eng.
        cols = self.conn.execute("PRAGMA table_info(parsed_frames)").fetchall()
        col_names = {str(col["name"]) for col in cols}
        if "parsed_json_eng" not in col_names:
            self.conn.execute(
                "ALTER TABLE parsed_frames ADD COLUMN parsed_json_eng TEXT"
            )

        self.conn.commit()

    def insert_raw_packet(self, raw: RawPacket) -> tuple[int | None, bool]:
        """
        Insert one raw packet if it is not already present.

        Returns
        -------
        tuple[int | None, bool]
            '(row_id, inserted)' where 'inserted' is 'True' only when a
            new row was created.
        """
        payload = json.dumps(raw.raw_json, ensure_ascii=False, separators=(",", ":"))

        existing = self.conn.execute(
            """
            SELECT id FROM raw_frames
            WHERE timestamp_utc = ? AND observer = ? AND raw_json = ?
            """,
            (raw.timestamp_utc, raw.observer, payload),
        ).fetchone()
        if existing:
            return int(existing[0]), False

        # If the row does not already exist, insert it and return the
        # new ID.
        cur = self.conn.execute(
            """
            INSERT INTO raw_frames (
                timestamp_utc, observer, raw_json
            ) VALUES (?, ?, ?)
            """,
            (raw.timestamp_utc, raw.observer, payload),
        )
        self.conn.commit()
        return int(cur.lastrowid), True

    def insert_parsed_packet(self, parsed: ParsedPacket) -> bool:
        """
        Insert one parsed packet row if it does not already exist.

        Parsed rows are uniquely keyed by 'raw_frame_id' because each 
        raw row should produce at most one parsed row at a time.
        """
        existing = self.conn.execute(
            "SELECT raw_frame_id FROM parsed_frames WHERE raw_frame_id = ?",
            (parsed.raw_frame_id,),
        ).fetchone()
        if existing:
            return False

        # Store the parsed JSON as text. This is optional and may be
        # 'None' when parsing succeeded but mission-specific decoding 
        # failed.
        parsed_json = json.dumps(parsed.parsed_json, ensure_ascii=False) if parsed.parsed_json is not None else None
        parsed_json_eng = json.dumps(parsed.parsed_json_eng, ensure_ascii=False) if parsed.parsed_json_eng is not None else None
        self.conn.execute(
            """
            INSERT INTO parsed_frames (
                raw_frame_id, timestamp_utc, observer,
                dest_callsign, src_callsign, raw_ax25_frame_hex,
                ccsds_apid, ccsds_sequence_count, raw_ccsds_packet_hex,
                parsed_json, parsed_json_eng
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parsed.raw_frame_id,
                parsed.timestamp_utc,
                parsed.observer,
                parsed.dest_callsign,
                parsed.src_callsign,
                parsed.raw_ax25_frame_hex,
                parsed.ccsds_apid,
                parsed.ccsds_sequence_count,
                parsed.raw_ccsds_packet_hex,
                parsed_json,
                parsed_json_eng,
            ),
        )
        self.conn.commit()
        return True

    def get_last_raw_timestamp(self) -> str | None:
        """
        Return the newest raw metadata timestamp currently stored.
        """
        row = self.conn.execute(
            "SELECT timestamp_utc FROM raw_frames ORDER BY timestamp_utc DESC LIMIT 1"
        ).fetchone()
        return str(row[0]) if row else None

    def iter_unparsed_raw_rows(
        self,
        start_utc: str | None = None,
        end_utc: str | None = None,
    ) -> list[sqlite3.Row]:
        """
        Return raw rows that do not yet have a matching parsed row.

        Optional start/end timestamps limit the raw rows that are parsed.
        Rows are ordered oldest-to-newest so parsing proceeds 
        chronologically.
        """
        where = ["p.raw_frame_id IS NULL"]
        params: list[Any] = []

        if start_utc:
            where.append("r.timestamp_utc >= ?")
            params.append(start_utc)

        if end_utc:
            where.append("r.timestamp_utc <= ?")
            params.append(end_utc)

        sql = f"""
            SELECT r.*
            FROM raw_frames r
            LEFT JOIN parsed_frames p ON p.raw_frame_id = r.id
            WHERE {" AND ".join(where)}
            ORDER BY r.timestamp_utc ASC, r.id ASC
        """
        cur = self.conn.execute(sql, params)
        return list(cur.fetchall())

    def iter_parsed_rows(
        self,
        start_utc: str | None = None,
        end_utc: str | None = None,
    ) -> list[sqlite3.Row]:
        """
        Return parsed rows, optionally limited to a timestamp range.
        """
        where: list[str] = []
        params: list[Any] = []

        if start_utc:
            where.append("timestamp_utc >= ?")
            params.append(start_utc)

        if end_utc:
            where.append("timestamp_utc <= ?")
            params.append(end_utc)

        sql = "SELECT * FROM parsed_frames"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY timestamp_utc ASC, raw_frame_id ASC"

        return list(self.conn.execute(sql, params).fetchall())

    def get_recent_raw_rows(self, limit: int = 20) -> list[sqlite3.Row]:
        """
        Return the most recent raw rows for inspection/debugging.
        """
        return list(
            self.conn.execute(
                "SELECT * FROM raw_frames ORDER BY timestamp_utc DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        )

    def get_recent_parsed_rows(self, limit: int = 20) -> list[sqlite3.Row]:
        """
        Return the most recent parsed rows for inspection/debugging.
        """
        return list(
            self.conn.execute(
                "SELECT * FROM parsed_frames ORDER BY timestamp_utc DESC, raw_frame_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        )

    def delete_raw_packet_by_id(self, raw_frame_id: int) -> None:
        """
        Delete one raw row by ID.

        This is used for rows proven to be permanently malformed so the
        parser does not retry them forever.
        """
        self.conn.execute("DELETE FROM raw_frames WHERE id = ?", (raw_frame_id,))
        self.conn.commit()

    def delete_parsed_rows(self,
                                     start_utc: str | None = None,
                                     end_utc: str | None = None) -> int:
        """
        Delete parsed rows in this per-NORAD database.

        Optional start/end timestamps support reparsing only a subset of
        stored raw frames after decoder logic changes.

        Returns
        -------
        int
            Number of parsed rows deleted.
        """
        where: list[str] = []
        params: list[Any] = []

        if start_utc:
            where.append("timestamp_utc >= ?")
            params.append(start_utc)

        if end_utc:
            where.append("timestamp_utc <= ?")
            params.append(end_utc)

        count_sql = "SELECT COUNT(*) FROM parsed_frames"
        delete_sql = "DELETE FROM parsed_frames"

        if where:
            clause = " WHERE " + " AND ".join(where)
            count_sql += clause
            delete_sql += clause

        row = self.conn.execute(count_sql, params).fetchone()
        count = int(row[0]) if row else 0

        self.conn.execute(delete_sql, params)
        self.conn.commit()
        return count

    def dump_parsed_archive_json(self,
                                 output_path: str | Path,
                                 start_utc: str | None = None,
                                 end_utc: str | None = None) -> Path:
        """
        Dump a compact parsed-frame archive JSON file.

        Each record contains only timestamp_utc, observer, and
        raw_ccsds_packet_hex to keep archival files small.
        """
        outpath = Path(output_path)
        outpath.parent.mkdir(parents=True, exist_ok=True)

        rows = self.iter_parsed_rows(start_utc=start_utc, end_utc=end_utc)
        records = [
            {
                "timestamp_utc": row["timestamp_utc"],
                "observer": row["observer"],
                "raw_ccsds_packet_hex": row["raw_ccsds_packet_hex"],
            }
            for row in rows
        ]

        outpath.write_text(
            json.dumps(records, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        return outpath

    def get_available_numeric_fields(self, apid: int | None = None) -> list[str]:
        """
        Inspect stored 'parsed_json' payloads and list numeric leaf 
        fields.

        Parameters
        ----------
        apid
            Optional APID filter.
        """
        cur = self.conn.execute(
            "SELECT parsed_json FROM parsed_frames WHERE parsed_json IS NOT NULL"
            + (" AND ccsds_apid = ?" if apid is not None else ""),
            ((apid,) if apid is not None else ()),
        )
        fields: set[str] = set()
        for row in cur.fetchall():
            try:
                payload = json.loads(row[0])
            except Exception:
                continue
            if not isinstance(payload, dict) or payload.get("_decode_error") is True:
                continue
            self._collect_numeric_fields(payload, prefix="", out=fields)
        return sorted(fields)

    def _collect_numeric_fields(self, obj: Any, prefix: str, out: set[str]) -> None:
        """
        Recursively collect dotted field paths for numeric leaf values.

        The implementation intentionally ignores booleans because 'bool' 
        is a subclass of 'int' in Python and would otherwise pollute the 
        list.
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{prefix}.{key}" if prefix else str(key)
                self._collect_numeric_fields(value, new_prefix, out)
            return

        if isinstance(obj, list):
            for i, value in enumerate(obj):
                new_prefix = f"{prefix}.{i}" if prefix else str(i)
                self._collect_numeric_fields(value, new_prefix, out)
            return

        if isinstance(obj, (int, float)) and not isinstance(obj, bool):
            out.add(prefix)

# ----------------------------------------------------------------------