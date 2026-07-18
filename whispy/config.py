"""Minimal config: ~/.config/whispy/whispy.conf (KEY=value)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return Path(xdg) / "whispy" if xdg else Path.home() / ".config" / "whispy"


def _data_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) / "whispy" if xdg else Path.home() / ".local" / "share" / "whispy"


def _default_audio() -> Path:
    if os.environ.get("WHISPY_AUDIO"):
        return Path(os.environ["WHISPY_AUDIO"])
    return Path("/dev/shm/whispy.wav") if Path("/dev/shm").exists() else Path("/tmp/whispy.wav")


def _default_lock() -> Path:
    if os.environ.get("WHISPY_LOCK"):
        return Path(os.environ["WHISPY_LOCK"])
    return Path("/tmp/whispy.lock")


def resolve_model(explicit: str = "") -> str:
    """Pick the best available model.

    If ``explicit`` is set it is used as-is (even if missing → clear error later).
    Otherwise: large-v3-turbo (whispy/whisper-toggle) → base → default path.
    """
    if explicit and explicit.strip():
        return str(Path(explicit).expanduser())

    candidates = [
        _data_dir() / "models" / "ggml-large-v3-turbo.bin",
        Path.home() / ".local/share/whisper-toggle/models/ggml-large-v3-turbo.bin",
        _data_dir() / "models" / "ggml-base.bin",
        Path.home() / ".local/share/whisper-toggle/models/ggml-base.bin",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return str(_data_dir() / "models" / "ggml-base.bin")


@dataclass
class Config:
    whisper_model: str = ""
    whisper_language: str = "it"
    whisper_threads: int = 8
    autopaste: bool = True
    silence_duration: float = 1.5
    silence_threshold: int = 3
    max_record_seconds: int = 120
    keep_audio: bool = False
    ptt_key: str = "META+F12"
    notify_level: str = "normal"  # normal | quiet | off
    audio_file: Path = field(default_factory=_default_audio)
    lock_file: Path = field(default_factory=_default_lock)

    @property
    def config_file(self) -> Path:
        return _config_dir() / "whispy.conf"

    @property
    def default_model(self) -> Path:
        return Path(resolve_model())

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> Config:
        cfg = cls()
        target = Path(path) if path else cfg.config_file
        raw_model = ""
        if target.exists():
            for line in target.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().lower().replace("-", "_")
                value = value.strip().strip('"').strip("'")
                if key in {"audio_file", "lock_file"}:
                    setattr(cfg, key, Path(value))
                    continue
                if key == "whisper_model":
                    raw_model = value
                    continue
                if not hasattr(cfg, key):
                    continue
                current = getattr(cfg, key)
                if isinstance(current, bool):
                    setattr(cfg, key, value.lower() in {"1", "true", "yes", "on"})
                elif isinstance(current, int):
                    setattr(cfg, key, int(value))
                elif isinstance(current, float):
                    setattr(cfg, key, float(value))
                elif isinstance(current, Path):
                    setattr(cfg, key, Path(value))
                else:
                    setattr(cfg, key, value)
        cfg.whisper_model = resolve_model(raw_model or cfg.whisper_model)
        return cfg
