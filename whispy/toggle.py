"""Toggle daemon for Whispy.

Implements the classic "press once to record, press again to transcribe and
paste" loop from whisper-toggle. Uses a lockfile to coordinate between rapid
invocations triggered by a hotkey daemon.
"""

from __future__ import annotations

import contextlib
import os
import sys
import time
from pathlib import Path

from . import paste
from .audio import record
from .config import Config
from .transcribe import Transcriber, TranscriptionError

DEBOUNCE_SECONDS = 0.4


def _is_active(lock: Path) -> bool:
    """Return True if a recording session is currently active."""
    if not lock.exists():
        return False
    try:
        pid = int(lock.read_text().strip())
    except (ValueError, OSError):
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock(lock: Path) -> bool:
    """Write our PID into the lockfile. Returns True on success."""
    try:
        lock.write_text(str(os.getpid()))
        return True
    except OSError:
        return False


def _release_lock(lock: Path) -> None:
    """Remove the lockfile if it matches our PID."""
    try:
        if lock.exists() and lock.read_text().strip() == str(os.getpid()):
            lock.unlink()
    except OSError:
        pass


def toggle(cfg: Config | None = None) -> int:
    """Run one toggle step: start recording or stop+transcribe+paste."""
    cfg = cfg or Config.load()
    lock = cfg.lock_file
    debounce = cfg.debounce_file

    if debounce.exists():
        try:
            elapsed = time.time() - debounce.stat().st_mtime
            if elapsed < DEBOUNCE_SECONDS:
                return 0
        except OSError:
            pass
    debounce.touch()

    if _is_active(lock):
        try:
            rec_pid = int(lock.read_text().strip())
            os.kill(rec_pid, 15)  # SIGTERM
        except (ValueError, OSError):
            pass
        _release_lock(lock)
        _transcribe_and_paste(cfg)
        return 0

    if not _acquire_lock(lock):
        print("[whispy] could not acquire lock", file=sys.stderr)
        return 1

    pid = os.fork()
    if pid == 0:  # child
        try:
            record(cfg)
        finally:
            _release_lock(lock)
        os._exit(0)
    return 0


def _transcribe_and_paste(cfg: Config) -> None:
    """Transcribe the recorded audio and paste the result."""
    wav = cfg.audio_file
    if not wav.exists():
        print("[whispy] no audio file found", file=sys.stderr)
        return
    try:
        text = Transcriber(cfg).transcribe(wav)
    except TranscriptionError as exc:
        print(f"[whispy] transcription failed: {exc}", file=sys.stderr)
        return
    if not text:
        print("[whispy] transcription produced no text", file=sys.stderr)
        return
    if cfg.autopaste:
        paste.paste_text(text)
    else:
        print(text)
    if not cfg.keep_audio:
        with contextlib.suppress(OSError):
            wav.unlink()


def main() -> int:
    """CLI entry point for the toggle command."""
    return toggle()


if __name__ == "__main__":
    sys.exit(main())
