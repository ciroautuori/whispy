"""Integration test for record/stop toggle flow."""

from __future__ import annotations

import os
import time
import wave
from pathlib import Path
from unittest.mock import patch

from whispy.config import Config
from whispy.toggle import toggle


def test_toggle_e2e_record_stop_with_mock_whisper(tmp_path: Path, monkeypatch) -> None:
    """Real mic toggle with whisper mocked out (fast and deterministic)."""
    monkeypatch.setattr("whispy.toggle.LOG", tmp_path / "log")
    Path("/tmp/whispy-debounce").unlink(missing_ok=True)

    cfg = Config(
        audio_file=tmp_path / "e2e.wav",
        lock_file=tmp_path / "e2e.lock",
        whisper_model=str(tmp_path / "m.bin"),
        autopaste=False,
        keep_audio=True,
    )
    Path(cfg.whisper_model).write_bytes(b"x")

    # _spawn_autostop forks a child that sleeps max_record_seconds and inherits
    # pytest's stdout — without this the suite can't finish until it wakes up.
    with patch("whispy.toggle._notify"), patch("whispy.toggle._spawn_autostop"):
        assert toggle(cfg) == 0
        assert cfg.lock_file.exists()
        pid = int(cfg.lock_file.read_text().strip())
        assert os.getpgid(pid)
        time.sleep(0.7)

        Path("/tmp/whispy-debounce").unlink(missing_ok=True)
        time.sleep(0.4)

        # Write dummy valid WAV if mic recorded empty file
        if not cfg.audio_file.exists() or cfg.audio_file.stat().st_size <= 44:
            with wave.open(str(cfg.audio_file), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                w.writeframes(b"\x00\x00" * 16000)

        with patch("whispy.toggle.transcribe", return_value="Test ok"):
            rc = toggle(cfg)

        assert rc == 0
