"""Provider registry: maps ``cfg.provider`` to a transcription backend.

Each provider module exposes ``transcribe(cfg, wav_path) -> str`` and raises
``RuntimeError`` with a clear, actionable message on failure.

Cloud providers read their API key from an environment variable, never from
``whispy.conf`` (that file is plaintext). Set the relevant one before use:

    provider       env var              default model
    ------------   ------------------   -----------------------------
    local          (none)               ggml model on disk, unchanged
    openai         OPENAI_API_KEY       whisper-1
    groq           GROQ_API_KEY         whisper-large-v3-turbo
    openrouter     OPENROUTER_API_KEY   openai/whisper-large-v3-turbo
    huggingface    HF_TOKEN             openai/whisper-large-v3
    google         GOOGLE_API_KEY       (Cloud Speech-to-Text v1 default)
    nvidia         NVIDIA_API_KEY       + nvidia_function_id in config
    ollama         (none — local)       qwen2-audio, must be pulled first

Override the model via ``cloud_model=`` in whispy.conf (all providers
except google, whose ``model`` field is a different namespace — see
providers/google.py).

Each import is lazy: a missing dependency (e.g. ``nvidia-riva-client``) only
breaks that one provider, not the whole package.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Config

Transcriber = Callable[["Config", Path], str]

# Single source of truth for "what does each provider need" — the CLI table
# (describe_providers, below) and the GUI (gui.py) both read this instead of
# keeping two copies of the same mapping in sync by hand.
PROVIDER_INFO: dict[str, dict[str, object]] = {
    "local": {
        "env_var": "",
        "default_model": "on-disk ggml model (unchanged)",
        "needs_key": False,
    },
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "default_model": "whisper-1",
        "needs_key": True,
    },
    "groq": {
        "env_var": "GROQ_API_KEY",
        "default_model": "whisper-large-v3-turbo",
        "needs_key": True,
    },
    "openrouter": {
        "env_var": "OPENROUTER_API_KEY",
        "default_model": "openai/whisper-large-v3-turbo",
        "needs_key": True,
    },
    "huggingface": {
        "env_var": "HF_TOKEN",
        "default_model": "openai/whisper-large-v3",
        "needs_key": True,
    },
    "google": {
        "env_var": "GOOGLE_API_KEY",
        "default_model": "Cloud Speech-to-Text v1 default",
        "needs_key": True,
    },
    "nvidia": {
        "env_var": "NVIDIA_API_KEY",
        "default_model": "+ nvidia_function_id in config",
        "needs_key": True,
    },
    "ollama": {
        "env_var": "",
        "default_model": "qwen2-audio — experimental, must be pulled",
        "needs_key": False,
    },
}

PROVIDER_NAMES: tuple[str, ...] = tuple(PROVIDER_INFO.keys())


def get_provider(name: str) -> Transcriber:
    """Return the ``transcribe(cfg, wav_path)`` function for ``name``."""
    key = (name or "local").strip().lower()
    if key not in PROVIDER_NAMES:
        raise RuntimeError(f"unknown provider {key!r} — choose one of: {', '.join(PROVIDER_NAMES)}")

    if key == "local":
        from .local import transcribe as f
    elif key == "openai":
        from .openai import transcribe as f
    elif key == "groq":
        from .groq import transcribe as f
    elif key == "openrouter":
        from .openrouter import transcribe as f
    elif key == "huggingface":
        from .huggingface import transcribe as f
    elif key == "google":
        from .google import transcribe as f
    elif key == "nvidia":
        from .nvidia import transcribe as f
    else:  # ollama
        from .ollama import transcribe as f
    return f


def describe_providers() -> str:
    """Human-readable table for ``whispy providers`` (see __main__.py)."""
    width = max(len(name) for name in PROVIDER_NAMES)
    key_width = max(len(str(info["env_var"])) for info in PROVIDER_INFO.values()) + 2
    lines = ["provider set via PROVIDER= in whispy.conf:", ""]
    for name in PROVIDER_NAMES:
        info = PROVIDER_INFO[name]
        env = str(info["env_var"]) or ("— (local)" if name == "ollama" else "—")
        env_col = f"{env}*" if info["needs_key"] else env
        lines.append(f"  {name:<{width}}  {env_col:<{key_width}}  {info['default_model']}")
    lines.append("")
    lines.append("(* = needs that env var set)")
    return "\n".join(lines)
