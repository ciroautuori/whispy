"""Push-to-talk: hold = record, release = transcribe + paste.

KDE global shortcuts only report the press, never the release:
push-to-talk requires reading the keyboard directly via evdev.

Requires: python-evdev and membership in the ``input`` group.
"""

from __future__ import annotations

import contextlib
import selectors
import time
from pathlib import Path

from evdev import InputDevice, ecodes, list_devices

from .audio import start_recording, stop_recording
from .config import Config
from .toggle import _log, _notify, _transcribe_and_paste

# convenience aliases → real ecodes name
_ALIASES = {
    "META": "LEFTMETA",
    "SUPER": "LEFTMETA",
    "WIN": "LEFTMETA",
    "CTRL": "LEFTCTRL",
    "CONTROL": "LEFTCTRL",
    "ALT": "LEFTALT",
    "SHIFT": "LEFTSHIFT",
}

DEFAULT_COMBO = "META+F12"


def parse_combo(spec: str) -> set[int]:
    """'META+F12' → {KEY_LEFTMETA, KEY_F12}. Raises ValueError if unknown."""
    codes: set[int] = set()
    for part in (spec or DEFAULT_COMBO).upper().split("+"):
        name = part.strip()
        if not name:
            continue
        name = _ALIASES.get(name, name)
        code = getattr(ecodes, f"KEY_{name}", None)
        if code is None:
            raise ValueError(f"unknown key: {part!r}")
        codes.add(code)
    if not codes:
        raise ValueError("empty combo")
    return codes


def find_keyboards() -> list[InputDevice]:
    """Devices that can emit letters — i.e. real keyboards, not mice/touchpads.

    Excludes ydotool's virtual device: whispy uses it for auto-paste and
    reading it back here would mean reacting to its own synthetic keys.
    """
    found = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue
        keys = dev.capabilities().get(ecodes.EV_KEY, [])
        is_keyboard = ecodes.KEY_A in keys and ecodes.KEY_Z in keys
        if is_keyboard and "ydotool" not in dev.name.lower():
            found.append(dev)
        else:
            dev.close()
    return found


def run(cfg: Config | None = None) -> int:
    """Push-to-talk loop. Does not return until interrupted."""
    cfg = cfg or Config.load()
    _lock_paths_cleanup()  # a leftover toggle lock would block the next toggle press

    try:
        combo = parse_combo(getattr(cfg, "ptt_key", "") or DEFAULT_COMBO)
    except ValueError as exc:
        _log(f"ptt: {exc}")
        _notify(str(exc), "critical")
        return 1

    devices = find_keyboards()
    if not devices:
        msg = "no readable keyboard (the 'input' group is required)"
        _log(f"ptt: {msg}")
        _notify(msg, "critical")
        return 1

    sel = selectors.DefaultSelector()
    for dev in devices:
        sel.register(dev, selectors.EVENT_READ)

    names = ", ".join(d.name for d in devices)
    _log(f"ptt start combo={sorted(combo)} devices=[{names}]")

    held: set[int] = set()
    proc = None

    try:
        while True:
            for key, _mask in sel.select():
                dev = key.fileobj
                try:
                    events = list(dev.read())
                except OSError:
                    continue

                for event in events:
                    if event.type != ecodes.EV_KEY:
                        continue
                    # value: 0=release 1=press 2=autorepeat (ignore)
                    if event.value == 1:
                        held.add(event.code)
                    elif event.value == 0:
                        held.discard(event.code)
                    else:
                        continue

                    if event.code not in combo:
                        continue

                    if combo <= held and proc is None:
                        proc = _start(cfg)
                    elif proc is not None and not combo <= held:
                        proc = _stop_and_transcribe(cfg, proc)
    except KeyboardInterrupt:
        _log("ptt stop (interrupt)")
        if proc is not None:
            with contextlib.suppress(Exception):
                stop_recording(proc.pid)
        return 0
    finally:
        sel.close()
        for dev in devices:
            with contextlib.suppress(Exception):
                dev.close()


def _start(cfg: Config):
    """Start the recorder. Returns the Popen, or None if the mic does not start."""
    try:
        proc = start_recording(cfg)
    except RuntimeError as exc:
        _log(f"ptt: {exc}")
        _notify(str(exc), "critical")
        return None
    _log(f"ptt record start pid={proc.pid}")
    # the key is held down: you already know you are recording, a brief hint is enough
    _notify("● REC", timeout_ms=2000)
    return proc


def _stop_and_transcribe(cfg: Config, proc):
    """Stop the recorder and transcribe. Always returns None (state: stopped)."""
    _log(f"ptt stop pid={proc.pid} → transcribe")
    # it lasts ~2s and gets closed by the paste: no long timeouts
    _notify("⏳ Transcribing…", timeout_ms=6000)
    with contextlib.suppress(Exception):
        stop_recording(proc.pid)
    # arecord only updates the header on exit: give it a moment
    time.sleep(0.12)
    # Never suppress silently here: the PTT loop must survive a failed
    # transcription, but the user has to be told *why* nothing was pasted.
    try:
        _transcribe_and_paste(cfg)
    except Exception as exc:  # noqa: BLE001 — keep the loop alive, surface the cause
        msg = str(exc) or repr(exc)
        _log(f"ptt transcribe failed [{type(exc).__name__}]: {msg}")
        _notify(msg[:120], "critical", timeout_ms=6000)
    return None


def _lock_paths_cleanup() -> None:
    """PTT does not use the toggle locks: drop any left over from a mixed session."""
    for p in (Path("/tmp/whispy.lock"), Path("/tmp/whispy-autostop.pid")):
        with contextlib.suppress(OSError):
            p.unlink(missing_ok=True)
