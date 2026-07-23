"""LogView — read-only tail of ``/tmp/whispy.log`` in a mono Text widget."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from ..const import BORDER, MONO, SURFACE, TEXT

LOG_PATH = Path("/tmp/whispy.log")
TAIL_LINES = 200


class LogView:
    def __init__(self, parent: tk.Misc, path: Path | None = None) -> None:
        self._path = path or LOG_PATH
        self.text = tk.Text(
            parent,
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            font=(MONO, 10),
            relief="flat",
            wrap="none",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
        )

    def refresh(self) -> None:
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        if self._path.exists():
            try:
                lines = self._path.read_text(encoding="utf-8", errors="replace").splitlines()[
                    -TAIL_LINES:
                ]
                self.text.insert("1.0", "\n".join(lines) if lines else "(log file is empty)")
            except OSError as exc:
                self.text.insert("1.0", f"couldn't read the log: {exc}")
        else:
            self.text.insert("1.0", "no log yet — nothing has run through whispy on this machine")
        self.text.config(state="disabled")


def make_header(parent: tk.Misc, on_refresh: Callable[[], None]) -> tk.Frame:
    header = tk.Frame(parent, bg=SURFACE)
    from tkinter import ttk

    ttk.Label(header, text="/tmp/whispy.log — last 200 lines", style="TLabel").pack(side="left")
    ttk.Button(header, text="Refresh", style="Ghost.TButton", command=on_refresh).pack(side="right")
    return header
