from __future__ import annotations

from pathlib import Path

from .base import TranscribeProvider


class OpenAIProvider(TranscribeProvider):
    def transcribe(self, audio_path: Path) -> str:
        api_key = getattr(self.cfg, "api_key", "").strip()
        if not api_key:
            raise RuntimeError("OpenAI API key not found in config (api_key=...)")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai not installed. Run: pip install openai") from exc

        client = OpenAI(api_key=api_key)

        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=file,
                language=self.cfg.whisper_language or "it",
                response_format="text",
            )

        return str(transcription).strip()
