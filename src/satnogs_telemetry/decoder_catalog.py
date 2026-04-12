"""
Decoder catalog utilities.

This module scans the satnogs-decoders submodule for available .ksy files
and provides simple metadata for interactive selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DecoderCandidate:
    """
    Represents one .ksy decoder candidate discovered in the submodule.
    """

    relative_ksy_path: str
    absolute_ksy_path: Path
    guessed_root_class: str


def guess_root_class_from_ksy_filename(ksy_path: Path) -> str:
    """
    Guess the Kaitai-generated Python root class name from a .ksy filename.

    This is a best-effort guess based on the filename.
    Example:
        my_decoder.ksy -> MyDecoder
    """
    stem = ksy_path.stem
    parts = stem.replace("-", "_").split("_")
    return "".join(part.capitalize() for part in parts if part)


def scan_ksy_files(satnogs_decoders_dir: Path) -> list[DecoderCandidate]:
    """
    Recursively scan the satnogs-decoders directory for .ksy files.

    Parameters
    ----------
    satnogs_decoders_dir
        Root path of the satnogs-decoders submodule.

    Returns
    -------
    list[DecoderCandidate]
        Sorted list of discovered decoders.
    """
    if not satnogs_decoders_dir.exists():
        raise FileNotFoundError(
            f"satnogs-decoders directory not found: {satnogs_decoders_dir}"
        )

    candidates: list[DecoderCandidate] = []

    for path in sorted(satnogs_decoders_dir.rglob("*.ksy")):
        rel = path.relative_to(satnogs_decoders_dir).as_posix()
        candidates.append(
            DecoderCandidate(
                relative_ksy_path=rel,
                absolute_ksy_path=path.resolve(),
                guessed_root_class=guess_root_class_from_ksy_filename(path),
            )
        )

    return candidates