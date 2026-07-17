"""Transcription backends for Whispy.

Talks to whisper.cpp via either a local HTTP server (fast, model kept warm)
or the CLI binary (simpler, no daemon). A single
:func:`Transcriber.transcribe` entrypoint normalizes the result and cleans
speech artifacts.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import Config


class TranscriptionError(RuntimeError):
    """Raised when the transcription backend cannot produce text."""


class Transcriber:
    """Whisper transcription front-end (server or CLI backend)."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def transcribe(self, wav_path: Path) -> str:
        """Return cleaned transcribed text for ``wav_path``."""
        if self.cfg.backend == "server":
            raw = self._run_server(wav_path)
        elif self.cfg.backend == "cli":
            raw = self._run_cli(wav_path)
        else:
            raise TranscriptionError(f"unknown backend: {self.cfg.backend!r}")
        return self._postprocess(raw)

    def _run_server(self, wav_path: Path) -> str:
        """POST the WAV to a running whisper-server and return raw text."""
        import urllib.request

        port = self.cfg.whisper_port
        url = f"http://127.0.0.1:{port}/inference"

        boundary = "whispy-boundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; '
            f'filename="{wav_path.name}"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode()
        body += wav_path.read_bytes()
        body += f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        import urllib.error

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise TranscriptionError(f"whisper-server on port {port} not reachable: {exc}") from exc

    def _run_cli(self, wav_path: Path) -> str:
        """Invoke whisper-cli directly and return raw stdout."""
        binary = shutil.which("whisper-cli") or self.cfg.whisper_cli or "whisper-cli"
        cmd = [
            binary,
            "-m",
            self.cfg.whisper_model,
            "-nt",
            "-t",
            str(self.cfg.whisper_threads),
            "-f",
            str(wav_path),
        ]
        if self.cfg.whisper_language and self.cfg.whisper_language != "auto":
            cmd += ["-l", self.cfg.whisper_language]
        try:
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
        except FileNotFoundError as exc:
            raise TranscriptionError(f"whisper-cli not found: {binary}") from exc
        except subprocess.CalledProcessError as exc:
            raise TranscriptionError(
                f"whisper-cli failed ({exc.returncode}): {(exc.stderr or exc.stdout).strip()}"
            ) from exc
        return proc.stdout.strip()

    @staticmethod
    def _postprocess(text: str) -> str:
        """Strip whisper noise markers and tidy whitespace."""
        import re

        text = re.sub(r"\[.*?\]", "", text)
        text = text.strip()
        if text:
            text = text[0].upper() + text[1:]
        return text
