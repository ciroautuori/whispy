"""Microphone recording → 16 kHz mono WAV (arecord or rec)."""

from __future__ import annotations

import contextlib
import shutil
import struct
import subprocess
from pathlib import Path

from .config import Config


def fix_wav_header(path: Path) -> bool:
    """Repair the RIFF/data header after killing arecord (0x80000000 size placeholder).

    arecord writes 'infinite' sizes and only updates them on a clean exit.
    With SIGTERM/SIGINT they stay invalid → whisper reads ~18h of garbage or fails.
    """
    try:
        data = bytearray(path.read_bytes())
    except OSError:
        return False
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return False

    idx = data.find(b"data", 12)
    if idx < 0 or idx + 8 > len(data):
        return False

    data_size = len(data) - (idx + 8)
    if data_size <= 0:
        return False

    struct.pack_into("<I", data, 4, len(data) - 8)
    struct.pack_into("<I", data, idx + 4, data_size)
    try:
        path.write_bytes(data)
    except OSError:
        return False
    return True


def build_record_cmd(wav: Path) -> list[str] | None:
    """Preferred recorder command. arecord+pulse first (rec often gives Out:0 here)."""
    if shutil.which("arecord"):
        return [
            "arecord",
            "-q",
            "-D",
            "pulse",
            "-r",
            "16000",
            "-c",
            "1",
            "-f",
            "S16_LE",
            str(wav),
        ]
    rec = shutil.which("rec") or shutil.which("sox")
    if rec:
        return [
            rec,
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
        ]
    return None


def start_recording(cfg: Config) -> subprocess.Popen[bytes]:
    """Start the recorder in the background (new session). Returns the Popen."""
    wav = cfg.audio_file
    wav.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        wav.unlink(missing_ok=True)

    cmd = build_record_cmd(wav)
    if not cmd:
        raise RuntimeError("need arecord or sox/rec")

    # start_new_session=True → PGID = PID, killpg is safe from the second press
    return subprocess.Popen(
        cmd,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_recording(pid: int, wait_s: float = 2.0) -> None:
    """Stop the recorder's process group and wait for it to exit."""
    import os
    import signal
    import time

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            os.killpg(pid, sig)
            break
        except ProcessLookupError:
            return
        except PermissionError:
            try:
                os.kill(pid, sig)
                break
            except OSError:
                return
        except OSError:
            continue

    deadline = time.time() + wait_s
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.05)

    with contextlib.suppress(OSError):
        os.killpg(pid, signal.SIGKILL)
    with contextlib.suppress(OSError):
        os.kill(pid, signal.SIGKILL)
