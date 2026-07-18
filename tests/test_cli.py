"""CLI entrypoint: every argv shape must exit with a predictable code."""

from __future__ import annotations

from whispy import __version__
from whispy.__main__ import main


def test_version(capsys) -> None:
    import sys

    old = sys.argv
    try:
        sys.argv = ["whispy", "version"]
        assert main() == 0
        assert capsys.readouterr().out.strip() == __version__
    finally:
        sys.argv = old


def test_help(capsys) -> None:
    import sys

    old = sys.argv
    try:
        sys.argv = ["whispy", "--help"]
        assert main() == 0
        out = capsys.readouterr().out
        assert "whispy" in out.lower()
    finally:
        sys.argv = old


def test_unknown(capsys) -> None:
    import sys

    old = sys.argv
    try:
        sys.argv = ["whispy", "nope"]
        assert main() == 1
        err = capsys.readouterr().err
        assert "unknown" in err
    finally:
        sys.argv = old
