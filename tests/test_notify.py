"""Notifications must never stack up, nor interrupt when the outcome is obvious."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from whispy import notify


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Every test starts with no stored id and with notify-send/gdbus 'present'."""
    monkeypatch.setattr(notify, "_ID_FILE", tmp_path / "notify-id")
    monkeypatch.setattr(notify.shutil, "which", lambda _cmd: "/usr/bin/stub")
    monkeypatch.delenv("WHISPY_NOTIFY_LEVEL", raising=False)


def _run_ok(stdout: str = "42"):
    return mock.Mock(return_value=mock.Mock(stdout=stdout))


def test_reuses_id_instead_of_stacking():
    """The second notification must replace the first one, not pile on top of it."""
    with mock.patch.object(notify.subprocess, "run", _run_ok("42")) as run:
        notify.notify("● REC")
        assert "-r" not in run.call_args[0][0]  # first call: nothing to replace yet
        notify.notify("⏳ Transcribing…")
        cmd = run.call_args[0][0]
        assert "-r" in cmd and "42" in cmd


def test_transient_for_info_but_not_for_errors():
    """Errors must stay in history; everything else is transient noise."""
    with mock.patch.object(notify.subprocess, "run", _run_ok()) as run:
        notify.notify("hello", "low")
        assert "--transient" in run.call_args[0][0]
        notify.notify("boom", "critical")
        assert "--transient" not in run.call_args[0][0]


@pytest.mark.parametrize(
    ("level", "urgency", "expected"),
    [
        ("normal", "low", 1),
        ("normal", "critical", 1),
        ("quiet", "low", 0),  # in quiet mode info messages disappear…
        ("quiet", "critical", 1),  # …but errors do not
        ("off", "low", 0),
        ("off", "critical", 0),
    ],
)
def test_levels(monkeypatch, level, urgency, expected):
    monkeypatch.setenv("WHISPY_NOTIFY_LEVEL", level)
    with mock.patch.object(notify.subprocess, "run", _run_ok()) as run:
        notify.notify("msg", urgency)
        assert run.call_count == expected


def test_stale_id_is_not_reused(monkeypatch):
    """Replacing an id the server already dropped spawns a second bubble."""
    with mock.patch.object(notify.subprocess, "run", _run_ok("42")):
        notify.notify("● REC")

    # pretend the id file was written long ago
    old = notify._ID_FILE.stat().st_mtime - (notify._ID_TTL_S + 1)
    os.utime(notify._ID_FILE, (old, old))

    with mock.patch.object(notify.subprocess, "run", _run_ok("43")) as run:
        notify.notify("⏳ Transcribing…")
        assert "-r" not in run.call_args[0][0]


def test_close_closes_and_forgets_id():
    with mock.patch.object(notify.subprocess, "run", _run_ok("7")):
        notify.notify("● REC")
    assert notify._ID_FILE.exists()

    with mock.patch.object(notify.subprocess, "run", mock.Mock()) as run:
        notify.close()
        assert "CloseNotification" in " ".join(run.call_args[0][0])
    assert not notify._ID_FILE.exists()


def test_close_without_id_does_not_blow_up():
    notify.close()  # no id stored: must be a silent no-op


def test_missing_notify_send_does_not_blow_up(monkeypatch):
    monkeypatch.setattr(notify.shutil, "which", lambda _cmd: None)
    with mock.patch.object(notify.subprocess, "run") as run:
        notify.notify("msg")
        run.assert_not_called()


def test_unreadable_config_does_not_block_the_notification(monkeypatch):
    """A broken config must never suppress an error message."""

    def _boom(*_a, **_k):
        raise OSError("unreadable config")

    monkeypatch.setattr("whispy.config.Config.load", _boom)
    assert notify._level() == "normal"
