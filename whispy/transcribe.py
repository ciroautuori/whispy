"""Transcription dispatcher: routes to the configured provider.

``cfg.provider`` picks the backend (default: ``local``, whisper.cpp — the
original single-provider engine, now at ``providers/local.py``). Cloud
providers (openai, groq, openrouter, huggingface, google, nvidia) and the
best-effort ``ollama`` provider live under ``providers/`` — see
``providers/__init__.py`` for the full list and which environment variable
each cloud provider expects its API key in.

This module's public contract — ``transcribe(cfg, wav_path) -> str`` and
``wav_duration_s(wav_path) -> float`` — is unchanged, so ``toggle.py`` and
``ptt.py`` need no edits.
"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .providers import get_provider
from .providers.base import clean_transcript


def wav_duration_s(wav_path: Path) -> float:
    """Duration of a 16-bit mono WAV (after the header fix). 0 if unknown."""
    try:
        size = wav_path.stat().st_size
    except OSError:
        return 0.0
    # typical header is 44 bytes, 16kHz mono 16-bit = 32000 bytes/s
    data = max(0, size - 44)
    return data / 32000.0


def transcribe(cfg: Config, wav_path: Path) -> str:
    """Run the configured provider and return cleaned, paste-ready text."""
    backend = get_provider(cfg.provider)
    text = backend(cfg, wav_path)
    if not text:
        return ""
    # providers/local.py already cleans its own output (whisper-cli-specific
    # stdout/stderr fallback quirks). Re-cleaning here is harmless —
    # clean_transcript is idempotent — and puts every cloud provider's raw
    # API text on the same paste-ready footing without a special case.
    return clean_transcript(text)
