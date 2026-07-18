"""Discreet notifications: a single bubble that updates, instead of a stack.

Principles:
- **one notification** per cycle: replaced via ``--replace-id``;
- **transient**: does not pollute the notification history;
- **silence when it is obvious**: if the text was pasted you already see it,
  so the notification is closed instead of announcing success;
- **errors stay**: they are the only thing worth an interruption.

Level via ``NOTIFY_LEVEL`` in whispy.conf: ``normal`` | ``quiet`` | ``off``.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import time
from pathlib import Path

# id of the last notification: lets us replace it instead of stacking a new one
_ID_FILE = Path("/tmp/whispy-notify-id")
# past this, assume the server dropped the id and start a fresh bubble
_ID_TTL_S = 30.0

LEVELS = ("normal", "quiet", "off")
_ERROR_URGENCIES = {"critical"}


def _level() -> str:
    """Current level. Env takes precedence over the config (handy for tests)."""
    env = os.environ.get("WHISPY_NOTIFY_LEVEL", "").strip().lower()
    if env in LEVELS:
        return env
    try:
        from .config import Config

        lvl = (Config.load().notify_level or "normal").strip().lower()
    except Exception:  # noqa: BLE001 — a notification must never crash the flow
        return "normal"
    return lvl if lvl in LEVELS else "normal"


def _read_id() -> int | None:
    """Last notification id, but only while it can still plausibly be on screen.

    Replacing an id the server has already forgotten makes Plasma log
    "trying to replace notification with id N which doesn't exist" and spawn a
    second bubble — exactly the stacking this module exists to prevent.
    """
    try:
        age = time.time() - _ID_FILE.stat().st_mtime
        if age > _ID_TTL_S:
            return None
        return int(_ID_FILE.read_text().strip())
    except (OSError, ValueError):
        return None


def _write_id(nid: int | None) -> None:
    if nid is None:
        return
    with contextlib.suppress(OSError):
        _ID_FILE.write_text(str(nid))


def notify(
    msg: str,
    urgency: str = "low",
    timeout_ms: int = 4000,
    *,
    replace: bool = True,
) -> None:
    """Show (or update) the whispy notification."""
    if not shutil.which("notify-send"):
        return

    is_error = urgency in _ERROR_URGENCIES
    lvl = _level()
    if lvl == "off" or (lvl == "quiet" and not is_error):
        return

    cmd = ["notify-send", "-a", "Whispy", "-p", "-t", str(timeout_ms), "-u", urgency]
    # errors deserve to stay in the history; the rest is passing noise
    if not is_error:
        cmd.append("--transient")
    if replace:
        nid = _read_id()
        if nid is not None:
            cmd += ["-r", str(nid)]
    cmd += ["Whispy", msg]

    try:
        out = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError:
        return

    with contextlib.suppress(ValueError, AttributeError):
        _write_id(int(out.stdout.strip()))


def close() -> None:
    """Close the current notification: used when the outcome is already on screen."""
    nid = _read_id()
    if nid is None or not shutil.which("gdbus"):
        return
    with contextlib.suppress(OSError):
        subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.freedesktop.Notifications",
                "--object-path",
                "/org/freedesktop/Notifications",
                "--method",
                "org.freedesktop.Notifications.CloseNotification",
                str(nid),
            ],
            check=False,
            capture_output=True,
        )
    with contextlib.suppress(OSError):
        _ID_FILE.unlink(missing_ok=True)
