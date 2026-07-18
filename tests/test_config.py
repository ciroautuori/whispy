"""Config parsing: defaults, key=value file, and env overrides."""

from __future__ import annotations

from pathlib import Path

from whispy.config import Config


def test_load_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.delenv("WHISPY_AUDIO", raising=False)
    monkeypatch.delenv("WHISPY_LOCK", raising=False)
    cfg = Config.load()
    assert cfg.whisper_language == "it"
    assert cfg.autopaste is True
    assert cfg.whisper_threads == 8
    # resolve_model: with nothing under the data dir, the path falls back to ggml-base.bin
    assert cfg.whisper_model.endswith(".bin")


def test_load_key_values(tmp_path: Path) -> None:
    conf = tmp_path / "whispy.conf"
    conf.write_text(
        "\n".join(
            [
                "# comment",
                "WHISPER_LANGUAGE=it",
                "WHISPER_THREADS=8",
                "AUTOPASTE=0",
                'WHISPER_MODEL="/opt/m.bin"',
                f"AUDIO_FILE={tmp_path / 'a.wav'}",
                f"LOCK_FILE={tmp_path / 'l.lock'}",
            ]
        ),
        encoding="utf-8",
    )
    cfg = Config.load(conf)
    assert cfg.whisper_language == "it"
    assert cfg.whisper_threads == 8
    assert cfg.autopaste is False
    assert cfg.whisper_model == "/opt/m.bin"
    assert cfg.audio_file == tmp_path / "a.wav"
    assert cfg.lock_file == tmp_path / "l.lock"


def test_env_override_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WHISPY_AUDIO", str(tmp_path / "x.wav"))
    monkeypatch.setenv("WHISPY_LOCK", str(tmp_path / "x.lock"))
    cfg = Config()
    assert cfg.audio_file == tmp_path / "x.wav"
    assert cfg.lock_file == tmp_path / "x.lock"
