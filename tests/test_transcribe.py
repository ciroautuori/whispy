"""Transcript cleanup and the whisper-cli argv.

``clean_transcript`` removes model artifacts and normalizes whitespace, and
does nothing else on purpose — dictation is not captioning. The tests below
pin the three things it used to damage: punctuation, capitalization, and
parenthesised speech.
"""

from pathlib import Path

import pytest

from whispy.config import Config
from whispy.providers.base import clean_transcript
from whispy.providers.local import build_whisper_cmd


def test_strips_bracketed_timestamps() -> None:
    raw = "  [00:00.000 --> 00:01.000]  ciao mondo  "
    assert clean_transcript(raw) == "ciao mondo"


def test_strips_starred_annotations() -> None:
    assert clean_transcript("*sighs* va bene") == "va bene"


@pytest.mark.parametrize(
    "raw",
    [
        "ciao, come stai?",
        "e poi sono uscito.",
        "aspetta! non ho finito...",
        "sì: due cose;",
    ],
)
def test_punctuation_survives(raw: str) -> None:
    # it used to strip trailing .,;:!? — "come stai?" pasted as "come stai"
    assert clean_transcript(raw) == raw


def test_capitalization_is_left_to_the_model() -> None:
    # forcing upper is wrong when dictating into the middle of a sentence
    assert clean_transcript("hello") == "hello"
    assert clean_transcript("Hello") == "Hello"
    assert clean_transcript("iPhone è arrivato") == "iPhone è arrivato"


def test_parenthesised_speech_survives() -> None:
    raw = "ho parlato con Marco (il collega) ieri"
    assert clean_transcript(raw) == raw


def test_whitespace_is_collapsed() -> None:
    assert clean_transcript("  troppi     spazi\n\tqui  ") == "troppi spazi qui"


@pytest.mark.parametrize("junk", ["", "   ", "...", "[BLANK_AUDIO]", "you", "Music", "a"])
def test_junk_becomes_empty(junk: str) -> None:
    assert clean_transcript(junk) == ""


def test_cleaning_twice_changes_nothing() -> None:
    # transcribe.py cleans once, but nothing should break if it ran again
    once = clean_transcript("  [x] ciao, come stai?  ")
    assert clean_transcript(once) == once == "ciao, come stai?"


def test_build_whisper_cmd_defaults(tmp_path: Path) -> None:
    cfg = Config(whisper_model="tiny.bin", whisper_threads=4)
    cmd = build_whisper_cmd(cfg, tmp_path / "in.wav", "/usr/bin/whisper-cli")
    assert cmd[0] == "/usr/bin/whisper-cli"
    assert "-m" in cmd and "tiny.bin" in cmd
    assert "-t" in cmd and "4" in cmd
    assert "-l" in cmd and "it" in cmd
    assert "-ng" not in cmd


def test_build_whisper_cmd_no_gpu(tmp_path: Path) -> None:
    cfg = Config()
    cmd = build_whisper_cmd(cfg, tmp_path / "in.wav", "/usr/bin/whisper-cli", no_gpu=True)
    assert cmd[1] == "-ng"
