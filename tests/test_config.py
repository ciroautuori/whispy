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


def test_set_key_preserves_comments_and_other_lines(tmp_path: Path) -> None:
    """`whispy use` must not cost the user the notes they wrote in the file.

    Config.save() rewrites the whole file from the dataclass, which drops
    every comment — hence a separate single-line edit.
    """
    conf = tmp_path / "whispy.conf"
    conf.write_text(
        "# i miei appunti\nWHISPER_LANGUAGE=it\n# non cancellarmi\nWHISPER_THREADS=12\n",
        encoding="utf-8",
    )
    Config().set_key("PROVIDER", "groq", conf)
    assert conf.read_text(encoding="utf-8") == (
        "# i miei appunti\n"
        "WHISPER_LANGUAGE=it\n"
        "# non cancellarmi\n"
        "WHISPER_THREADS=12\n"
        "PROVIDER=groq\n"
    )


def test_set_key_replaces_in_place(tmp_path: Path) -> None:
    conf = tmp_path / "whispy.conf"
    conf.write_text("PROVIDER=local\nWHISPER_THREADS=8\n", encoding="utf-8")
    Config().set_key("PROVIDER", "openai", conf)
    assert conf.read_text(encoding="utf-8") == "PROVIDER=openai\nWHISPER_THREADS=8\n"


def test_set_key_ignores_a_commented_out_line(tmp_path: Path) -> None:
    conf = tmp_path / "whispy.conf"
    conf.write_text("# PROVIDER=openai\n", encoding="utf-8")
    Config().set_key("PROVIDER", "groq", conf)
    assert conf.read_text(encoding="utf-8") == "# PROVIDER=openai\nPROVIDER=groq\n"


def test_set_key_creates_the_file(tmp_path: Path) -> None:
    conf = tmp_path / "sub" / "whispy.conf"
    Config().set_key("PROVIDER", "groq", conf)
    assert conf.read_text(encoding="utf-8") == "PROVIDER=groq\n"


def test_set_key_round_trips_through_load(tmp_path: Path) -> None:
    conf = tmp_path / "whispy.conf"
    conf.write_text("# hi\nWHISPER_LANGUAGE=en\n", encoding="utf-8")
    Config().set_key("PROVIDER", "groq", conf)
    assert Config.load(conf).provider == "groq"
