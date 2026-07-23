"""ProviderRow — one row in the provider-keys tab (name + key + show/test)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ..const import ACCENT, BORDER, MONO, MUTED, SURFACE
from ..state import dot_color


class ProviderRow:
    """Owns the tk.Frame for one provider and exposes handles the app needs."""

    def __init__(
        self,
        parent: tk.Misc,
        name: str,
        env_var: str,
        needs_key: bool,
        key_value: str,
        index: int,
        on_key_change: Callable[[str], None],
        on_test: Callable[[str, ttk.Button], None],
    ) -> None:
        self.name = name
        self.env_var = env_var
        self.needs_key = needs_key

        if index > 0:
            tk.Frame(parent, bg=BORDER, height=1).grid(row=index, column=0, sticky="new")

        self.wf = tk.Frame(parent, bg=SURFACE)
        self.wf.grid(row=index, column=0, sticky="ew")
        self.wf.columnconfigure(3, weight=1)

        self.bar = tk.Frame(self.wf, bg=BORDER, width=4)
        self.bar.grid(row=0, column=0, rowspan=2, sticky="ns")
        self.bar.grid_propagate(False)

        self.dot_label = tk.Label(self.wf, text="●", bg=SURFACE, fg=MUTED, font=("", 11))
        self.dot_label.grid(row=0, column=1, padx=(10, 6), pady=(8, 0))

        self.name_label = ttk.Label(self.wf, text=name, style="Body.TLabel", width=13)
        self.name_label.grid(row=0, column=2, sticky="w", pady=(8, 0))

        if needs_key:
            self._key_var = tk.StringVar(value=key_value)
            self._key_var.trace_add("write", lambda *_a, n=name: on_key_change(n))
            self.entry = ttk.Entry(
                self.wf,
                textvariable=self._key_var,
                show="•",
                width=28,
                style="Dark.TEntry",
                font=(MONO, 10),
            )
            self.entry.grid(row=0, column=3, sticky="ew", padx=(6, 4), pady=(8, 0))

            self._eye_visible = tk.BooleanVar(value=False)

            def _toggle() -> None:
                visible = not self._eye_visible.get()
                self._eye_visible.set(visible)
                self.entry.config(show="" if visible else "•")
                self._eye_btn.config(text="hide" if visible else "show")

            self._eye_btn = ttk.Button(
                self.wf, text="show", width=5, style="Small.TButton", command=_toggle
            )
            self._eye_btn.grid(row=0, column=4, padx=(2, 0), pady=(8, 0))
        else:
            self.entry = None  # type: ignore[assignment]
            self._eye_btn = None  # type: ignore[assignment]
            ttk.Label(self.wf, text="(no key needed)", style="Muted.TLabel").grid(
                row=0, column=3, sticky="w", padx=(6, 4), pady=(8, 0)
            )

        self.test_btn = ttk.Button(self.wf, text="Test", style="Ghost.TButton")
        self.test_btn.grid(row=0, column=5, rowspan=2, padx=(4, 10))
        self.test_btn.config(command=lambda b=self.test_btn: on_test(name, b))

    def key_value(self) -> str:
        return self._key_var.get().strip() if self.entry is not None else ""

    def refresh_dot(
        self, provider: str, testing: str | None = None, keys: dict[str, str] | None = None
    ) -> None:
        keys = (
            keys
            if keys is not None
            else ({self.env_var: self.key_value()} if self.entry is not None else {})
        )
        self.dot_label.config(fg=dot_color(self.name, provider, keys, testing))

    def set_active(self, active: bool) -> None:
        self.bar.config(bg=ACCENT if active else BORDER)
        self.name_label.config(style="Accent.TLabel" if active else "Body.TLabel")

    def set_test_state(self, *, recording: bool, enabled: bool) -> None:
        self.test_btn.config(
            text="● stop" if recording else "Test",
            state="normal" if (enabled or recording) else "disabled",
        )
