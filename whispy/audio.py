"""Audio recording helpers for Whispy.

Records microphone audio to a WAV file using either sox (`rec`) or ALSA
(`arecord`), with configurable silence detection to stop automatically once
the user stops talking.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import sys
from pathlib import Path

from .config import Config


def _sox_available() -> bool:
    return bool(shutil.which("rec") or shutil.which("sox"))


def _arecord_available() -> bool:
    return bool(shutil.which("arecord"))


def record(cfg: Config) -> Path:
    """Record microphone audio to ``cfg.audio_file``.

    Stops on silence (if ``cfg.silence_duration > 0`` and the backend supports
    it) or after ``cfg.max_record_seconds``. Returns the WAV path.
    """
    wav = cfg.audio_file
    wav.parent.mkdir(parents=True, exist_ok=True)

    if _sox_available():
        _record_sox(cfg, wav)
    elif _arecord_available():
        _record_arecord(cfg, wav)
    else:
        print(
            "[whispy] neither sox/rec nor arecord found — cannot record",
            file=sys.stderr,
        )
        sys.exit(1)
    return wav


def _record_sox(cfg: Config, wav: Path) -> None:
    """Record using sox `rec` with silence detection."""
    rec_bin = shutil.which("rec") or shutil.which("sox")
    cmd = [
        rec_bin,
        "-q",
        "-r",
        "16000",
        "-c",
        "1",
        "-b",
        "16",
        "-e",
        "signed-integer",
        str(wav),
        "silence",
    ]
    if cfg.silence_duration > 0:
        cmd += [
            "1",
            f"{cfg.silence_duration}",
            f"{cfg.silence_threshold}%",
            "1",
            f"{cfg.silence_duration}",
            f"{cfg.silence_threshold}%",
        ]
    cmd += ["restart"]
    timeout = cfg.max_record_seconds if cfg.max_record_seconds > 0 else None
    with contextlib.suppress(subprocess.TimeoutExpired):
        subprocess.run(cmd, check=False, timeout=timeout)


def _record_arecord(cfg: Config, wav: Path) -> None:
    """Record using ALSA arecord (no silence detection available)."""
    device = cfg.record_device or "default"
    cmd = [
        "arecord",
        "-q",
        "-D",
        device,
        "-r",
        "16000",
        "-c",
        "1",
        "-f",
        "S16_LE",
        str(wav),
    ]
    timeout = cfg.max_record_seconds if cfg.max_record_seconds > 0 else None
    with contextlib.suppress(subprocess.TimeoutExpired):
        subprocess.run(cmd, check=False, timeout=timeout)
