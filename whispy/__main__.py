"""``python -m whispy`` / ``whispy`` — dictation toggle."""

from __future__ import annotations

import sys

from . import __version__
from .toggle import toggle


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help", "help"}:
        print("whispy — press to record, press to transcribe and paste")
        print("usage: whispy | whispy ptt | whispy version | whispy-hotkey")
        print("  ptt = push-to-talk: hold the key down, release to transcribe")
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "version":
        print(__version__)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "ptt":
        from .ptt import run

        return run()
    if len(sys.argv) > 1:
        print(
            f"[whispy] unknown: {sys.argv[1]!r} — use: whispy | whispy version",
            file=sys.stderr,
        )
        return 1
    try:
        return toggle()
    except Exception as exc:  # noqa: BLE001 — the hotkey must not die silently
        from pathlib import Path

        msg = f"crash: {exc!r}"
        print(f"[whispy] {msg}", file=sys.stderr)
        with Path("/tmp/whispy.log").open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
