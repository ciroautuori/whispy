"""OpenAI audio transcriptions (cloud). Needs ``OPENAI_API_KEY``.

Uses the plain HTTP endpoint via :func:`base.openai_compatible_transcribe`
rather than the ``openai`` SDK: it's the same multipart contract, and it
keeps the project free of a third-party dependency for a handful of POSTs.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from .base import openai_compatible_transcribe


def transcribe(cfg: Config, wav_path: Path) -> str:
    return openai_compatible_transcribe(
        cfg,
        wav_path,
        base_url="https://api.openai.com/v1/audio/transcriptions",
        default_model="whisper-1",
        env_var="OPENAI_API_KEY",
        label="OpenAI",
    )
