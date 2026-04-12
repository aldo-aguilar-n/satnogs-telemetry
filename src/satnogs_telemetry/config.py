"""
Application configuration objects and TOML loading helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass(slots=True)
class AppConfig:
    """
    Configuration for the SatNOGS telemetry backend.
    """

    db_dir: Path = Path("data")
    satnogs_base_url: str = "https://db.satnogs.org/api/telemetry/"
    request_timeout_s: int = 60
    source_name: str = "satnogs_db"

    satnogs_decoders_dir: Path = Path("tools/satnogs-decoders")
    generated_decoders_dir: Path = Path("decoders")
    ksc_bin: str = "kaitai-struct-compiler"
    config_path: Path = Path("config.toml")

    # Loaded from .env by cli.py, with config.toml fallback
    satnogs_api_token: str = ""

    # One decoder mapping per satellite NORAD ID
    satellite_decoders: dict[int, dict[str, str]] = field(default_factory=dict)

    def db_path_for_norad(self, norad_cat_id: int) -> Path:
        """
        Return the SQLite database path for a specific satellite.
        """
        return self.db_dir / f"{norad_cat_id}.sqlite3"


def load_app_config(config_path: str | Path) -> AppConfig:
    """
    Load AppConfig from TOML.
    """
    path = Path(config_path)
    if not path.exists():
        return AppConfig(config_path=path)

    with path.open("rb") as f:
        data = tomllib.load(f)

    app = data.get("app", {})
    satellites = data.get("satellites", {})

    satellite_decoders: dict[int, dict[str, str]] = {}
    for norad_str, sat_entry in satellites.items():
        try:
            norad = int(norad_str)
        except ValueError:
            continue

        decoder = sat_entry.get("decoder")
        if isinstance(decoder, dict):
            ksy_path = str(decoder.get("ksy_path", "")).strip()
            root_class = str(decoder.get("root_class", "")).strip()
            if ksy_path and root_class:
                satellite_decoders[norad] = {
                    "ksy_path": ksy_path,
                    "root_class": root_class,
                }

    return AppConfig(
        db_dir=Path(app.get("db_dir", "data")),
        satnogs_base_url=str(app.get("satnogs_base_url", "https://db.satnogs.org/api/telemetry/")),
        request_timeout_s=int(app.get("request_timeout_s", 60)),
        source_name=str(app.get("source_name", "satnogs_db")),
        satnogs_decoders_dir=Path(app.get("satnogs_decoders_dir", "tools/satnogs-decoders")),
        generated_decoders_dir=Path(app.get("generated_decoders_dir", "decoders")),
        ksc_bin=str(app.get("ksc_bin", "kaitai-struct-compiler")),
        config_path=path,
        satnogs_api_token=str(app.get("satnogs_api_token", "")).strip(),
        satellite_decoders=satellite_decoders,
    )