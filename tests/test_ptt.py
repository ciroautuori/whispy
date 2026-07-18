"""Push-to-talk: combo parsing and device selection."""

from __future__ import annotations

import pytest

evdev = pytest.importorskip("evdev", reason="python-evdev not installed")

from evdev import ecodes  # noqa: E402

from whispy import ptt  # noqa: E402


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("META+F12", {ecodes.KEY_LEFTMETA, ecodes.KEY_F12}),
        ("super+f12", {ecodes.KEY_LEFTMETA, ecodes.KEY_F12}),  # case-insensitive
        ("MENU", {ecodes.KEY_MENU}),
        ("RIGHTCTRL", {ecodes.KEY_RIGHTCTRL}),
        ("CTRL+ALT+K", {ecodes.KEY_LEFTCTRL, ecodes.KEY_LEFTALT, ecodes.KEY_K}),
    ],
)
def test_parse_combo(spec, expected):
    assert ptt.parse_combo(spec) == expected


def test_empty_combo_uses_default():
    assert ptt.parse_combo("") == ptt.parse_combo(ptt.DEFAULT_COMBO)


@pytest.mark.parametrize("spec", ["PIPPO", "META+NONESISTE", "+"])
def test_unknown_key_is_explicit(spec):
    """A clear error at startup beats a key that silently never responds."""
    with pytest.raises(ValueError):
        ptt.parse_combo(spec)


class _FakeDev:
    def __init__(self, name, keys):
        self.name = name
        self._keys = keys
        self.closed = False

    def capabilities(self):
        return {ecodes.EV_KEY: self._keys}

    def close(self):
        self.closed = True


_LETTERS = [ecodes.KEY_A, ecodes.KEY_Z]


def test_find_keyboards_skips_ydotool_and_non_keyboards(monkeypatch):
    """ydotool is our own auto-paste device: reading it back would loop forever."""
    devs = {
        "/dev/input/event0": _FakeDev("ydotoold virtual device", _LETTERS),
        "/dev/input/event1": _FakeDev("Real Keyboard", _LETTERS),
        "/dev/input/event2": _FakeDev("Mouse", [ecodes.KEY_A]),  # no Z
    }
    monkeypatch.setattr(ptt, "list_devices", lambda: list(devs))
    monkeypatch.setattr(ptt, "InputDevice", lambda path: devs[path])

    found = ptt.find_keyboards()

    assert [d.name for d in found] == ["Real Keyboard"]
    assert devs["/dev/input/event0"].closed  # rejected devices must be closed
    assert devs["/dev/input/event2"].closed


def test_find_keyboards_ignores_unreadable_devices(monkeypatch):
    """One device without permissions must not fail the whole scan."""

    def _open(path):
        if path == "/dev/input/event0":
            raise OSError("permission denied")
        return _FakeDev("Real Keyboard", _LETTERS)

    monkeypatch.setattr(ptt, "list_devices", lambda: ["/dev/input/event0", "/dev/input/event1"])
    monkeypatch.setattr(ptt, "InputDevice", _open)

    assert [d.name for d in ptt.find_keyboards()] == ["Real Keyboard"]
