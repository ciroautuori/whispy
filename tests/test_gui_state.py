"""Headless tests for the ViewModel (whispy.gui.state).

These run without a display because :mod:`whispy.gui.state` never imports Tk.
What we lock down:
- dot_color priority (testing > needs_key > has_key > active)
- FormState round-trips into :class:`whispy.config.Config`
- raw_whisper_model_line reads '' when the field is absent (so auto-detect stays free)
"""

from __future__ import annotations

from pathlib import Path

from whispy.config import Config
from whispy.gui.state import FormState, dot_color, raw_whisper_model_line


def test_dot_color_recording_wins_over_everything() -> None:
    # a row being tested shows amber even if it would otherwise be danger/muted
    assert dot_color("groq", "local", {}, testing="groq") == "#e0a659"


def test_dot_color_no_key_needed_is_muted() -> None:
    assert dot_color("local", "local", {}) == "#8b8f99"
    # active flag is irrelevant when no key is needed
    assert dot_color("ollama", "ollama", {}) == "#8b8f99"


def test_dot_color_key_set_is_teal() -> None:
    assert dot_color("groq", "local", {"GROQ_API_KEY": "sk-..."}) == "#5fb0a8"
    # even the active provider with a key is teal, not amber
    assert dot_color("groq", "groq", {"GROQ_API_KEY": "sk-..."}) == "#5fb0a8"


def test_dot_color_missing_key_is_danger_only_if_active() -> None:
    assert dot_color("nvidia", "nvidia", {"NVIDIA_API_KEY": ""}) == "#e2635a"
    # missing key on an inactive row is just muted, not an alarm
    assert dot_color("nvidia", "local", {"NVIDIA_API_KEY": ""}) == "#8b8f99"


def test_dot_color_whitespace_only_key_counts_as_missing() -> None:
    assert dot_color("openai", "openai", {"OPENAI_API_KEY": "   "}) == "#e2635a"


def test_form_state_round_trips_into_config(tmp_path: Path) -> None:
    s = FormState(
        provider="groq",
        cloud_model="whisper-large-v3-turbo",
        whisper_language="en",
        whisper_threads=4,
        silence_duration=2.5,
        silence_threshold=5,
        max_record_seconds=60,
        autopaste=False,
        keep_audio=True,
        ptt_key="CTRL+SPACE",
        notify_level="quiet",
        keys={"GROQ_API_KEY": "k"},
    )
    cfg = s.to_config()
    assert isinstance(cfg, Config)
    assert cfg.provider == "groq"
    assert cfg.cloud_model == "whisper-large-v3-turbo"
    assert cfg.whisper_language == "en"
    assert cfg.whisper_threads == 4
    assert cfg.silence_duration == 2.5
    assert cfg.silence_threshold == 5
    assert cfg.max_record_seconds == 60
    assert cfg.autopaste is False
    assert cfg.keep_audio is True
    assert cfg.ptt_key == "CTRL+SPACE"
    assert cfg.notify_level == "quiet"


def test_form_state_fills_blanks_with_sane_defaults() -> None:
    # an empty provider falls back to local instead of ""; notify falls back to normal
    s = FormState(provider="", notify_level="", ptt_key="")
    cfg = s.to_config()
    assert cfg.provider == "local"
    assert cfg.notify_level == "normal"
    assert cfg.ptt_key == "META+F12"
    # an empty ollama host keeps its default, not blank
    s2 = FormState(provider="ollama", ollama_host="")
    assert s2.to_config().ollama_host == "http://localhost:11434"


def test_form_state_int_fields_fall_back_on_garbage() -> None:
    # GUI Spinbox can hold a non-numeric string while typing; we must not crash on save
    s = FormState(
        whisper_threads="??",
        silence_threshold="x",
        max_record_seconds="",
        silence_duration="not-a-number",
    )
    cfg = s.to_config()
    assert cfg.whisper_threads == 8  # Config default
    assert cfg.silence_threshold == 3
    assert cfg.max_record_seconds == 120
    assert cfg.silence_duration == 1.5


def test_raw_whisper_model_line_returns_blank_when_unset(tmp_path: Path) -> None:
    conf = tmp_path / "whispy.conf"
    conf.write_text("WHISPER_LANGUAGE=it\nOTHER=value\n", encoding="utf-8")
    assert raw_whisper_model_line(conf) == ""
    conf.write_text('WHISPER_MODEL="/opt/m.bin"\n', encoding="utf-8")
    assert raw_whisper_model_line(conf) == "/opt/m.bin"


def test_raw_whisper_model_line_blank_when_file_missing(tmp_path: Path) -> None:
    assert raw_whisper_model_line(tmp_path / "nope.conf") == ""
