"""ydotool argument syntax: a sticky Ctrl leaves the desktop unusable."""

from __future__ import annotations

from whispy.paste import (
    KEY_LEFTCTRL,
    KEY_V,
    ydotool_ctrl_v_args,
    ydotool_release_modifiers_args,
)


def test_ctrl_v_args_are_explicit_press_release() -> None:
    args = ydotool_ctrl_v_args()
    assert args == [
        f"{KEY_LEFTCTRL}:1",
        f"{KEY_V}:1",
        f"{KEY_V}:0",
        f"{KEY_LEFTCTRL}:0",
    ]
    # sticky-Ctrl regression: NEVER emit "29+47"
    joined = " ".join(args)
    assert "+" not in joined
    assert args[0].endswith(":1")
    assert args[-1].endswith(":0")


def test_release_modifiers_all_keyup() -> None:
    args = ydotool_release_modifiers_args()
    assert args
    assert all(a.endswith(":0") for a in args)
    assert f"{KEY_LEFTCTRL}:0" in args


def test_ydotool_parser_trap_documented() -> None:
    """Documents the ydotool 1.x parser bug on '29+47'."""
    bad = "29+47"
    # strtol stops at '+'; last char '7' -> KEY DOWN with no UP
    # strtol simulation: read until the first non-digit
    n = 0
    for ch in bad:
        if ch.isdigit():
            n = n * 10 + int(ch)
        else:
            break
    assert n == KEY_LEFTCTRL
    assert bad[-1] != "0"  # -> ydotool emits PRESS
