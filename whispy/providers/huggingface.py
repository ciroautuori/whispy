"""Hugging Face Inference (serverless, cloud). Needs ``HF_TOKEN``.

Unlike the OpenAI-compatible trio, this endpoint wants the raw audio bytes
as the request body — no multipart, no JSON wrapper. Serverless models can
be cold on first call (503 while it spins up), so we retry once.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..config import Config
from .base import post_binary, read_wav_bytes, require_env


def transcribe(cfg: Config, wav_path: Path) -> str:
    token = require_env("HF_TOKEN", "Hugging Face")
    model = (cfg.cloud_model or "").strip() or "openai/whisper-large-v3"
    url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "audio/wav"}
    data = read_wav_bytes(wav_path)

    try:
        result = post_binary(url, headers, data, timeout=60.0)
    except RuntimeError as exc:
        if "HTTP 503" not in str(exc):
            raise
        time.sleep(4.0)  # model is loading — one retry beats failing outright
        result = post_binary(url, headers, data, timeout=60.0)

    if "error" in result:
        raise RuntimeError(f"Hugging Face: {result['error']}")
    return str(result.get("text") or "").strip()
