"""Toggle start/stop against a mocked recorder."""

from __future__ import annotations

import os
import time
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from whispy.config import Config
from whispy.toggle import MIN_AGE_STOP, STARTED_AT, toggle


def _cfg(tmp: Path) -> Config:
    return Config(
        whisper_model=str(tmp / "model.bin"),
        whisper_language="it",
        autopaste=False,
        keep_audio=True,
        audio_file=tmp / "a.wav",
        lock_file=tmp / "l.lock",
    )


def _write_wav(path: Path, samples: int = 16000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * samples)


def test_start_writes_lock_and_notifies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("whispy.toggle.LOG", tmp_path / "log")
    Path("/tmp/whispy-debounce").unlink(missing_ok=True)
    STARTED_AT.unlink(missing_ok=True)

    cfg = _cfg(tmp_path)
    mock_proc = MagicMock()
    mock_proc.pid = os.getpid()
    mock_proc.poll.return_value = None

    with (
        patch("whispy.toggle.start_recording", return_value=mock_proc) as start,
        patch("whispy.toggle._notify"),
    ):
        rc = toggle(cfg)

    assert rc == 0
    start.assert_called_once()
    assert cfg.lock_file.read_text().strip() == str(os.getpid())
    assert STARTED_AT.exists()


def test_stop_after_min_age_transcribes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("whispy.toggle.LOG", tmp_path / "log")
    Path("/tmp/whispy-debounce").unlink(missing_ok=True)

    cfg = _cfg(tmp_path)
    _write_wav(cfg.audio_file, 20000)
    cfg.lock_file.write_text(str(os.getpid()))
    # recording "old" enough that stopping is allowed
    STARTED_AT.write_text(str(time.time() - MIN_AGE_STOP - 0.5))

    with (
        patch("whispy.toggle.stop_recording") as stop,
        patch("whispy.toggle.transcribe", return_value="Ciao mondo") as tr,
        patch("whispy.toggle._notify"),
        patch("whispy.toggle.paste.copy_to_clipboard", return_value=True) as copy,
        patch("whispy.toggle.paste.inject_paste") as inject,
    ):
        rc = toggle(cfg)

    assert rc == 0
    stop.assert_called_once()
    tr.assert_called_once()
    copy.assert_called_once()
    inject.assert_not_called()
    assert not cfg.lock_file.exists()


def test_early_stop_ignored_double_fire(tmp_path: Path, monkeypatch) -> None:
    """A second F12 within 50ms must not stop (the bug that killed transcription)."""
    monkeypatch.setattr("whispy.toggle.LOG", tmp_path / "log")
    Path("/tmp/whispy-debounce").unlink(missing_ok=True)
    STARTED_AT.unlink(missing_ok=True)
    cfg = _cfg(tmp_path)

    mock_proc = MagicMock()
    mock_proc.pid = os.getpid()
    mock_proc.poll.return_value = None

    with (
        patch("whispy.toggle.start_recording", return_value=mock_proc),
        patch("whispy.toggle._notify"),
    ):
        assert toggle(cfg) == 0

    with (
        patch("whispy.toggle.stop_recording") as stop,
        patch("whispy.toggle.transcribe") as tr,
        patch("whispy.toggle._notify"),
    ):
        # immediate stop -> ignored
        assert toggle(cfg) == 0
        stop.assert_not_called()
        tr.assert_not_called()

    assert cfg.lock_file.exists()

    # past MIN_AGE_STOP -> stop goes through
    STARTED_AT.write_text(str(time.time() - MIN_AGE_STOP - 0.2))
    _write_wav(cfg.audio_file, 20000)
    with (
        patch("whispy.toggle.stop_recording") as stop,
        patch("whispy.toggle.transcribe", return_value="Ciao"),
        patch("whispy.toggle._notify"),
        patch("whispy.toggle.paste.copy_to_clipboard", return_value=True),
        patch("whispy.toggle.paste.inject_paste", return_value=True),
    ):
        assert toggle(cfg) == 0
        stop.assert_called_once()


def test_double_start_fire_debounced(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("whispy.toggle.LOG", tmp_path / "log")
    Path("/tmp/whispy-debounce").unlink(missing_ok=True)
    cfg = _cfg(tmp_path)
    mock_proc = MagicMock()
    mock_proc.pid = os.getpid()
    mock_proc.poll.return_value = None

    with (
        patch("whispy.toggle.start_recording", return_value=mock_proc) as start,
        patch("whispy.toggle._notify"),
        patch("whispy.toggle._read_lock", return_value=None),
    ):
        assert toggle(cfg) == 0
        assert toggle(cfg) == 0
        assert start.call_count == 1
