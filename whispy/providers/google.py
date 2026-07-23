"""Google Cloud Speech-to-Text v1 (cloud, plain API key). Needs ``GOOGLE_API_KEY``.

This is the dedicated Speech-to-Text product (simple ``?key=`` auth) — not
Gemini's multimodal audio understanding, which needs a heavier chat-style
request and isn't a dedicated transcription endpoint.

Note: ``cloud_model`` (used by every other provider to pick a model name)
does NOT apply here. Google's ``config.model`` field is a different
namespace (recognition profiles like ``latest_long``, ``phone_call``, not
brand/model names) — passing an arbitrary string into it would silently
break requests, so it's left unset and Google's default is used instead.
"""

from __future__ import annotations

import base64
from pathlib import Path

from ..config import Config
from .base import post_json, read_wav_bytes, require_env

# whispy's short language code -> BCP-47 locale Google expects.
# Extend this if you dictate in a language that isn't here yet.
_LOCALES = {
    "it": "it-IT",
    "en": "en-US",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "pt": "pt-PT",
    "nl": "nl-NL",
    "pl": "pl-PL",
    "ru": "ru-RU",
    "ja": "ja-JP",
    "zh": "zh-CN",
    "ko": "ko-KR",
    "ar": "ar-SA",
}


def _locale(code: str) -> str:
    code = (code or "it").strip().lower()
    if code in _LOCALES:
        return _LOCALES[code]
    # Fail loud rather than silently guessing a locale: transcribing e.g.
    # Portuguese audio against an en-US recognizer produces confident
    # garbage, not an obvious error.
    raise RuntimeError(
        f"Google: no BCP-47 mapping for language {code!r} — "
        f"add one to _LOCALES in providers/google.py (e.g. {code!r}: '{code}-XX')"
    )


def transcribe(cfg: Config, wav_path: Path) -> str:
    api_key = require_env("GOOGLE_API_KEY", "Google Cloud Speech-to-Text")
    body = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": 16000,
            "languageCode": _locale(cfg.whisper_language),
        },
        "audio": {"content": base64.b64encode(read_wav_bytes(wav_path)).decode("ascii")},
    }
    url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
    data = post_json(url, {}, body, timeout=60.0)

    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"Google: {err.get('message', err) if isinstance(err, dict) else err}")

    results = data.get("results") or []
    if not results:
        return ""
    alternatives = results[0].get("alternatives") or []
    return str(alternatives[0].get("transcript") or "").strip() if alternatives else ""
