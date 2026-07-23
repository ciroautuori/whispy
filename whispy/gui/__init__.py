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
- ``app.py``   — the View: wires ``tk.Variable`` <-> state and hosts callbacks

Needs the ``python3-tk`` system package on Debian/Ubuntu (Arch ships it in
the base python package). Keys entered in a row are applied to ``os.environ``
this process when you click that row's Test; Save Keys is what makes them
durable across restarts (writes ``whispy.env``, chmod 600 — see envfile.py).
"""

from __future__ import annotations

from .app import WhispyGUI, main

__all__ = ["WhispyGUI", "main"]
