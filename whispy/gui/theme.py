"""ttk style registry — installed once via :func:`apply`.

All visual styling leans on one ttk :class:`Style` with named styles keyed off
the constants in :mod:`whispy.gui.const`. Keeping every style map here (instead
of scattered across the widgets) is what lets a future dark/light theme swap
happen as a single :func:`apply` call with different tokens.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import const

CLAM = "clam"  # the only built-in theme that lets every color be overridden


def apply(root: tk.Tk) -> ttk.Style:
    """Install the dark Whispy theme onto ``root`` and return the :class:`Style`."""
    style = ttk.Style(root)
    style.theme_use(CLAM)
    root.configure(bg=const.BG)

    style.configure(
        ".",
        background=const.BG,
        foreground=const.TEXT,
        bordercolor=const.BORDER,
        focuscolor=const.ACCENT,
    )
    style.configure("TFrame", background=const.BG)
    style.configure("Surface.TFrame", background=const.SURFACE)
    style.configure("Sink.TFrame", background=const.SURFACE2)

    style.configure("TLabel", background=const.BG, foreground=const.TEXT)
    style.configure("Body.TLabel", background=const.SURFACE, foreground=const.TEXT)
    style.configure("Muted.TLabel", background=const.SURFACE, foreground=const.MUTED)
    style.configure("BgMuted.TLabel", background=const.BG, foreground=const.MUTED)
    style.configure(
        "Accent.TLabel", background=const.SURFACE, foreground=const.ACCENT, font=("", 10, "bold")
    )
    style.configure(
        "Danger.TLabel", background=const.SURFACE, foreground=const.DANGER, font=("", 10, "bold")
    )

    style.configure("TNotebook", background=const.BG, bordercolor=const.BORDER)
    style.configure("TNotebook.Tab", background=const.BG, foreground=const.MUTED, padding=(14, 8))
    style.map(
        "TNotebook.Tab",
        background=[("selected", const.SURFACE)],
        foreground=[("selected", const.TEXT)],
    )

    style.configure(
        "Dark.TEntry",
        fieldbackground=const.SURFACE,
        foreground=const.TEXT,
        insertcolor=const.TEXT,
        padding=6,
    )
    style.configure(
        "Dark.TSpinbox",
        fieldbackground=const.SURFACE,
        foreground=const.TEXT,
        arrowcolor=const.TEXT,
        padding=4,
    )
    style.configure(
        "Dark.TCombobox",
        fieldbackground=const.SURFACE,
        foreground=const.TEXT,
        arrowcolor=const.TEXT,
        padding=4,
    )
    style.map(
        "Dark.TCombobox",
        fieldbackground=[("readonly", const.SURFACE)],
        foreground=[("readonly", const.TEXT)],
    )

    style.configure("Dark.TCheckbutton", background=const.BG, foreground=const.TEXT)
    style.map("Dark.TCheckbutton", background=[("active", const.BG)])

    style.configure(
        "Accent.TButton",
        background=const.ACCENT,
        foreground=const.BG,
        padding=(14, 8),
        font=("", 10, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#eab471"), ("disabled", const.BORDER)],
        foreground=[("disabled", const.MUTED)],
    )

    style.configure(
        "Ghost.TButton", background=const.SURFACE, foreground=const.TEXT, padding=(10, 6)
    )
    style.map(
        "Ghost.TButton",
        background=[("active", const.BORDER), ("disabled", const.SURFACE)],
        foreground=[("disabled", const.MUTED)],
    )

    style.configure(
        "Small.TButton", background=const.SURFACE, foreground=const.MUTED, padding=(6, 3)
    )
    style.map("Small.TButton", background=[("active", const.BORDER), ("disabled", const.SURFACE)])

    return style
