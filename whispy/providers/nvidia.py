"""NVIDIA ASR — Parakeet/Canary/Nemotron via Riva/NIM. Needs ``NVIDIA_API_KEY``.

Architecturally different from every other cloud provider here: NVIDIA's
speech models speak gRPC, not plain HTTP JSON — there is no REST endpoint
to POST a WAV to. This needs the ``nvidia-riva-client`` package (lazily
imported below, same pattern as ``evdev`` in ``ptt.py``, so its absence
only breaks this one provider).

The cloud route also needs a ``function-id``: a UUID tied to the *specific*
ASR model you pick (Parakeet CTC 0.6B, Parakeet RNNT multilingual, Canary,
Nemotron ASR streaming, ...). It isn't hardcoded here on purpose — NVIDIA's
catalog changes, and guessing wrong silently routes to the wrong model.
Get yours from the model's own page on https://build.nvidia.com (each
model's "API Reference" tab shows its function-id) and set
``nvidia_function_id`` in whispy.conf.

Alternatively, if you're running your own NIM container (self-hosted, no
function-id needed), set ``nvidia_server`` to its ``host:port`` and this
skips the cloud endpoint entirely.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from .base import read_wav_bytes, require_env

# whispy's short code -> Riva's expected BCP-47-ish language code.
_LANGS = {"it": "it-IT", "en": "en-US", "es": "es-US", "fr": "fr-FR", "de": "de-DE"}


def transcribe(cfg: Config, wav_path: Path) -> str:
    try:
        import riva.client
    except ImportError as exc:
        raise RuntimeError(
            "NVIDIA provider needs: pip install nvidia-riva-client --break-system-packages"
        ) from exc

    server = (getattr(cfg, "nvidia_server", "") or "").strip()
    function_id = (getattr(cfg, "nvidia_function_id", "") or "").strip()

    if server:
        # self-hosted NIM container — no API key, no function-id
        auth = riva.client.Auth(uri=server)
    else:
        api_key = require_env("NVIDIA_API_KEY", "NVIDIA")
        if not function_id:
            raise RuntimeError(
                "NVIDIA cloud needs nvidia_function_id in whispy.conf — "
                "copy it from your chosen ASR model's API Reference page on build.nvidia.com"
            )
        auth = riva.client.Auth(
            use_ssl=True,
            uri="grpc.nvcf.nvidia.com:443",
            metadata_args=[
                ["function-id", function_id],
                ["authorization", f"Bearer {api_key}"],
            ],
        )

    asr = riva.client.ASRService(auth)
    lang = _LANGS.get((cfg.whisper_language or "it").strip().lower(), "en-US")
    config = riva.client.RecognitionConfig(
        encoding=riva.client.AudioEncoding.LINEAR_PCM,
        sample_rate_hertz=16000,
        language_code=lang,
        max_alternatives=1,
        enable_automatic_punctuation=True,
        audio_channel_count=1,
    )

    try:
        # NOTE: offline_recognize is the single-file (non-streaming) call
        # matching Riva's transcribe_file.py reference script. If your
        # installed nvidia-riva-client version exposes this differently,
        # `python3 -c "import riva.client, inspect; print([m for m in
        # dir(riva.client.ASRService) if 'recognize' in m.lower()])"` will
        # show the current method name.
        response = asr.offline_recognize(read_wav_bytes(wav_path), config)
    except Exception as exc:  # noqa: BLE001 — surface whatever gRPC raised, cleanly
        raise RuntimeError(f"NVIDIA: {exc}") from exc

    results = getattr(response, "results", None) or []
    if not results:
        return ""
    alternatives = getattr(results[0], "alternatives", None) or []
    return str(alternatives[0].transcript).strip() if alternatives else ""
