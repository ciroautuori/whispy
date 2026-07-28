"""``python -m whispy`` / ``whispy`` — dictation toggle and GUI control panel."""

from __future__ import annotations

import sys

from . import __version__
from .toggle import toggle


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help", "help"}:
        print("whispy — press to record, press to transcribe and paste")
        print("usage: whispy | whispy gui | whispy ptt | whispy providers | whispy version")
        print("  gui       = open desktop control panel to manage providers & keys")
        print("  ptt       = push-to-talk: hold the key down, release to transcribe")
        print("  providers = list transcription backends and the key each one needs")
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "version":
        print(__version__)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "providers":
        from .providers import describe_providers

        print(describe_providers())
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
            f"[whispy] unknown: {sys.argv[1]!r} — use: "
            "whispy | whispy gui | whispy ptt | whispy providers | whispy version",
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
