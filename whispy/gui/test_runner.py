"""TestRunner — records real mic audio and runs the real transcriber in a thread.

Owns the bookkeeping the GUI used to inline: enabling/disabling the other test
buttons while one is running, the double-click-to-stop event, and routing
results back onto the Tk main loop via :meth:`root.after`.
"""

from __future__ import annotations

import contextlib
import os
import threading
import time
from pathlib import Path
from tkinter import ttk

from ..audio import fix_wav_header, start_recording, stop_recording
from ..config import Config
from ..providers import PROVIDER_INFO
from ..transcribe import transcribe

RECORD_SECONDS = 5.0


class TestRunner:
    def __init__(self, root, on_result, on_state_change) -> None:
        self._root = root
        self._on_result = on_result
        self._on_state_change = on_state_change
        self.testing_name: str | None = None
        self._stop_event: threading.Event | None = None

    @property
    def busy(self) -> bool:
        return self.testing_name is not None

    def start(self, name: str, button: ttk.Button, build_config, get_key_value) -> None:
        """Kick off a live test of ``name``.

        ``build_config()`` returns a :class:`Config`, ``get_key_value(name)``
        returns the currently-typed key for the provider (may be empty).
        """
        if self.testing_name == name:
            if self._stop_event is not None:
                self._stop_event.set()
            return
        if self.testing_name is not None:
            return

        self.testing_name = name
        self._stop_event = threading.Event()
        self._on_state_change(name, recording=True)
        threading.Thread(
            target=self._worker,
            args=(name, button, build_config, get_key_value),
            daemon=True,
        ).start()

    def _worker(self, name: str, button: ttk.Button, build_config, get_key_value) -> None:
        cfg: Config = build_config()
        cfg.provider = name
        cfg.audio_file = Path("/tmp/whispy-gui-test.wav")

        info = PROVIDER_INFO.get(name, {})
        env_var = str(info.get("env_var") or "")
        if env_var:
            typed = (get_key_value(name) or "").strip()
            if typed:
                os.environ[env_var] = typed

        try:
            proc = start_recording(cfg)
        except RuntimeError as exc:
            self._emit(name, button, f"✗ {exc}", ok=False)
            return

        self._stop_event.wait(timeout=RECORD_SECONDS)
        with contextlib.suppress(Exception):
            stop_recording(proc.pid)
        time.sleep(0.12)

        if not fix_wav_header(cfg.audio_file):
            self._emit(name, button, "✗ invalid audio — try again", ok=False)
            return
        if not cfg.audio_file.exists() or cfg.audio_file.stat().st_size <= 44:
            self._emit(name, button, "✗ no audio captured", ok=False)
            return

        try:
            text = transcribe(cfg, cfg.audio_file)
        except RuntimeError as exc:
            self._emit(name, button, f"✗ {exc}", ok=False)
            return

        if text:
            self._emit(name, button, f"✓ {name}: “{text}”", ok=True)
        else:
            self._emit(
                name,
                button,
                "✓ connected, but heard no speech — try again, closer to the mic",
                ok=True,
            )

    def _emit(self, name: str, button: ttk.Button, msg: str, *, ok: bool) -> None:
        def _update():
            self.testing_name = None
            self._stop_event = None
            self._on_result(msg, ok=ok)
            self._on_state_change(name, recording=False)

        self._root.after(0, _update)
