"""Toast — a transient status message that fades after ``ttl_ms``.

tk.Tk has no toast primitive, but the rest of the UI already used an
inline ``ttk.Label`` as a status line: this just wraps it with an auto-clear.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..const import ACCENT2, DANGER, MUTED


class Toast:
    def __init__(self, parent: tk.Misc, text: str = "", ttl_ms: int = 3500) -> None:
        self._ttl = ttl_ms
        self._var = tk.StringVar(value=text)
        self._label = ttk.Label(parent, textvariable=self._var, style="BgMuted.TLabel")
        self._after_id: str | None = None

    @property
    def widget(self) -> ttk.Label:
        return self._label

    def pack(self, **kw) -> None:  # noqa: A003 — mirrors tk widget API
        self._label.pack(**kw)

    def _clear_after(self) -> None:
        self._after_id = None
        self._var.set("")

    def show(self, msg: str, *, ok: bool = True) -> None:
        self._var.set(msg)
        self._label.config(foreground=ACCENT2 if ok else DANGER)
        if self._after_id:
            self._label.after_cancel(self._after_id)
        if self._ttl > 0:
            self._after_id = self._label.after(self._ttl, self._clear_after)

    def set_sticky(self, msg: str, *, ok: bool = True) -> None:
        """Permanent status (no auto-clear) — used for the persistent bottom status."""
        if self._after_id:
            self._label.after_cancel(self._after_id)
            self._after_id = None
        # Use MUTED visually since sticky messages are not callouts.
        self._label.config(foreground=MUTED)
        self._var.set(msg)
