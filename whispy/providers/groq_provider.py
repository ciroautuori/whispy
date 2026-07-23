from __future__ import annotations

from pathlib import Path

from .base import TranscribeProvider


class GroqProvider(TranscribeProvider):
    def transcribe(self, audio_path: Path) -> str:
        api_key = getattr(self.cfg, "api_key", "").strip()
        if not api_key:
            raise RuntimeError("Groq API key not found in config (api_key=...)")

        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("groq not installed. Run: pip install groq") from exc

        client = Groq(api_key=api_key)

        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(audio_path.name, file.read()),
                model="whisper-large-v3",
                language=self.cfg.whisper_language or "it",
                response_format="text",
            )

        return str(transcription).strip()
