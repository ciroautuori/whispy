"""Generate ``whispy.desktop`` — the launcher entry and its right-click menu.

The entry opens the control panel. Its Desktop Actions are the quick menu the
desktop shows on right-click: dictate once, and switch provider without
opening anything.

Only *ready* providers are listed — one that needs an API key you haven't set
would be an option that fails, so it isn't offered until the key exists. The
menu therefore grows as you add keys, which is why this file gets regenerated
by ``whispy use``, by the control panel's Save Keys, and by ``install.sh``.

:func:`render` is deliberately pure: the entire menu can be asserted in tests
with no display, no desktop environment, and no filesystem.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path

from .providers import PROVIDER_INFO, PROVIDER_NAMES, normalize

APP_ID = "whispy"
ICON = "audio-input-microphone"
ACTIVE_MARK = "●"


def applications_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "applications"


def desktop_file_path() -> Path:
    return applications_dir() / f"{APP_ID}.desktop"


def ready_providers(keys: Mapping[str, str] | None = None) -> list[str]:
    """Providers that can run right now, in registry order.

    ``keys`` maps env-var name -> value; when omitted, whispy.env and the
    process environment are consulted. A provider is ready when it needs no
    key, or when the key it needs is present and non-empty.
    """
    if keys is None:
        from .envfile import read_env_file

        file_keys = read_env_file()
        keys = {k: file_keys.get(k) or os.environ.get(k, "") for k in _key_vars()}

    out = []
    for name in PROVIDER_NAMES:
        info = PROVIDER_INFO[name]
        if not info["needs_key"]:
            out.append(name)
            continue
        if (keys.get(str(info["env_var"]), "") or "").strip():
            out.append(name)
    return out


def _key_vars() -> list[str]:
    return [str(i["env_var"]) for i in PROVIDER_INFO.values() if i["env_var"]]


def _action_id(provider: str) -> str:
    """Desktop Entry spec allows only A-Za-z0-9- in action identifiers."""
    return "provider-" + provider.replace("_", "-")


def _quote(command: str) -> str:
    """Quote an Exec program path per the Desktop Entry spec if it needs it."""
    if any(c in command for c in " \t\"'\\$`"):
        escaped = command.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return command


def _resolve(name: str, fallback: str) -> str:
    return shutil.which(name) or str(Path.home() / ".local" / "bin" / fallback)


def render(
    active: str,
    ready: Iterable[str],
    *,
    gui_exec: str | None = None,
    dictate_exec: str | None = None,
    cli_exec: str | None = None,
) -> str:
    """Return the full contents of whispy.desktop. Pure — writes nothing."""
    gui = _quote(gui_exec or _resolve("whispy-gui", "whispy-gui"))
    dictate = _quote(dictate_exec or _resolve("whispy-hotkey", "whispy-hotkey"))
    cli = _quote(cli_exec or _resolve("whispy", "whispy"))

    active = normalize(active)
    ready = [p for p in ready if p in PROVIDER_INFO]
    actions = ["dictate", *(_action_id(p) for p in ready)]

    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=Whispy",
        "GenericName=Voice Dictation",
        "Comment=Speak, and the text lands at your cursor",
        "Comment[it]=Parla, e il testo arriva dove hai il cursore",
        f"Icon={ICON}",
        "Terminal=false",
        # exactly one main category: "Utility;AudioVideo;" makes the launcher
        # list Whispy twice (desktop-file-validate warns about it)
        "Categories=Utility;",
        "Keywords=dictation;speech;voice;whisper;transcription;stt;",
        "StartupNotify=true",
        f"Exec={gui}",
        f"Actions={';'.join(actions)};",
        "",
        "[Desktop Action dictate]",
        "Name=Dictate now",
        "Name[it]=Detta ora",
        f"Exec={dictate}",
    ]

    for provider in ready:
        label = str(PROVIDER_INFO[provider]["label"])
        mark = f"{ACTIVE_MARK} " if provider == active else ""
        lines += [
            "",
            f"[Desktop Action {_action_id(provider)}]",
            f"Name={mark}{label}",
            f"Exec={cli} use {provider}",
        ]

    return "\n".join(lines) + "\n"


def write(path: Path | None = None, *, refresh: bool = True) -> Path:
    """Render the entry for the current config and write it to disk."""
    from .config import Config

    target = path or desktop_file_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(Config.load().provider, ready_providers()), encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"cannot write {target}: {exc}") from exc

    if refresh and shutil.which("update-desktop-database"):
        # best effort: the file is valid either way, this only nudges the
        # desktop into re-reading it sooner
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(
                ["update-desktop-database", str(target.parent)],
                check=False,
                capture_output=True,
                timeout=10,
            )
    return target
