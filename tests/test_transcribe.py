"""Transcript cleaning and whisper command construction."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from whispy import transcribe as transcribe_mod
from whispy.config import Config
from whispy.transcribe import build_whisper_cmd, clean_transcript


def test_clean_strips_timestamps_and_parens() -> None:
    raw = "  [00:00.000 --> 00:01.000]  ciao mondo (noise)  "
    assert clean_transcript(raw) == "Ciao mondo"


def test_clean_empty_and_junk() -> None:
    assert clean_transcript("") == ""
    assert clean_transcript("...") == ""
    assert clean_transcript("   ") == ""
    assert clean_transcript("*sirra*") == ""
    assert clean_transcript("[BLANK_AUDIO]") == ""


def test_build_whisper_includes_no_speech_thold() -> None:
    cfg = Config(whisper_model="m.bin", whisper_language="it", whisper_threads=4)
    cmd = build_whisper_cmd(cfg, Path("x.wav"), binary="whisper-cli")
    assert "-nth" in cmd


def test_clean_capitalizes() -> None:
    assert clean_transcript("hello") == "Hello"


def test_build_whisper_cmd_flags() -> None:
    cfg = Config(
        whisper_model="/models/ggml-base.bin",
        whisper_language="it",
        whisper_threads=6,
    )
    cmd = build_whisper_cmd(cfg, Path("/tmp/a.wav"), binary="/usr/bin/whisper-cli")
    assert cmd[0] == "/usr/bin/whisper-cli"
    assert "-m" in cmd and "/models/ggml-base.bin" in cmd
    assert "-nt" in cmd and "-np" in cmd
    assert "-l" in cmd and "it" in cmd
    assert "-f" in cmd and "/tmp/a.wav" in cmd
    assert "-t" in cmd and "6" in cmd


def test_build_whisper_cmd_auto_lang() -> None:
    cfg = Config(whisper_model="m.bin", whisper_language="auto")
    cmd = build_whisper_cmd(cfg, Path("x.wav"), binary="whisper-cli")
    assert cmd[cmd.index("-l") + 1] == "auto"


def test_build_whisper_cmd_no_gpu() -> None:
    cfg = Config(whisper_model="m.bin")
    assert "-ng" not in build_whisper_cmd(cfg, Path("x.wav"), binary="whisper-cli")
    assert "-ng" in build_whisper_cmd(cfg, Path("x.wav"), binary="whisper-cli", no_gpu=True)


@pytest.mark.parametrize(
    "stderr",
    [
        "ggml-backend.cpp:194: GGML_ASSERT(buffer) failed",
        "CUDA error: out of memory",
        "failed to allocate compute buffer",
    ],
)
def test_gpu_failures_are_recognized(stderr) -> None:
    assert transcribe_mod._looks_like_gpu_failure(stderr)


@pytest.mark.parametrize("stderr", ["error: unknown argument", "no such file", ""])
def test_other_failures_are_not_gpu(stderr) -> None:
    assert not transcribe_mod._looks_like_gpu_failure(stderr)


def _wav(tmp_path):
    """A file big enough to pass the emptiness check."""
    p = tmp_path / "a.wav"
    p.write_bytes(b"\x00" * 200)
    return p


def test_gpu_crash_retries_on_cpu(tmp_path, monkeypatch) -> None:
    """VRAM taken by another process must not cost the user their dictation."""
    model = tmp_path / "m.bin"
    model.write_bytes(b"x")
    cfg = Config(whisper_model=str(model))
    monkeypatch.setattr(transcribe_mod.shutil, "which", lambda _c: "/usr/bin/whisper-cli")

    calls = []

    def fake_run(cmd, **_kw):
        calls.append(cmd)
        if "-ng" not in cmd:
            raise subprocess.CalledProcessError(-6, cmd, stderr="GGML_ASSERT(buffer) failed")
        return subprocess.CompletedProcess(cmd, 0, stdout="hello there\n", stderr="")

    monkeypatch.setattr(transcribe_mod.subprocess, "run", fake_run)

    assert transcribe_mod.transcribe(cfg, _wav(tmp_path)) == "Hello there"
    assert len(calls) == 2 and "-ng" in calls[1]


def test_non_gpu_crash_does_not_retry(tmp_path, monkeypatch) -> None:
    """A genuine error must surface, not be masked by a pointless CPU retry."""
    model = tmp_path / "m.bin"
    model.write_bytes(b"x")
    cfg = Config(whisper_model=str(model))
    monkeypatch.setattr(transcribe_mod.shutil, "which", lambda _c: "/usr/bin/whisper-cli")

    calls = []

    def fake_run(cmd, **_kw):
        calls.append(cmd)
        raise subprocess.CalledProcessError(1, cmd, stderr="error: unknown argument")

    monkeypatch.setattr(transcribe_mod.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="whisper-cli failed"):
        transcribe_mod.transcribe(cfg, _wav(tmp_path))
    assert len(calls) == 1
