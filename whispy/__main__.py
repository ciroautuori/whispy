"""``python -m whispy`` entrypoint.

Subcommands:
  (default)   toggle — record / transcribe-and-paste (bound to a hotkey)
  record      force-start a recording session
  transcribe  transcribe the latest recording and paste
  serve       run the Second Brain REST+UI server only
  brain       open the Second Brain desktop window (FastAPI + pywebview)
  version     print the installed version
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .audio import record
from .config import Config
from .toggle import (
    _transcribe_and_paste,
)
from .toggle import (
    toggle as toggle_run,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="whispy",
        description="Local speech-to-text and second-brain desktop app.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("record", help="force-start a recording session")
    sub.add_parser("transcribe", help="transcribe the latest recording and paste")

    serve = sub.add_parser("serve", help="run the Second Brain REST+UI server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=58182)

    brain = sub.add_parser("brain", help="open the Second Brain desktop window")
    brain.add_argument("--host", default="127.0.0.1")
    brain.add_argument("--port", type=int, default=58182)
    brain.add_argument("--width", type=int, default=390)
    brain.add_argument("--height", type=int, default=760)

    sub.add_parser("version", help="print the installed version")
    return parser


def main() -> int:
    """Dispatch to the requested subcommand."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "record":
        record(Config.load())
        return 0
    if args.command == "transcribe":
        _transcribe_and_paste(Config.load())
        return 0
    if args.command == "serve":
        from .server import run as server_run

        server_run(host=args.host, port=args.port)
        return 0
    if args.command == "brain":
        from . import webapp

        return webapp.run_cli(args)
    if args.command == "version":
        print(__version__)
        return 0
    # default: toggle
    return toggle_run()


if __name__ == "__main__":
    sys.exit(main())
