"""Local transcription via whisper-cli (whisper.cpp). No API key, no network.

Exposes the same ``transcribe(cfg, wav_path) -> str`` contract as every other
provider module — see ``providers/__init__.py`` for the registry that
dispatches to it.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ..config import Config
from .base import clean_transcript


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


_GPU_FAILURE = re.compile(
    r"ggml_backend|GGML_ASSERT|cuda|cublas|vulkan|out of memory|failed to allocate",
    re.I,
)


def _looks_like_gpu_failure(stderr: str) -> bool:
    """Whether a whisper-cli crash is plausibly the GPU running out of room."""
    return bool(_GPU_FAILURE.search(stderr or ""))


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)


def transcribe(cfg: Config, wav_path: Path) -> str:
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

    raw = proc.stdout if proc.stdout.strip() else proc.stderr
    text = clean_transcript(proc.stdout)
    if not text and proc.stdout.strip():
        return ""
    if not text and raw and raw != proc.stdout:
        text = clean_transcript(raw)
    return text
