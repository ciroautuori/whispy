"""Whispy control panel — desktop app to manage provider, keys, and settings.

Tkinter + ttk (stdlib, no new dependency). Run via ``whispy gui`` or
``python -m whispy.gui``.

Architecture (was: one 740-line monolith, is: thin layers):

- ``state.py``  — pure ViewModel (no Tk): editable fields + dot coloring + Config round-trip
- ``theme.py``  — every ttk style map, one :func:`apply` call
- ``const.py``  — design tokens (colors, spacing, fonts)
- ``components/`` — reusable widgets (Toast, LogView, ProviderRow, StatusBar)
- ``test_runner.py`` — live mic-test worker, in a thread, no Tk coupling
- ``tabs.py``  — Notebook tab layout, bound to self's tk Variables
- ``app.py``   — the View: wires ``tk.Variable`` <-> field and hosts callbacks

``WhispyGUI`` and ``main`` are resolved lazily (PEP 562). Importing them
eagerly here would pull in ``tkinter`` for anything that merely touches
``whispy.gui.state`` — which is deliberately Tk-free so it can be unit
tested on a headless machine. That eager import broke CI on a server with
no Tk installed, which is exactly the case ``state.py`` exists to support.

Needs the ``python3-tk`` system package on Debian/Ubuntu, ``tk`` on Arch
(Arch's own ``python`` package does not pull it in). Keys entered in a row
are applied to ``os.environ`` this process when you click that row's Test;
Save Keys is what makes them durable across restarts (writes ``whispy.env``,
chmod 600 — see envfile.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # for type checkers only — never executed at runtime
    from .app import WhispyGUI, main

__all__ = ["WhispyGUI", "main"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import app

        return getattr(app, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
