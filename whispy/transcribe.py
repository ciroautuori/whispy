"""Delegation to the configured provider."""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .providers import get_provider


def transcribe(cfg: Config, wav_path: Path) -> str:
    """Run the active provider on the WAV and return the cleaned text."""
    provider = get_provider(cfg)
    return provider.transcribe(wav_path)


def wav_duration_s(wav_path: Path) -> float:
    """Duration of a 16-bit mono WAV (after the header fix). 0 if unknown."""
    try:
        size = wav_path.stat().st_size
    except OSError:
        return 0.0
    # typical header is 44 bytes, 16kHz mono 16-bit = 32000 bytes/s
    data = max(0, size - 44)
    return data / 32000.0
