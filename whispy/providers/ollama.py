"""Ollama (local) — best-effort, NOT a peer of the other providers.

Important honesty note: Ollama has no dedicated speech-to-text API. It's a
local LLM runtime built around ``/api/generate`` and ``/api/chat`` for text
(and, on some models, images). Audio input is an open, unfinished feature
request upstream (ollama/ollama#11798) — the only way to get a transcript
today is to point a *locally-pulled, audio-capable* model (e.g.
``qwen2-audio``, via ``ollama pull qwen2-audio``) at the audio and ask it
to transcribe, using the same ``audio=[...]`` parameter multimodal image
models use for pictures.

This is genuinely less reliable than the Whisper-family providers: model
availability, audio format support, and output quality vary a lot by which
model you've pulled. Treat this as "worth having a hook for," not "a drop-in
equivalent to Groq/OpenAI." No API key needed since it's local.
"""

from __future__ import annotations

import base64
from pathlib import Path

from ..config import Config
from .base import post_json, read_wav_bytes

_PROMPT = (
    "Transcribe the speech in this audio verbatim, in its original language. "
    "Reply with only the transcript, no commentary."
)


def transcribe(cfg: Config, wav_path: Path) -> str:
    host = (getattr(cfg, "ollama_host", "") or "http://localhost:11434").rstrip("/")
    model = (cfg.cloud_model or "").strip() or "qwen2-audio"
    audio_b64 = base64.b64encode(read_wav_bytes(wav_path)).decode("ascii")

    body = {
        "model": model,
        "prompt": _PROMPT,
        "audio": [audio_b64],
        "stream": False,
    }
    try:
        data = post_json(f"{host}/api/generate", {}, body, timeout=120.0)
    except RuntimeError as exc:
        raise RuntimeError(
            f"Ollama transcription failed ({exc}) — needs a locally-pulled "
            f"audio-capable model (`ollama pull {model}`); Ollama has no "
            "dedicated STT endpoint, this path is best-effort"
        ) from exc

    if "error" in data:
        raise RuntimeError(f"Ollama: {data['error']}")
    return str(data.get("response") or "").strip()
