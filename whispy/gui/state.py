"""ViewModel — form state with no Tk dependency (so it is unit-testable).

Holds the editable model for every field in the control panel, plus the
small pieces of pure logic the GUI used to inline: provider-dot coloring,
keyboard "show/hide" toggle, and serialization to :class:`whispy.config.Config`.

Keeping this module Tk-free is what lets ``tests/test_gui_state.py`` exercise
the logic without a running X server.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..envfile import read_env_file
from ..providers import PROVIDER_INFO, PROVIDER_NAMES
from .const import ACCENT2, DANGER, MUTED

DOT_RECORDING = "#e0a659"


def initial_keys() -> dict[str, str]:
    """Per-provider key, with whispy.env winning over the live environment."""
    file_keys = read_env_file()
    out: dict[str, str] = {}
    for info in PROVIDER_INFO.values():
        env_var = str(info["env_var"])
        if not env_var:
            continue
        out[env_var] = file_keys.get(env_var) or os.environ.get(env_var, "")
    return out


def raw_whisper_model_line(conf_path: Path) -> str:
    """The literal ``WHISPER_MODEL=`` from the file, or '' if unset/absent.

    Deliberately NOT :attr:`Config.whisper_model` (which ``resolve_model``
    always fills with a concrete guess): showing and saving the guess would
    pin it forever instead of leaving auto-detect free to keep re-checking.
    """
    if not conf_path.exists():
        return ""
    for line in conf_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip().lower().replace("-", "_") == "whisper_model":
            return value.strip().strip('"').strip("'")
    return ""


def dot_color(name: str, provider: str, keys: dict[str, str], testing: str | None = None) -> str:
    """The color for a provider row's status dot.

    - testing is running on this row → recording amber
    - no key needed → muted
    - key set → teal
    - no key + this is the active provider → red (missing key is an error only here)
    - no key + inactive → muted
    """
    if name == testing:
        return DOT_RECORDING
    info = PROVIDER_INFO.get(name, {})
    if not info.get("needs_key"):
        return MUTED
    env_var = str(info["env_var"])
    has_key = bool(keys.get(env_var, "").strip())
    if has_key:
        return ACCENT2
    return DANGER if name == provider else MUTED


@dataclass
class FormState:
    """Plain-form state, serialized to :class:`Config` and to whispy.env on save."""

    provider: str = "local"
    cloud_model: str = ""
    ollama_host: str = "http://localhost:11434"
    nvidia_server: str = ""
    nvidia_function_id: str = ""
    whisper_model: str = ""
    whisper_language: str = "it"
    whisper_threads: int = 8
    silence_duration: float = 1.5
    silence_threshold: int = 3
    max_record_seconds: int = 120
    autopaste: bool = True
    keep_audio: bool = False
    ptt_key: str = "META+F12"
    notify_level: str = "normal"
    keys: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls) -> FormState:
        cfg = Config.load()
        return cls(
            provider=cfg.provider,
            cloud_model=cfg.cloud_model,
            ollama_host=cfg.ollama_host,
            nvidia_server=cfg.nvidia_server,
            nvidia_function_id=cfg.nvidia_function_id,
            whisper_model=raw_whisper_model_line(cfg.config_file),
            whisper_language=cfg.whisper_language,
            whisper_threads=cfg.whisper_threads,
            silence_duration=cfg.silence_duration,
            silence_threshold=cfg.silence_threshold,
            max_record_seconds=cfg.max_record_seconds,
            autopaste=cfg.autopaste,
            keep_audio=cfg.keep_audio,
            ptt_key=cfg.ptt_key,
            notify_level=cfg.notify_level,
            keys=initial_keys(),
        )

    def to_config(self) -> Config:
        cfg = Config()
        cfg.provider = (self.provider or "local").strip()
        cfg.whisper_model = (self.whisper_model or "").strip()
        cfg.whisper_language = (self.whisper_language or "it").strip()
        cfg.cloud_model = (self.cloud_model or "").strip()
        cfg.ollama_host = (self.ollama_host or "http://localhost:11434").strip()
        cfg.nvidia_server = (self.nvidia_server or "").strip()
        cfg.nvidia_function_id = (self.nvidia_function_id or "").strip()
        cfg.autopaste = bool(self.autopaste)
        cfg.keep_audio = bool(self.keep_audio)
        cfg.ptt_key = (self.ptt_key or "META+F12").strip()
        cfg.notify_level = (self.notify_level or "normal").strip()
        cfg.whisper_threads = self._int(self.whisper_threads, 8)
        cfg.silence_threshold = self._int(self.silence_threshold, 3)
        cfg.max_record_seconds = self._int(self.max_record_seconds, 120)
        cfg.silence_duration = self._float(self.silence_duration, 1.5)
        return cfg

    @staticmethod
    def _int(value: object, fallback: int) -> int:
        with contextlib.suppress(ValueError, TypeError):
            return int(value)  # type: ignore[arg-type]
        return fallback

    @staticmethod
    def _float(value: object, fallback: float) -> float:
        with contextlib.suppress(ValueError, TypeError):
            return float(value)  # type: ignore[arg-type]
        return fallback


def provider_key_var_names() -> list[tuple[str, str, bool]]:
    """List of ``(provider_name, env_var, needs_key)`` for row building."""
    out = []
    for name in PROVIDER_NAMES:
        info = PROVIDER_INFO[name]
        out.append((name, str(info["env_var"]), bool(info["needs_key"])))
    return out
