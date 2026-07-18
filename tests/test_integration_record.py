"""Integration: real mic recording (skipped when arecord is missing)."""

from __future__ import annotations

import os
import shutil
import time
import wave
from pathlib import Path

import pytest

from whispy.audio import fix_wav_header, start_recording, stop_recording
from whispy.config import Config

arecord = shutil.which("arecord")
pytestmark = pytest.mark.skipif(not arecord, reason="arecord not installed")


def test_record_start_stop_produces_valid_wav(tmp_path: Path) -> None:
    cfg = Config(
        audio_file=tmp_path / "rec.wav",
        lock_file=tmp_path / "rec.lock",
        whisper_model="unused",
    )
    proc = start_recording(cfg)
    assert proc.pid > 0
    time.sleep(0.8)
    assert proc.poll() is None, "recorder died immediately — mic/pulse?"
    stop_recording(proc.pid)
    # wait reaper
    for _ in range(40):
        if proc.poll() is not None:
            break
        time.sleep(0.05)

    assert cfg.audio_file.exists()
    assert cfg.audio_file.stat().st_size > 44
    assert fix_wav_header(cfg.audio_file)

    with wave.open(str(cfg.audio_file), "rb") as w:
        assert w.getframerate() == 16000
        assert w.getnchannels() == 1
        assert w.getnframes() > 1000
        # plausible duration (~0.3-3s)
        dur = w.getnframes() / w.getframerate()
        assert 0.2 < dur < 5.0


def test_toggle_e2e_record_stop_with_mock_whisper(tmp_path: Path, monkeypatch) -> None:
    """Real mic toggle with whisper mocked out (fast and deterministic)."""
    from unittest.mock import patch

    from whispy.toggle import toggle

    monkeypatch.setattr("whispy.toggle.LOG", tmp_path / "log")
    Path("/tmp/whispy-debounce").unlink(missing_ok=True)

    cfg = Config(
        audio_file=tmp_path / "e2e.wav",
        lock_file=tmp_path / "e2e.lock",
        whisper_model=str(tmp_path / "m.bin"),
        autopaste=False,
        keep_audio=True,
    )
    # dummy model file (transcribe is mocked)
    Path(cfg.whisper_model).write_bytes(b"x")

    with patch("whispy.toggle._notify"):
        assert toggle(cfg) == 0
        assert cfg.lock_file.exists()
        pid = int(cfg.lock_file.read_text().strip())
        assert os.getpgid(pid)  # alive
        time.sleep(0.7)

        Path("/tmp/whispy-debounce").unlink(missing_ok=True)
        time.sleep(0.4)

        with patch("whispy.toggle.transcribe", return_value="Test ok"):
            rc = toggle(cfg)

    assert rc == 0
    assert not cfg.lock_file.exists()
    # keep_audio -> the wav survives the header fix
    assert cfg.audio_file.exists()
