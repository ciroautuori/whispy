from __future__ import annotations

from ..config import Config
from .base import TranscribeProvider


def get_provider(cfg: Config) -> TranscribeProvider:
    provider_name = getattr(cfg, "provider", "local").strip().lower()

    if provider_name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(cfg)
    elif provider_name == "groq":
        from .groq_provider import GroqProvider

        return GroqProvider(cfg)
    elif provider_name == "faster-whisper":
        from .faster_whisper import FasterWhisperProvider

        return FasterWhisperProvider(cfg)
    else:
        from .local import LocalProvider

        return LocalProvider(cfg)
