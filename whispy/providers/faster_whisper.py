"""faster-whisper (local, CTranslate2). No API key, no network.

Needs the optional dependency: ``pip install "whispy[faster-whisper]"``.
Unlike the ``local`` provider (which shells out to whisper.cpp and wants a
``.bin`` ggml model on disk), this loads a CTranslate2 model in-process: if
``whisper_model`` isn't an existing CTranslate2 directory it's treated as a
model *name* (e.g. ``large-v3``) that faster-whisper downloads on first use.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import Config

DEFAULT_MODEL = "large-v3"


def transcribe(cfg: Config, wav_path: Path) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            'faster-whisper not installed — pip install "whispy[faster-whisper]"'
        ) from exc

    logging.getLogger("faster_whisper").setLevel(logging.ERROR)

    # cloud_model doubles as the model-name override here (large-v3, medium, ...).
    # whisper_model is only usable if it points at a real CTranslate2 directory —
    # the ggml .bin the `local` provider uses is a different format entirely.
    model_id = (cfg.cloud_model or "").strip()
    if not model_id:
        candidate = (cfg.whisper_model or "").strip()
        model_id = candidate if candidate and Path(candidate).is_dir() else DEFAULT_MODEL

    try:
        model = WhisperModel(model_id, device="auto", compute_type="default")
        segments, _info = model.transcribe(
            str(wav_path), language=(cfg.whisper_language or "it").strip() or "it", beam_size=5
        )
        text = " ".join(segment.text.strip() for segment in segments)
    except Exception as exc:  # noqa: BLE001 — surface loader/runtime errors cleanly
        raise RuntimeError(f"faster-whisper: {exc}") from exc

    return text.strip()
