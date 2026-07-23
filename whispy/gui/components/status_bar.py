"""StatusBar — bottom-row sticky status + action buttons."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ..const import BG


class StatusBar:
    def __init__(self, parent: tk.Misc) -> None:
        self.frame = tk.Frame(parent, bg=BG)
        self._var = tk.StringVar(value="")
        self.label = ttk.Label(self.frame, textvariable=self._var, style="BgMuted.TLabel")
        self.label.pack(side="left")
        self._buttons: dict[str, ttk.Button] = {}

    def add_button(
        self, key: str, text: str, command: Callable[[], None], *, primary: bool = False
    ) -> ttk.Button:
        btn = ttk.Button(
            self.frame,
            text=text,
            style="Accent.TButton" if primary else "Ghost.TButton",
            command=command,
        )
        btn.pack(side="right", padx=(8, 0) if self._buttons else 0)
        self._buttons[key] = btn
        return btn

    def set(self, msg: str) -> None:
        self._var.set(msg)

    def pack(self, **kw) -> None:  # noqa: A003
        self.frame.pack(**kw)
