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


def _run(argv: list[str]) -> int:
    import sys

    old = sys.argv
    try:
        sys.argv = argv
        return main()
    finally:
        sys.argv = old


def test_use_switches_provider(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("WHISPY_NOTIFY_LEVEL", "off")

    from whispy.config import Config

    assert _run(["whispy", "use", "ollama"]) == 0
    assert Config.load().provider == "ollama"
    assert "ollama" in capsys.readouterr().out


def test_use_rejects_an_unknown_provider(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("WHISPY_NOTIFY_LEVEL", "off")

    assert _run(["whispy", "use", "nope"]) == 1
    err = capsys.readouterr().err
    assert "unknown provider" in err and "local" in err


def test_use_without_a_name_explains_itself(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("WHISPY_NOTIFY_LEVEL", "off")

    assert _run(["whispy", "use"]) == 1
    assert "missing provider name" in capsys.readouterr().err


def test_use_warns_when_the_key_is_missing(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("WHISPY_NOTIFY_LEVEL", "off")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    assert _run(["whispy", "use", "groq"]) == 0
    assert "GROQ_API_KEY" in capsys.readouterr().err


def test_desktop_command_writes_the_entry(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    assert _run(["whispy", "desktop"]) == 0
    entry = tmp_path / "data" / "applications" / "whispy.desktop"
    assert entry.exists()
    assert "[Desktop Action dictate]" in entry.read_text(encoding="utf-8")
    assert str(entry) in capsys.readouterr().out
