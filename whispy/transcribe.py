"""Local transcription via whisper-cli."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .config import Config

# typical whisper hallucinations / no-speech output on silence or noise
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


def build_whisper_cmd(
    cfg: Config,
    wav_path: Path,
    binary: str | None = None,
    *,
    no_gpu: bool = False,
) -> list[str]:
    """Build the whisper-cli argv (testable without executing)."""
    binary = binary or shutil.which("whisper-cli") or "whisper-cli"
    lang = (cfg.whisper_language or "it").strip() or "it"
    cmd = [
        binary,
        "-m",
        str(cfg.whisper_model),
        "-nt",  # no timestamps
        "-np",  # result only
        "-t",
        str(cfg.whisper_threads),
        "-l",
        lang,
        # less aggressive on "no speech" (the 0.60 default discards too much)
        "-nth",
        "0.4",
        "-f",
        str(wav_path),
    ]
    if no_gpu:
        cmd.insert(1, "-ng")
    return cmd


# whisper.cpp dies with an assertion rather than a clean message when the GPU
# buffer cannot be allocated, so the symptom has to be matched on text.
_GPU_FAILURE = re.compile(
    r"ggml_backend|GGML_ASSERT|cuda|cublas|vulkan|out of memory|failed to allocate",
    re.I,
)


def _looks_like_gpu_failure(stderr: str) -> bool:
    """Whether a whisper-cli crash is plausibly the GPU running out of room."""
    return bool(_GPU_FAILURE.search(stderr or ""))


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)


def clean_transcript(text: str) -> str:
    """Clean whisper stdout → text ready to paste."""
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    # tokens like *sirra* / ** / markdown-ish
    text = re.sub(r"\*+[^*\s]*\*+", "", text)
    text = re.sub(r"\s+", " ", text).strip(" \t\n\r.,;:!?-–—")
    if not text or _JUNK.match(text):
        return ""
    if len(text) <= 1:
        return ""
    return text[0].upper() + text[1:]


def wav_duration_s(wav_path: Path) -> float:
    """Duration of a 16-bit mono WAV (after the header fix). 0 if unknown."""
    try:
        size = wav_path.stat().st_size
    except OSError:
        return 0.0
    # typical header is 44 bytes, 16kHz mono 16-bit = 32000 bytes/s
    data = max(0, size - 44)
    return data / 32000.0


def transcribe(cfg: Config, wav_path: Path) -> str:
    """Run whisper-cli on the WAV and return the cleaned text."""
    binary = shutil.which("whisper-cli")
    if not binary:
        raise RuntimeError("whisper-cli not found (install whisper.cpp)")

    model = Path(cfg.whisper_model)
    if not model.is_file():
        raise RuntimeError(f"model not found: {model}")

    if not wav_path.is_file() or wav_path.stat().st_size <= 44:
        raise RuntimeError(f"empty audio: {wav_path}")

    try:
        proc = _run(build_whisper_cmd(cfg, wav_path, binary))
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("whisper-cli timeout") from exc
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or "").strip()
        # A GPU build dies when VRAM is taken by something else (another model
        # server, a game). The CPU path is slower but always available, so a
        # retry beats handing the user a GGML assertion.
        if not _looks_like_gpu_failure(err):
            raise RuntimeError(f"whisper-cli failed ({exc.returncode}): {err[:300]}") from exc
        try:
            proc = _run(build_whisper_cmd(cfg, wav_path, binary, no_gpu=True))
        except subprocess.TimeoutExpired as exc2:
            raise RuntimeError("whisper-cli timeout (CPU fallback)") from exc2
        except subprocess.CalledProcessError as exc2:
            err2 = (exc2.stderr or exc2.stdout or "").strip()
            raise RuntimeError(
                f"whisper-cli failed on GPU and CPU ({exc2.returncode}): {err2[:200]}"
            ) from exc2

    # some builds also put the text on stderr if -np fails
    raw = proc.stdout if proc.stdout.strip() else proc.stderr
    text = clean_transcript(proc.stdout)
    if not text and proc.stdout.strip():
        # stdout was there but was junk — log-friendly via exception-less return
        return ""
    if not text and raw and raw != proc.stdout:
        text = clean_transcript(raw)
    return text
