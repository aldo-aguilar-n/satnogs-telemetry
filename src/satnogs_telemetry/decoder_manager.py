"""
Decoder compilation and caching manager.

This module is responsible for:
- resolving satellite-level Kaitai decoder specs from config
- compiling .ksy files into Python on first use
- caching generated Python decoders locally
- reusing cached decoders unless the .ksy source changed
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig
from .interactive_mapping import (
    prompt_for_satellite_decoder_choice,
    save_satellite_decoder_mapping,
)


@dataclass(slots=True)
class DecoderRef:
    """
    Reference to a satellite decoder definition before compilation.
    """

    ksy_path: Path
    root_class: str
    cache_key: str


@dataclass(slots=True)
class CompiledDecoder:
    """
    Reference to a compiled Python decoder.
    """

    generated_py: Path
    root_class: str
    buildinfo_path: Path


class DecoderManager:
    """
    Resolve, compile, cache, and return satellite-level Kaitai decoders.
    """

    def __init__(self, config: AppConfig) -> None:
        """
        Initialize the decoder manager.
        """
        self.config = config
        self.config.generated_decoders_dir.mkdir(parents=True, exist_ok=True)

    def resolve_decoder(self, norad_cat_id: int) -> DecoderRef | None:
        """
        Resolve the decoder definition for a given NORAD ID.

        If no decoder is configured yet, interactively prompt the user to choose
        one from the satnogs-decoders submodule, then save that mapping to config.

        Parameters
        ----------
        norad_cat_id
            NORAD catalog ID.

        Returns
        -------
        DecoderRef | None
            Decoder reference.
        """
        decoder_info = self.config.satellite_decoders.get(norad_cat_id)

        if not decoder_info:
            ksy_path, root_class = prompt_for_satellite_decoder_choice(
                satnogs_decoders_dir=self.config.satnogs_decoders_dir,
                norad_cat_id=norad_cat_id,
            )

            save_satellite_decoder_mapping(
                config_path=self.config.config_path,
                norad_cat_id=norad_cat_id,
                ksy_path=ksy_path,
                root_class=root_class,
            )

            self.config.satellite_decoders[norad_cat_id] = {
                "ksy_path": ksy_path,
                "root_class": root_class,
            }
            decoder_info = self.config.satellite_decoders[norad_cat_id]

        rel_ksy = decoder_info.get("ksy_path", "").strip()
        root_class = decoder_info.get("root_class", "").strip()

        if not rel_ksy:
            raise ValueError(f"Decoder entry for NORAD {norad_cat_id} is missing 'ksy_path'")
        if not root_class:
            raise ValueError(f"Decoder entry for NORAD {norad_cat_id} is missing 'root_class'")

        ksy_path = (self.config.satnogs_decoders_dir / rel_ksy).resolve()
        cache_key = "satellite_decoder"

        return DecoderRef(
            ksy_path=ksy_path,
            root_class=root_class,
            cache_key=cache_key,
        )

    def ensure_compiled(self, norad_cat_id: int, decoder: DecoderRef) -> CompiledDecoder:
        """
        Compile a decoder if needed, otherwise reuse the cached generated Python file.
        """
        out_dir = self.config.generated_decoders_dir / str(norad_cat_id) / decoder.cache_key
        out_dir.mkdir(parents=True, exist_ok=True)

        generated_py = out_dir / f"{decoder.ksy_path.stem}.py"
        buildinfo_path = out_dir / ".buildinfo.json"

        if self._is_cache_valid(decoder, generated_py, buildinfo_path):
            return CompiledDecoder(
                generated_py=generated_py,
                root_class=decoder.root_class,
                buildinfo_path=buildinfo_path,
            )

        self._compile_ksy(decoder.ksy_path, out_dir)
        self._write_buildinfo(decoder, generated_py, buildinfo_path)

        return CompiledDecoder(
            generated_py=generated_py,
            root_class=decoder.root_class,
            buildinfo_path=buildinfo_path,
        )

    def _compile_ksy(self, ksy_path: Path, out_dir: Path) -> None:
        """
        Invoke the Kaitai compiler to generate a Python parser.
        """
        if not ksy_path.exists():
            raise FileNotFoundError(f"KSY file not found: {ksy_path}")

        subprocess.run(
            [
                self.config.ksc_bin,
                "-t",
                "python",
                "-d",
                str(out_dir),
                str(ksy_path),
            ],
            check=True,
        )

    def _is_cache_valid(
        self,
        decoder: DecoderRef,
        generated_py: Path,
        buildinfo_path: Path,
    ) -> bool:
        """
        Check whether a cached generated decoder is still valid.
        """
        if not generated_py.exists():
            return False
        if not buildinfo_path.exists():
            return False
        if not decoder.ksy_path.exists():
            return False

        try:
            info = json.loads(buildinfo_path.read_text(encoding="utf-8"))
        except Exception:
            return False

        current_mtime_ns = decoder.ksy_path.stat().st_mtime_ns

        return (
            info.get("ksy_path") == str(decoder.ksy_path)
            and info.get("ksy_mtime_ns") == current_mtime_ns
            and info.get("generated_py") == str(generated_py)
            and info.get("root_class") == decoder.root_class
            and info.get("target") == "python"
        )

    def _write_buildinfo(
        self,
        decoder: DecoderRef,
        generated_py: Path,
        buildinfo_path: Path,
    ) -> None:
        """
        Write metadata describing a compiled decoder cache entry.
        """
        payload = {
            "ksy_path": str(decoder.ksy_path),
            "ksy_mtime_ns": decoder.ksy_path.stat().st_mtime_ns,
            "generated_py": str(generated_py),
            "root_class": decoder.root_class,
            "target": "python",
        }
        buildinfo_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")