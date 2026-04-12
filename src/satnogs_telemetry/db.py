"""
SQLite storage layer for one satellite database.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import ParsedPacket, RawPacket
from .utils import flatten_dict, json_dumps


class TelemetryDB:
    """
    SQLite-backed telemetry database for a single satellite.
    """

    def __init__(self, db_path: str | Path) -> None:
        """Open the database connection."""
        self.path = str(db_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def init_schema(self) -> None:
        """
        Create the required tables and indexes.

        This schema is intended for one satellite per database file.
        """
        cur = self.conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                norad_cat_id INTEGER NOT NULL,
                timestamp_utc TEXT NOT NULL,
                observer TEXT,
                raw_json TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'satnogs_db',
                inserted_utc TEXT NOT NULL,
                UNIQUE(raw_json)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS parsed_frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_frame_id INTEGER NOT NULL UNIQUE,
                norad_cat_id INTEGER NOT NULL,
                timestamp_utc TEXT NOT NULL,
                observer TEXT,
                dest_callsign TEXT NOT NULL,
                src_callsign TEXT NOT NULL,
                raw_ax25_frame_hex TEXT NOT NULL,
                ccsds_apid INTEGER NOT NULL,
                ccsds_sequence_count INTEGER NOT NULL,
                raw_ccsds_packet_hex TEXT NOT NULL,
                parsed_json TEXT,
                flatten_json TEXT,
                parser_path TEXT,
                parser_root_class TEXT,
                inserted_utc TEXT NOT NULL,
                FOREIGN KEY(raw_frame_id) REFERENCES raw_frames(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_time
            ON raw_frames(timestamp_utc)
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_parsed_apid_time
            ON parsed_frames(ccsds_apid, timestamp_utc)
            """
        )

        self.conn.commit()

    def get_last_raw_timestamp(self) -> str | None:
        """Return the latest stored raw timestamp in this satellite DB."""
        row = self.conn.execute(
            """
            SELECT MAX(timestamp_utc) AS ts
            FROM raw_frames
            """
        ).fetchone()

        return row["ts"] if row and row["ts"] else None

    def insert_raw_packet(
        self,
        raw: RawPacket,
        inserted_utc: str,
        source: str,
    ) -> tuple[int, bool]:
        """
        Insert a full raw SatNOGS packet.

        Returns
        -------
        tuple[int, bool]
            (row_id, inserted_new)
        """
        raw_json_text = json_dumps(raw.raw_json)

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO raw_frames (
                norad_cat_id, timestamp_utc, observer, raw_json, source, inserted_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                raw.norad_cat_id,
                raw.timestamp_utc,
                raw.observer,
                raw_json_text,
                source,
                inserted_utc,
            ),
        )
        self.conn.commit()

        if cur.lastrowid:
            return int(cur.lastrowid), True

        row = self.conn.execute(
            """
            SELECT id
            FROM raw_frames
            WHERE raw_json = ?
            """,
            (raw_json_text,),
        ).fetchone()

        if row is None:
            raise RuntimeError("Failed to locate existing raw packet after INSERT OR IGNORE")

        return int(row["id"]), False

    def insert_parsed_packet(self, parsed: ParsedPacket, inserted_utc: str) -> bool:
        """Insert or replace one parsed packet row."""
        flatten_json = flatten_dict(parsed.parsed_json) if parsed.parsed_json else None

        self.conn.execute(
            """
            INSERT OR REPLACE INTO parsed_frames (
                raw_frame_id, norad_cat_id, timestamp_utc, observer,
                dest_callsign, src_callsign, raw_ax25_frame_hex,
                ccsds_apid, ccsds_sequence_count, raw_ccsds_packet_hex,
                parsed_json, flatten_json, parser_path, parser_root_class,
                inserted_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parsed.raw_frame_id,
                parsed.norad_cat_id,
                parsed.timestamp_utc,
                parsed.observer,
                parsed.dest_callsign,
                parsed.src_callsign,
                parsed.raw_ax25_frame_hex,
                parsed.ccsds_apid,
                parsed.ccsds_sequence_count,
                parsed.raw_ccsds_packet_hex,
                json_dumps(parsed.parsed_json) if parsed.parsed_json is not None else None,
                json_dumps(flatten_json) if flatten_json is not None else None,
                parsed.parser_path,
                parsed.parser_root_class,
                inserted_utc,
            ),
        )
        self.conn.commit()
        return True

    def iter_unparsed_raw_rows(self) -> list[sqlite3.Row]:
        """Return raw rows that do not yet have parsed entries."""
        rows = self.conn.execute(
            """
            SELECT r.*
            FROM raw_frames r
            LEFT JOIN parsed_frames p ON p.raw_frame_id = r.id
            WHERE p.raw_frame_id IS NULL
            ORDER BY r.timestamp_utc
            """
        ).fetchall()

        return list(rows)

    def get_recent_raw_rows(self, limit: int = 20) -> list[sqlite3.Row]:
        """Return recent raw rows from this satellite DB."""
        rows = self.conn.execute(
            """
            SELECT id, norad_cat_id, timestamp_utc, observer, raw_json
            FROM raw_frames
            ORDER BY timestamp_utc DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return list(rows)

    def get_recent_parsed_rows(self, limit: int = 20) -> list[sqlite3.Row]:
        """Return recent parsed rows from this satellite DB."""
        rows = self.conn.execute(
            """
            SELECT *
            FROM parsed_frames
            ORDER BY timestamp_utc DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return list(rows)

    def get_available_numeric_fields(self, apid: int | None = None) -> list[str]:
        """Return numeric flattened fields available from parsed_json rows."""
        if apid is None:
            rows = self.conn.execute(
                """
                SELECT flatten_json
                FROM parsed_frames
                WHERE flatten_json IS NOT NULL
                ORDER BY timestamp_utc
                """
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT flatten_json
                FROM parsed_frames
                WHERE ccsds_apid = ?
                  AND flatten_json IS NOT NULL
                ORDER BY timestamp_utc
                """,
                (apid,),
            ).fetchall()

        keys: set[str] = set()
        for row in rows:
            flattened = json.loads(row["flatten_json"])
            for key, value in flattened.items():
                if isinstance(value, (int, float)) and key:
                    keys.add(key)

        return sorted(keys)

    def get_series_points(
        self,
        field_name: str,
        apid: int | None = None,
    ) -> tuple[list[str], list[float]]:
        """Return a time series for one flattened numeric field."""
        if apid is None:
            rows = self.conn.execute(
                """
                SELECT timestamp_utc, flatten_json
                FROM parsed_frames
                WHERE flatten_json IS NOT NULL
                ORDER BY timestamp_utc
                """
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT timestamp_utc, flatten_json
                FROM parsed_frames
                WHERE ccsds_apid = ?
                  AND flatten_json IS NOT NULL
                ORDER BY timestamp_utc
                """,
                (apid,),
            ).fetchall()

        xs: list[str] = []
        ys: list[float] = []

        for row in rows:
            flattened = json.loads(row["flatten_json"])
            value = flattened.get(field_name)
            if isinstance(value, (int, float)):
                xs.append(str(row["timestamp_utc"]))
                ys.append(float(value))

        return xs, ys
    
    def delete_raw_packet_by_id(self, raw_frame_id: int) -> None:
        """
        Delete one raw packet row by ID.
        """
        self.conn.execute(
            "DELETE FROM raw_frames WHERE id = ?",
            (raw_frame_id,),
        )
        self.conn.commit()

    def delete_raw_packets_by_ids(self, raw_frame_ids: list[int]) -> int:
        """
        Delete multiple raw packet rows by ID.

        Returns
        -------
        int
            Number of rows requested for deletion.
        """
        if not raw_frame_ids:
            return 0

        self.conn.executemany(
            "DELETE FROM raw_frames WHERE id = ?",
            [(rid,) for rid in raw_frame_ids],
        )
        self.conn.commit()
        return len(raw_frame_ids)
    
    def get_parsed_table_name(self) -> str:
        """
        Return the parsed table name used by this database schema.
        """
        candidates = ("parsed_packets", "parsed_frames")

        for name in candidates:
            row = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
                (name,),
            ).fetchone()
            if row is not None:
                return name

        raise RuntimeError(
            "Could not find parsed table. Expected one of: parsed_packets, parsed_frames"
        )

    def delete_parsed_rows_for_norad(self, norad_cat_id: int) -> int:
        """
        Delete all parsed rows for one NORAD ID.

        Returns
        -------
        int
            Number of rows deleted.
        """
        table = self.get_parsed_table_name()

        row = self.conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE norad_cat_id = ?",
            (norad_cat_id,),
        ).fetchone()
        count = int(row[0]) if row else 0

        self.conn.execute(
            f"DELETE FROM {table} WHERE norad_cat_id = ?",
            (norad_cat_id,),
        )
        self.conn.commit()
        return count
