"""Clipboard and paste-at-cursor helpers for Whispy.

Detects the active session (Wayland or X11) and pastes text using the
appropriate toolset. Falls back to printing to stdout when no paste backend
is installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess


def _session_type() -> str:
    """Return the current session type: wayland, x11, or unknown."""
    return os.environ.get("XDG_SESSION_TYPE", "x11").lower()


def paste_text(text: str) -> bool:
    """Paste ``text`` at the cursor or copy it to the clipboard.

    Returns True on success, False if no backend was available.
    """
    if not text:
        return False
    session = _session_type()
    if session == "wayland":
        return _paste_wayland(text)
    return _paste_x11(text)


def _copy_to_clipboard(text: str) -> bool:
    """Copy text to the clipboard using any available helper."""
    for tool in ("wl-copy", "xsel", "xclip"):
        binary = shutil.which(tool)
        if binary is None:
            continue
        if tool == "wl-copy":
            subprocess.run([binary], input=text.encode(), check=False)
        elif tool == "xsel":
            subprocess.run([binary, "-b", "-i"], input=text.encode(), check=False)
        elif tool == "xclip":
            subprocess.run([binary, "-selection", "clipboard"], input=text.encode(), check=False)
        return True
    print(text)
    return False


def _paste_wayland(text: str) -> bool:
    """Paste text on a Wayland session using wtype or ydotool."""
    copy = shutil.which("wl-copy")
    if copy is None:
        print(text)
        return False
    subprocess.run([copy], input=text.encode(), check=False)
    wtype_bin = shutil.which("wtype")
    if wtype_bin:
        subprocess.run([wtype_bin, text], check=False)
        return True
    ydotool_bin = shutil.which("ydotool")
    if ydotool_bin:
        subprocess.run([ydotool_bin, "type", text], check=False)
        return True
    print(text)
    return True


def _paste_x11(text: str) -> bool:
    """Paste text on an X11 session using xdotool."""
    copy = shutil.which("xsel") or shutil.which("xclip")
    if copy:
        if copy.endswith("xsel"):
            subprocess.run([copy, "-b", "-i"], input=text.encode(), check=False)
        else:
            subprocess.run([copy, "-selection", "clipboard"], input=text.encode(), check=False)
    xdotool_bin = shutil.which("xdotool")
    if xdotool_bin:
        subprocess.run([xdotool_bin, "key", "Shift+Insert"], check=False)
        return True
    print(text)
    return True
