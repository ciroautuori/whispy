from pathlib import Path

from whispy.config import Config
from whispy.providers.local import build_whisper_cmd, clean_transcript


def test_clean_strips_timestamps_and_parens() -> None:
    raw = "  [00:00.000 --> 00:01.000]  ciao mondo (noise)  "
    assert clean_transcript(raw) == "Ciao mondo"


def test_clean_capitalizes() -> None:
    assert clean_transcript("hello") == "Hello"


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
