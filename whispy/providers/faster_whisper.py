from __future__ import annotations

import logging
from pathlib import Path

from .base import TranscribeProvider


class FasterWhisperProvider(TranscribeProvider):
    def transcribe(self, audio_path: Path) -> str:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper missing. Run: pip install faster-whisper") from exc

        logging.getLogger("faster_whisper").setLevel(logging.ERROR)

        model_path = getattr(self.cfg, "whisper_model", "")
        if not model_path or not Path(model_path).exists():
            model_path = "large-v3"

        model = WhisperModel(model_path, device="auto", compute_type="default")

        segments, _info = model.transcribe(
            str(audio_path), language=self.cfg.whisper_language or "it", beam_size=5
        )

        text = " ".join([segment.text.strip() for segment in segments])
        return text.strip()
