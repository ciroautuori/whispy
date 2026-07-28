"""WhispyGUI — the View. Wires widgets to a :class:`FormState` ViewModel.

This is intentionally thin: form state lives in :mod:`whispy.gui.state`,
styling in :mod:`whispy.gui.theme`, reusable widgets in
:mod:`whispy.gui.components`, tab layout in :mod:`whispy.gui.tabs`, and the
live-test worker in :mod:`whispy.gui.test_runner`. What remains here is just
``tk.Variable`` <-> field binding and the few-line callbacks.
"""

from __future__ import annotations

import contextlib
import os
import tkinter as tk
from tkinter import ttk

from ..config import Config
from ..desktop import write as write_desktop
from ..envfile import env_file_path, write_env_file
from . import theme
from .components.status_bar import StatusBar
from .state import FormState, provider_key_var_names
from .tabs import build_log_tab, build_provider_tab, build_recording_tab
from .test_runner import TestRunner


class WhispyGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Whispy — Control Panel")
        # sized from the panel's own requested geometry (898x684 with all nine
        # provider rows): anything narrower clipped the key fields on the right
        self.root.geometry("920x720")
        self.root.minsize(820, 600)

        state = FormState.load()
        self._state = state

        self.rows: dict[str, object] = {}
        self.var_provider = tk.StringVar(value=state.provider)
        self.var_cloud_model = tk.StringVar(value=state.cloud_model)
        self.var_ollama_host = tk.StringVar(value=state.ollama_host)
        self.var_nvidia_server = tk.StringVar(value=state.nvidia_server)
        self.var_nvidia_function_id = tk.StringVar(value=state.nvidia_function_id)
        self.var_whisper_model = tk.StringVar(value=state.whisper_model)
        self.var_whisper_language = tk.StringVar(value=state.whisper_language)
        self.var_whisper_threads = tk.StringVar(value=str(state.whisper_threads))
        self.var_autopaste = tk.BooleanVar(value=state.autopaste)
        self.var_silence_duration = tk.StringVar(value=str(state.silence_duration))
        self.var_silence_threshold = tk.StringVar(value=str(state.silence_threshold))
        self.var_max_record_seconds = tk.StringVar(value=str(state.max_record_seconds))
        self.var_keep_audio = tk.BooleanVar(value=state.keep_audio)
        self.var_ptt_key = tk.StringVar(value=state.ptt_key)
        self.var_notify_level = tk.StringVar(value=state.notify_level)

        # status bar first so callbacks have somewhere to write
        self.status = StatusBar(self.root)
        self.status.pack(fill="x", side="bottom", padx=16, pady=12)

        self.runner = TestRunner(root, self._on_test_result, self._on_test_state)

        self.cfg = state.to_config()  # for the "currently resolved" line
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        provider_tab = ttk.Frame(notebook, style="TFrame")
        recording_tab = ttk.Frame(notebook, style="TFrame")
        log_tab = ttk.Frame(notebook, style="TFrame")
        notebook.add(provider_tab, text="Provider & Keys")
        notebook.add(recording_tab, text="Recording")
        notebook.add(log_tab, text="Log")

        theme.apply(root)

        build_provider_tab(provider_tab, state, self)
        build_recording_tab(recording_tab, self)
        build_log_tab(log_tab, self)

        self.status.add_button("save_keys", "Save Keys", self._save_keys)
        self.status.add_button("save_config", "Save Config", self._save_config, primary=True)

        self.on_provider_change()

    # ---- state <-> tk bindings --------------------------------------------

    def _snapshot_state(self) -> FormState:
        s = FormState(
            provider=self.var_provider.get(),
            cloud_model=self.var_cloud_model.get(),
            ollama_host=self.var_ollama_host.get(),
            nvidia_server=self.var_nvidia_server.get(),
            nvidia_function_id=self.var_nvidia_function_id.get(),
            whisper_model=self.var_whisper_model.get(),
            whisper_language=self.var_whisper_language.get(),
            whisper_threads=int(self.var_whisper_threads.get() or 8),
            silence_duration=float(self.var_silence_duration.get() or 1.5),
            silence_threshold=int(self.var_silence_threshold.get() or 3),
            max_record_seconds=int(self.var_max_record_seconds.get() or 120),
            autopaste=self.var_autopaste.get(),
            keep_audio=self.var_keep_audio.get(),
            ptt_key=self.var_ptt_key.get(),
            notify_level=self.var_notify_level.get(),
        )
        for name, env_var, _needs in provider_key_var_names():
            row = self.rows.get(name)
            if row is not None and row.entry is not None:
                s.keys[env_var] = row.key_value()
        return s

    # ---- callbacks ------------------------------------------------------

    def on_key_change(self, name: str) -> None:
        self._refresh_row_dot(name)

    def _refresh_row_dot(self, name: str) -> None:
        row = self.rows.get(name)
        if row is None:
            return
        row.refresh_dot(
            self.var_provider.get(), testing=self.runner.testing_name, keys=self._current_keys()
        )

    def _current_keys(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for name, env_var, _needs in provider_key_var_names():
            row = self.rows.get(name)
            if row is not None and row.entry is not None:
                out[env_var] = row.key_value()
        return out

    def _apply_provider(self, *_a) -> None:
        """Selecting a provider takes effect at once — no Save Config needed.

        It is the one setting people change often (laptop on battery -> a
        cloud backend and back), and a dropdown that silently does nothing
        until you find the save button is a trap. The other fields keep the
        explicit save.
        """
        self.on_provider_change()
        provider = self.var_provider.get()
        try:
            Config.load().set_key("PROVIDER", provider)
        except OSError as exc:
            self.status.set(f"✗ couldn't switch provider: {exc}")
            return
        self._refresh_desktop_entry()
        self.status.set(f"✓ provider: {provider}")

    def _refresh_desktop_entry(self) -> None:
        """Keep the launcher's right-click menu in step with the keys we hold."""
        with contextlib.suppress(RuntimeError):
            write_desktop()

    def on_provider_change(self, *_a) -> None:
        active = self.var_provider.get()
        for name, row in self.rows.items():
            row.set_active(name == active)
            row.refresh_dot(active, testing=self.runner.testing_name, keys=self._current_keys())

        if active == "ollama":
            self.extra_ollama.grid()
            self.extra_nvidia.grid_remove()
        elif active == "nvidia":
            self.extra_nvidia.grid()
            self.extra_ollama.grid_remove()
        else:
            self.extra_ollama.grid_remove()
            self.extra_nvidia.grid_remove()

    def on_test(self, name: str, button: ttk.Button) -> None:
        self.runner.start(
            name, button, build_config=self._build_config, get_key_value=self._row_key
        )

    def _row_key(self, name: str) -> str:
        row = self.rows.get(name)
        return row.key_value() if row is not None and row.entry is not None else ""

    def _on_test_state(self, name: str, *, recording: bool) -> None:
        for n, row in self.rows.items():
            if n == name and recording:
                row.set_test_state(recording=True, enabled=True)
            else:
                row.set_test_state(recording=False, enabled=not self.runner.busy)

    def _on_test_result(self, msg: str, *, ok: bool) -> None:
        self.test_result.show(msg, ok=ok)
        # re-refresh dots (testing cleared)
        keys = self._current_keys()
        for _name, row in self.rows.items():
            row.refresh_dot(self.var_provider.get(), testing=None, keys=keys)

    # ---- build config ------------------------------------------------

    def _build_config(self):
        return self._snapshot_state().to_config()

    # ---- log ---------------------------------------------------------

    def refresh_log(self) -> None:
        self.log_view.refresh()

    # ---- save --------------------------------------------------------

    def _save_config(self) -> None:
        cfg = self._build_config()
        try:
            cfg.save()
            self.status.set(f"✓ saved to {cfg.config_file}")
        except OSError as exc:
            self.status.set(f"✗ couldn't save: {exc}")

    def _save_keys(self) -> None:
        values: dict[str, str] = {}
        for name, env_var, _needs in provider_key_var_names():
            row = self.rows.get(name)
            if row is not None and row.entry is not None:
                values[env_var] = row.key_value()
        try:
            write_env_file(values)
        except OSError as exc:
            self.status.set(f"✗ couldn't save keys: {exc}")
            return
        for k, v in values.items():
            if v:
                os.environ[k] = v
        # a provider becomes usable the moment its key exists, so it should
        # show up in the launcher menu without waiting for a reinstall
        self._refresh_desktop_entry()
        self.status.set(f"✓ keys saved to {env_file_path()} (chmod 600)")


def main() -> int:
    root = tk.Tk()
    WhispyGUI(root)
    # KDE/KWin Wayland apre le finestre Tkinter dietro la finestra attiva:
    # forziamo il foreground con lift + topmost brevemente, poi rilasciamo
    # così la finestra non rimane "always on top" ma parte visibile.
    try:
        root.lift()
        root.attributes("-topmost", True)
        root.after(400, lambda: root.attributes("-topmost", False))
    except tk.TclError:
        pass  # backend non supporta topmost (es. alcuni Wayland) —fallback al lift
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
