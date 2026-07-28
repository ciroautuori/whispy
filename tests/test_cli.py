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


def test_providers_command_lists_backends(capsys) -> None:
    import sys

    from whispy.providers import PROVIDER_NAMES

    old = sys.argv
    try:
        sys.argv = ["whispy", "providers"]
        assert main() == 0
        out = capsys.readouterr().out
        for name in PROVIDER_NAMES:
            assert name in out
    finally:
        sys.argv = old


def test_package_version_matches_pyproject() -> None:
    """`whispy version` printed 0.2.0 while the package shipped as 0.4.0."""
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert declared == __version__


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
