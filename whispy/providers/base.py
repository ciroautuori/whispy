from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..config import Config


class TranscribeProvider(ABC):
    def __init__(self, cfg: Config):
        self.cfg = cfg

    @abstractmethod
    def transcribe(self, audio_path: Path) -> str:
        """Transcribe the audio and return the text."""
        pass
