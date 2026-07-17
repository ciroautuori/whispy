"""Configuration loading and defaults for Whispy.

Reads a INI-style config file (sourced as shell variables for parity with the
classic whisper-toggle.conf) and exposes a typed :class:`Config` object.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _config_dir() -> Path:
    """Return the platform-appropriate config directory for Whispy."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "whispy"
    return Path.home() / ".config" / "whispy"


def _data_dir() -> Path:
    """Return the platform-appropriate data directory for models/cache."""
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "whispy"
    return Path.home() / ".local" / "share" / "whispy"


@dataclass
class Config:
    """Runtime configuration for the Whispy recorder/transcriber."""

    backend: str = "server"
    whisper_server: str = ""
    whisper_cli: str = ""
    whisper_model: str = ""
    whisper_port: int = 58181
    whisper_device: int = 0
    whisper_threads: int = 4
    whisper_language: str = "auto"
    autopaste: bool = True
    silence_duration: float = 3.0
    silence_threshold: int = 3
    record_device: str = ""
    max_record_seconds: int = 120
    keep_audio: bool = False
    log_file: str = ""

    config_dir: Path = field(default_factory=_config_dir)
    data_dir: Path = field(default_factory=_data_dir)

    @property
    def config_file(self) -> Path:
        """Path to the main configuration file."""
        return self.config_dir / "whispy.conf"

    @property
    def audio_file(self) -> Path:
        """Path to the temporary recording WAV file."""
        return Path("/dev/shm/whispy.wav") if Path("/dev/shm").exists() else Path("/tmp/whispy.wav")

    @property
    def lock_file(self) -> Path:
        """Path to the toggle lock file."""
        return Path("/tmp/whispy.lock")

    @property
    def debounce_file(self) -> Path:
        """Path to the debounce state file."""
        return Path("/tmp/whispy-debounce")

    @property
    def default_model(self) -> Path:
        """Default model location."""
        return self.data_dir / "models" / "ggml-base.bin"

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> Config:
        """Load configuration from a file, falling back to defaults."""
        cfg = cls()
        target = Path(path) if path else cfg.config_file
        if not target.exists():
            cfg.whisper_model = str(cfg.default_model)
            return cfg

        for line in target.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lower().replace("-", "_")
            value = value.strip().strip('"').strip("'")
            if not hasattr(cfg, key):
                continue
            current = getattr(cfg, key)
            if isinstance(current, bool):
                setattr(cfg, key, value.lower() in {"1", "true", "yes", "on"})
            elif isinstance(current, int):
                setattr(cfg, key, int(value))
            elif isinstance(current, float):
                setattr(cfg, key, float(value))
            else:
                setattr(cfg, key, value)
        if not cfg.whisper_model:
            cfg.whisper_model = str(cfg.default_model)
        return cfg

    def ensure_dirs(self) -> None:
        """Create config and data directories if missing."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "models").mkdir(parents=True, exist_ok=True)
