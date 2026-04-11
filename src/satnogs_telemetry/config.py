"""
Application configuration and decoder registry loading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib

from .models import DecoderSpec, SatelliteConfig


@dataclass(slots=True)
class AppConfig:
    """
    Configuration for the SatNOGS telemetry backend.
    """

    db_dir: Path = Path("data")
    satnogs_base_url: str = "https://db.satnogs.org/api/telemetry/"
    request_timeout_s: int = 60
    source_name: str = "satnogs_db"
    satellites: list[SatelliteConfig] = field(default_factory=list)

    def db_path_for_norad(self, norad_cat_id: int) -> Path:
        """Return the SQLite DB path for a NORAD ID."""
        return self.db_dir / f"{norad_cat_id}.sqlite3"

    def resolve_satellite_config(self, raw_json: dict, norad_cat_id: int) -> SatelliteConfig | None:
        """
        Resolve the best matching satellite configuration.

        Matching priority:
        1. NORAD ID must match
        2. transmitter, if configured, must also match
        3. sat_id, if configured, must also match

        The most specific candidate wins.
        """
        candidates = [cfg for cfg in self.satellites if cfg.norad_cat_id == norad_cat_id]
        if not candidates:
            return None

        raw_transmitter = str(raw_json.get("transmitter") or "")
        raw_sat_id = str(raw_json.get("sat_id") or "")

        best: SatelliteConfig | None = None
        best_score = -1

        for cfg in candidates:
            if cfg.transmitter and cfg.transmitter != raw_transmitter:
                continue
            if cfg.sat_id and cfg.sat_id != raw_sat_id:
                continue

            # More specific matches score higher.
            score = 0
            if cfg.transmitter:
                score += 2
            if cfg.sat_id:
                score += 1

            if score > best_score:
                best = cfg
                best_score = score

        return best


def load_config(path: str | Path | None) -> AppConfig:
    """
    Load application config from TOML.

    If `path` is None, a default config object is returned.
    """
    if path is None:
        return AppConfig()

    config_path = Path(path)
    with config_path.open("rb") as f:
        data = tomllib.load(f)

    satellites: list[SatelliteConfig] = []

    for entry in data.get("satellites", []):
        apid_decoders: dict[int, DecoderSpec] = {}
        for dec in entry.get("apid_decoders", []):
            spec = DecoderSpec(
                apid=int(dec["apid"]),
                decoder_type=str(dec["type"]),
                parser_path=str(dec.get("parser_path") or ""),
                ksy_path=str(dec.get("ksy_path") or ""),
                root_class=str(dec.get("root_class") or ""),
                strip_ccsds_primary_header=bool(dec.get("strip_ccsds_primary_header", False)),
            )
            apid_decoders[spec.apid] = spec

        satellites.append(
            SatelliteConfig(
                norad_cat_id=int(entry["norad_cat_id"]),
                frame_protocol=str(entry.get("frame_protocol") or "ax25_ccsds"),
                transmitter=str(entry.get("transmitter") or ""),
                sat_id=str(entry.get("sat_id") or ""),
                apid_decoders=apid_decoders,
            )
        )

    return AppConfig(
        db_dir=Path(data.get("db_dir", "data")),
        satnogs_base_url=str(data.get("satnogs_base_url", "https://db.satnogs.org/api/telemetry/")),
        request_timeout_s=int(data.get("request_timeout_s", 60)),
        source_name=str(data.get("source_name", "satnogs_db")),
        satellites=satellites,
    )
