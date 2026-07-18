"""A WAV left behind by a killed arecord must still be readable."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from whispy.audio import fix_wav_header


def _make_corrupt_arecord_wav(path: Path, n_samples: int = 16000) -> None:
    """Simulate an interrupted arecord WAV: data size = 0x80000000."""
    pcm = b"\x00\x10" * n_samples  # silence-ish 16-bit
    # fmt chunk 16 bytes PCM mono 16k
    fmt = struct.pack(
        "<HHIIHH",
        1,  # PCM
        1,  # mono
        16000,
        16000 * 2,
        2,
        16,
    )
    # placeholder sizes like arecord mid-stream
    riff_size = 0x80000004
    data_size = 0x80000000
    buf = (
        b"RIFF"
        + struct.pack("<I", riff_size)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<I", 16)
        + fmt
        + b"data"
        + struct.pack("<I", data_size)
        + pcm
    )
    path.write_bytes(buf)


def test_fix_wav_header_repairs_arecord_placeholder(tmp_path: Path) -> None:
    wav = tmp_path / "broken.wav"
    _make_corrupt_arecord_wav(wav, n_samples=8000)

    # before the fix, the wave module reads an absurd frame count
    with wave.open(str(wav), "rb") as w:
        assert w.getnframes() > 1_000_000

    assert fix_wav_header(wav) is True

    with wave.open(str(wav), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getframerate() == 16000
        assert w.getnframes() == 8000
        assert abs(w.getnframes() / w.getframerate() - 0.5) < 0.01


def test_fix_wav_header_rejects_garbage(tmp_path: Path) -> None:
    p = tmp_path / "x.wav"
    p.write_bytes(b"not a wav")
    assert fix_wav_header(p) is False


def test_fix_wav_header_rejects_empty(tmp_path: Path) -> None:
    p = tmp_path / "empty.wav"
    p.write_bytes(b"")
    assert fix_wav_header(p) is False


def test_fix_wav_header_idempotent_on_valid(tmp_path: Path) -> None:
    wav = tmp_path / "ok.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 1000)

    assert fix_wav_header(wav) is True
    with wave.open(str(wav), "rb") as w:
        assert w.getnframes() == 1000
