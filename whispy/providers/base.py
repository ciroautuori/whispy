"""Shared plumbing for every provider: env-var keys, stdlib HTTP, multipart.

No third-party HTTP dependency on purpose — ``evdev`` (ptt-only, lazily
imported) is the sole non-stdlib import in the whole project, and a
dictation toggle doesn't need ``requests`` for a handful of POSTs.

Every provider module exposes ``transcribe(cfg, wav_path) -> str`` and
raises ``RuntimeError`` with a short, actionable message on failure — the
same contract the original single-provider ``transcribe.py`` always had, so
``toggle.py``'s ``except RuntimeError`` handling needs no changes.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import urllib.error
import urllib.request
import uuid
from pathlib import Path

# typical whisper-family hallucinations / no-speech output on silence or noise.
# Moved here (from the old single-provider transcribe.py) so it's one shared
# pass applied uniformly to local *and* cloud output, instead of being
# whisper-cli-specific.
_JUNK = re.compile(
    r"^[\s\*\.\,\-\—\–\?\!…]*$"
    r"|^\*+\w*\*+$"
    r"|^blank audio$"
    r"|^silence$"
    r"|^music$"
    r"|^applause$"
    r"|^you$",  # classic English false positive
    re.I,
)


def clean_transcript(text: str) -> str:
    """Strip model artifacts and normalize whitespace. Nothing else.

    What it deliberately leaves alone, because dictation is not captioning
    and the model already gets these right:

    - **Punctuation.** It used to strip trailing ``.,;:!?`` — so "come stai?"
      pasted as "come stai". Whisper punctuates well; throwing that away
      meant retyping it.
    - **Capitalization.** It used to force the first letter upper. That is
      wrong every time you dictate into the middle of a sentence, and
      redundant otherwise since the model already capitalizes.
    - **Parentheses.** ``(...)`` used to be deleted wholesale to catch
      non-speech notes like "(musica)". It also ate real speech. Bracketed
      ``[...]`` and starred ``*...*`` annotations are still removed, and
      _JUNK below still drops a transcript that is *only* noise.

    Applied once, by :func:`whispy.transcribe.transcribe` — providers return
    their backend's raw text.
    """
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\*+[^*\s]*\*+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or _JUNK.match(text):
        return ""
    if len(text) <= 1:
        return ""
    return text


def require_env(var_name: str, label: str) -> str:
    """Read an API key from the environment, or raise a clear, actionable error.

    Keys live in env vars, not in ``whispy.conf`` (that file is plaintext) —
    set e.g. ``export OPENAI_API_KEY=...`` in your shell profile.
    """
    value = os.environ.get(var_name, "").strip()
    if not value:
        raise RuntimeError(f"{label} needs {var_name} set in your environment")
    return value


def read_wav_bytes(wav_path: Path) -> bytes:
    try:
        return wav_path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"cannot read audio: {wav_path}") from exc


def _do_request(url: str, headers: dict, data: bytes, timeout: float) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed https URLs only
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("request timed out") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"bad response (not JSON): {raw[:200]!r}") from exc


def post_json(url: str, headers: dict, body: dict, timeout: float = 60.0) -> dict:
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", **headers}
    return _do_request(url, headers, data, timeout)


def post_binary(url: str, headers: dict, data: bytes, timeout: float = 60.0) -> dict:
    return _do_request(url, headers, data, timeout)


def post_multipart(
    url: str,
    headers: dict,
    fields: dict[str, str],
    file_bytes: bytes,
    file_name: str,
    file_field: str = "file",
    timeout: float = 60.0,
) -> dict:
    """multipart/form-data POST, hand-rolled since there's no ``requests`` dep."""
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(file_name)[0] or "audio/wav"

    parts: list[bytes] = []
    for key, value in fields.items():
        part = f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'
        parts.append(part.encode())
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_name}"\r\nContent-Type: {ctype}\r\n\r\n'
        ).encode()
        + file_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", **headers}
    return _do_request(url, headers, body, timeout)


def openai_compatible_transcribe(
    cfg,
    wav_path: Path,
    *,
    base_url: str,
    default_model: str,
    env_var: str,
    label: str,
) -> str:
    """Shared body for OpenAI, Groq, and OpenRouter: identical request/response shape.

    All three speak the same ``POST .../audio/transcriptions`` multipart
    contract (OpenRouter added theirs in May 2026 — OpenAI-SDK compatible),
    differing only in base URL, default model, and which API key to read.
    """
    api_key = require_env(env_var, label)
    model = (getattr(cfg, "cloud_model", "") or "").strip() or default_model
    headers = {"Authorization": f"Bearer {api_key}"}
    fields = {"model": model}
    lang = (getattr(cfg, "whisper_language", "") or "").strip()
    if lang:
        fields["language"] = lang

    data = post_multipart(
        base_url, headers, fields, read_wav_bytes(wav_path), wav_path.name, timeout=60.0
    )
    if "error" in data:
        raise RuntimeError(f"{label}: {data['error']}")
    return str(data.get("text") or "").strip()
