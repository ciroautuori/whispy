"""whispy.env: a small dotenv-style file for API keys, kept apart from whispy.conf.

Why this exists: the GUI (gui.py) can only hand data to *future* whispy
invocations — the KDE hotkey, a fresh terminal — by writing it somewhere
those invocations will read at their own startup. An env var set inside the
GUI's own Python process lives only in that process; it never reaches a
sibling process KDE spawns later for the hotkey. This file plays that
handoff role.

Loaded automatically the moment Config.load() runs (see config.py), which
is the one choke point every entry path — toggle, ptt, and now the GUI —
already goes through, so no other file needed to change for this to work.

Uses os.environ.setdefault(), never overwrite: a key properly exported in
your shell profile always wins over what's in this file. Same trust model
as a plain env var, just persisted to disk since that's the only way a GUI
can pass state forward on Linux. Written with chmod 600 (owner-only).
"""

from __future__ import annotations

import contextlib
import os
import stat
from pathlib import Path

from .config import _config_dir  # same XDG-aware directory as whispy.conf


def env_file_path() -> Path:
    return _config_dir() / "whispy.env"


def load_env_file(path: Path | None = None) -> None:
    """Load KEY=value lines into os.environ. Never overrides an already-set var."""
    target = path or env_file_path()
    if not target.exists():
        return
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def read_env_file(path: Path | None = None) -> dict[str, str]:
    """Current KEY -> value pairs on disk, for the GUI to pre-fill its fields."""
    target = path or env_file_path()
    out: dict[str, str] = {}
    if not target.exists():
        return out
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def write_env_file(values: dict[str, str], path: Path | None = None) -> None:
    """Write KEY=value lines (dropping blanks) and lock the file down to 600."""
    target = path or env_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in sorted(values.items()) if v.strip()]
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    with contextlib.suppress(OSError):  # 600 — this file holds API keys
        target.chmod(stat.S_IRUSR | stat.S_IWUSR)
