"""OpenRouter (routes to Whisper/GPT-4o-transcribe/etc). Needs ``OPENROUTER_API_KEY``.

OpenRouter's dedicated ``/audio/transcriptions`` endpoint is recent (May
2026) — model slugs are provider-prefixed, e.g. ``openai/whisper-large-v3``.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from .base import openai_compatible_transcribe


def transcribe(cfg: Config, wav_path: Path) -> str:
    return openai_compatible_transcribe(
        cfg,
        wav_path,
        base_url="https://openrouter.ai/api/v1/audio/transcriptions",
        default_model="openai/whisper-large-v3-turbo",
        env_var="OPENROUTER_API_KEY",
        label="OpenRouter",
    )
