"""``python -m whispy`` / ``whispy`` — dictation toggle and GUI control panel."""

from __future__ import annotations

import os
import sys

from . import __version__
from .toggle import toggle


def use_provider(name: str) -> int:
    """``whispy use <provider>`` — the launcher's right-click menu calls this.

    Writes one line of whispy.conf, refreshes the launcher menu so the active
    marker follows, and says what happened. It runs from a desktop menu with
    no terminal attached, so the notification is the only feedback there is.
    """
    import contextlib

    from . import notify
    from .config import Config
    from .desktop import write as write_desktop
    from .providers import PROVIDER_INFO, PROVIDER_NAMES, normalize

    key = normalize(name)
    if not name.strip() or key not in PROVIDER_INFO:
        problem = "missing provider name" if not name.strip() else f"unknown provider {name!r}"
        print(
            f"[whispy] {problem} — choose one of: {', '.join(PROVIDER_NAMES)}",
            file=sys.stderr,
        )
        notify.notify(f"✗ {problem}", "critical")
        return 1

    cfg = Config.load()
    try:
        target = cfg.set_key("PROVIDER", key)
    except OSError as exc:
        print(f"[whispy] cannot write config: {exc}", file=sys.stderr)
        notify.notify(f"✗ cannot save provider: {exc}", "critical")
        return 1

    info = PROVIDER_INFO[key]
    label = str(info["label"])
    env_var = str(info["env_var"])
    missing_key = bool(info["needs_key"]) and not os.environ.get(env_var, "").strip()

    # the menu only lists ready providers, but the CLI will happily set one
    # that has no key — say so rather than let the next dictation fail
    if missing_key:
        message = f"Provider: {label} — needs {env_var}, add it in whispy gui"
        urgency = "normal"
    else:
        message = f"Provider: {label}"
        urgency = "low"

    print(f"[whispy] provider = {key} ({target})")
    if missing_key:
        print(f"[whispy] warning: {env_var} is not set — add it with: whispy gui", file=sys.stderr)

    # the active marker lives in the .desktop file, so it has to be rewritten
    with contextlib.suppress(RuntimeError):
        write_desktop()

    notify.notify(message, urgency)
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help", "help"}:
        print("whispy — press to record, press to transcribe and paste")
        print("usage: whispy | whispy gui | whispy use <provider> | whispy ptt")
        print("       whispy providers | whispy desktop | whispy version")
        print("  gui       = open desktop control panel to manage providers & keys")
        print("  use       = switch transcription backend, e.g. whispy use groq")
        print("  ptt       = push-to-talk: hold the key down, release to transcribe")
        print("  providers = list transcription backends and the key each one needs")
        print("  desktop   = rewrite the launcher entry and its right-click menu")
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "version":
        print(__version__)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "providers":
        from .providers import describe_providers

        print(describe_providers())
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "use":
        return use_provider(sys.argv[2] if len(sys.argv) > 2 else "")
    if len(sys.argv) > 1 and sys.argv[1] == "desktop":
        from .desktop import write

        try:
            print(f"[whispy] wrote {write()}")
        except RuntimeError as exc:
            print(f"[whispy] {exc}", file=sys.stderr)
            return 1
        return 0
    if len(sys.argv) > 1 and sys.argv[1] in {"gui", "config"}:
        try:
            from .gui import main as gui_main
        except ImportError as exc:
            # Tk ships separately from Python on most distros. A traceback here
            # tells the user nothing they can act on; the package name does.
            print(
                f"[whispy] the control panel needs Tk, which isn't installed ({exc}).\n"
                "         Arch:          sudo pacman -S tk\n"
                "         Debian/Ubuntu: sudo apt install python3-tk\n"
                "         Fedora:        sudo dnf install python3-tkinter\n"
                "         Everything else works without it — try: whispy providers",
                file=sys.stderr,
            )
            return 1
        return gui_main()
    if len(sys.argv) > 1 and sys.argv[1] == "ptt":
        from .ptt import run

        return run()
    if len(sys.argv) > 1:
        print(
            f"[whispy] unknown: {sys.argv[1]!r} — use: whispy | whispy gui | "
            "whispy use <provider> | whispy ptt | whispy providers | "
            "whispy desktop | whispy version",
            file=sys.stderr,
        )
        return 1
    try:
        return toggle()
    except Exception as exc:  # noqa: BLE001
        from pathlib import Path

        msg = f"crash: {exc!r}"
        print(f"[whispy] {msg}", file=sys.stderr)
        with Path("/tmp/whispy.log").open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
