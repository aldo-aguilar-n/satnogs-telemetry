"""
Interactive decoder mapping helpers.

This module prompts the user to choose a .ksy decoder when no decoder
exists yet for a satellite, then saves that mapping to config.
"""

from __future__ import annotations

from pathlib import Path
import tomllib

try:
    import tomli_w
except ImportError as exc:
    raise ImportError("Please install tomli-w to enable config writing.") from exc

from .decoder_catalog import scan_ksy_files


def load_toml(path: Path) -> dict:
    """
    Load TOML file if it exists, otherwise return an empty dict.
    """
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def save_toml(path: Path, data: dict) -> None:
    """
    Save TOML data to disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(data, f)


def prompt_for_satellite_decoder_choice(
    satnogs_decoders_dir: Path,
    norad_cat_id: int,
) -> tuple[str, str]:
    """
    Prompt the user to choose one .ksy decoder for a satellite.

    Returns
    -------
    tuple[str, str]
        (relative_ksy_path, guessed_root_class)
    """
    candidates = scan_ksy_files(satnogs_decoders_dir)
    if not candidates:
        raise RuntimeError("No .ksy files found in satnogs-decoders submodule.")

    print()
    print(f"No decoder configured for NORAD {norad_cat_id}.")
    print("Select a .ksy decoder to use for this satellite:")
    for idx, candidate in enumerate(candidates, start=1):
        print(f"  {idx}. {candidate.relative_ksy_path}  [root class: {candidate.guessed_root_class}]")

    while True:
        raw = input("Enter selection number: ").strip()
        try:
            choice = int(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue

        if 1 <= choice <= len(candidates):
            selected = candidates[choice - 1]
            break

        print("Selection out of range.")

    # No extra prompt: just use the guessed class name.
    return selected.relative_ksy_path, selected.guessed_root_class


def save_satellite_decoder_mapping(
    config_path: Path,
    norad_cat_id: int,
    ksy_path: str,
    root_class: str,
) -> None:
    """
    Save one satellite-level decoder mapping into config TOML.
    """
    data = load_toml(config_path)

    satellites = data.setdefault("satellites", {})
    sat_key = str(norad_cat_id)
    sat_entry = satellites.setdefault(sat_key, {})
    decoder_entry = sat_entry.setdefault("decoder", {})

    decoder_entry["ksy_path"] = ksy_path
    decoder_entry["root_class"] = root_class

    save_toml(config_path, data)