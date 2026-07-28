"""Groq audio transcriptions (cloud, OpenAI-compatible). Needs ``GROQ_API_KEY``.

Groq exposes an OpenAI-shaped ``/openai/v1/audio/transcriptions`` endpoint,
so this reuses :func:`base.openai_compatible_transcribe` — no SDK needed.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from .base import openai_compatible_transcribe


def transcribe(cfg: Config, wav_path: Path) -> str:
    return openai_compatible_transcribe(
        cfg,
        wav_path,
        base_url="https://api.groq.com/openai/v1/audio/transcriptions",
        default_model="whisper-large-v3-turbo",
        env_var="GROQ_API_KEY",
        label="Groq",
    )
