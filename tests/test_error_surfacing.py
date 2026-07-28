"""Failures must reach the user, never disappear.

Regression cover for the outage: a provider raising ImportError (not
RuntimeError) slipped past every ``except RuntimeError`` and, in ptt.py,
past a bare ``contextlib.suppress(Exception)`` — so recording worked, no
text appeared, and nothing was logged or notified.
"""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from whispy.config import Config
from whispy.toggle import _transcribe_and_paste


def _cfg(tmp: Path) -> Config:
    return Config(
        whisper_model=str(tmp / "model.bin"),
        autopaste=False,
        keep_audio=True,
        audio_file=tmp / "a.wav",
        lock_file=tmp / "l.lock",
    )


def _write_wav(path: Path, samples: int = 20000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * samples)


def test_toggle_notifies_on_non_runtime_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("whispy.toggle.LOG", tmp_path / "log")
    cfg = _cfg(tmp_path)
    _write_wav(cfg.audio_file)

    boom = ImportError("cannot import name 'transcribe'")
    with (
        patch("whispy.toggle.transcribe", side_effect=boom),
        patch("whispy.toggle._notify") as notify,
    ):
        rc = _transcribe_and_paste(cfg)

    assert rc == 1
    notify.assert_called_once()
    assert "cannot import name" in notify.call_args.args[0]
    assert notify.call_args.args[1] == "critical"


def test_ptt_reports_instead_of_swallowing(tmp_path: Path, monkeypatch) -> None:
    from whispy import ptt

    monkeypatch.setattr("whispy.toggle.LOG", tmp_path / "log")
    proc = MagicMock()
    proc.pid = 12345

    with (
        patch.object(ptt, "stop_recording"),
        patch.object(ptt, "_transcribe_and_paste", side_effect=ImportError("boom")),
        patch.object(ptt, "_notify") as notify,
    ):
        assert ptt._stop_and_transcribe(_cfg(tmp_path), proc) is None

    messages = [c.args[0] for c in notify.call_args_list]
    assert any("boom" in m for m in messages), messages


def test_gui_test_runner_always_emits_a_result(tmp_path: Path) -> None:
    """A crashing worker used to leave every Test button disabled forever."""
    from whispy.gui.test_runner import TestRunner

    root = MagicMock()
    root.after.side_effect = lambda _ms, fn: fn()
    results: list[tuple[str, bool]] = []
    states: list[tuple[str, bool]] = []

    runner = TestRunner(
        root,
        lambda msg, *, ok: results.append((msg, ok)),
        lambda name, *, recording: states.append((name, recording)),
    )
    runner.testing_name = "local"

    with patch("whispy.gui.test_runner.start_recording", side_effect=ImportError("boom")):
        runner._worker("local", MagicMock(), lambda: _cfg(tmp_path), lambda _n: "")

    assert len(results) == 1
    msg, ok = results[0]
    assert ok is False
    assert "boom" in msg
    # state released, so the panel is usable again
    assert runner.testing_name is None
    assert runner.busy is False
    assert states[-1] == ("local", False)
