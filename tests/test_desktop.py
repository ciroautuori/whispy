"""The launcher entry and its right-click menu.

``render`` is pure, so the whole menu is asserted here without a display, a
desktop environment, or a filesystem.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from whispy.desktop import ACTIVE_MARK, ready_providers, render, write
from whispy.providers import PROVIDER_INFO

EXECS = {
    "gui_exec": "/usr/bin/whispy-gui",
    "dictate_exec": "/usr/bin/whispy-hotkey",
    "cli_exec": "/usr/bin/whispy",
}


def _actions(text: str) -> list[str]:
    for line in text.splitlines():
        if line.startswith("Actions="):
            return [a for a in line.removeprefix("Actions=").split(";") if a]
    raise AssertionError("no Actions= line")


# ---- what the entry does when you click it ---------------------------------


def test_clicking_the_icon_opens_the_control_panel() -> None:
    # the bug this feature exists for: Exec used to be the dictation wrapper,
    # so clicking the launcher icon started a recording and showed nothing
    text = render("local", ["local"], **EXECS)
    assert "Exec=/usr/bin/whispy-gui" in text.splitlines()


def test_dictation_is_still_one_right_click_away() -> None:
    text = render("local", ["local"], **EXECS)
    assert "[Desktop Action dictate]" in text
    assert "Exec=/usr/bin/whispy-hotkey" in text


# ---- which providers the menu offers ---------------------------------------


def test_only_ready_providers_are_listed() -> None:
    text = render("local", ["local", "groq"], **EXECS)
    assert _actions(text) == ["dictate", "provider-local", "provider-groq"]
    assert "provider-openai" not in text


def test_each_entry_switches_to_its_provider() -> None:
    text = render("local", ["groq"], **EXECS)
    assert "Exec=/usr/bin/whispy use groq" in text


def test_underscored_names_keep_working() -> None:
    # action ids may only contain A-Za-z0-9- , but the command wants the real name
    text = render("local", ["faster_whisper"], **EXECS)
    assert "provider-faster-whisper" in _actions(text)
    assert "Exec=/usr/bin/whispy use faster_whisper" in text


def test_unknown_names_are_ignored() -> None:
    text = render("local", ["local", "nope"], **EXECS)
    assert _actions(text) == ["dictate", "provider-local"]


# ---- the active marker -----------------------------------------------------


def test_active_provider_is_marked_and_others_are_not() -> None:
    text = render("groq", ["local", "groq"], **EXECS)
    assert f"Name={ACTIVE_MARK} Groq" in text
    assert "Name=Local" in text


def test_active_marker_accepts_a_dashed_name() -> None:
    assert f"Name={ACTIVE_MARK} Faster-Whisper" in render(
        "faster-whisper", ["faster_whisper"], **EXECS
    )


# ---- readiness -------------------------------------------------------------


def test_keyless_providers_are_always_ready() -> None:
    ready = ready_providers(keys={})
    assert "local" in ready and "faster_whisper" in ready
    assert "groq" not in ready and "openai" not in ready


def test_a_saved_key_makes_its_provider_ready() -> None:
    assert "groq" in ready_providers(keys={"GROQ_API_KEY": "gsk_x"})


def test_a_blank_key_does_not_count() -> None:
    assert "groq" not in ready_providers(keys={"GROQ_API_KEY": "   "})


def test_ready_providers_keeps_registry_order() -> None:
    ready = ready_providers(keys=dict.fromkeys(_all_key_vars(), "x"))
    assert ready == list(PROVIDER_INFO)


def _all_key_vars() -> list[str]:
    return [str(i["env_var"]) for i in PROVIDER_INFO.values() if i["env_var"]]


# ---- file format -----------------------------------------------------------


def test_paths_with_spaces_are_quoted() -> None:
    text = render("local", ["local"], gui_exec="/opt/my apps/whispy-gui")
    assert 'Exec="/opt/my apps/whispy-gui"' in text


def test_exactly_one_main_category() -> None:
    # two main categories make the launcher list Whispy twice
    line = next(x for x in render("local", ["local"], **EXECS).splitlines() if x.startswith("Cat"))
    assert line == "Categories=Utility;"


def test_write_produces_a_file_the_spec_accepts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    target = write(tmp_path / "whispy.desktop", refresh=False)
    assert target.exists()

    validator = shutil.which("desktop-file-validate")
    if validator is None:
        pytest.skip("desktop-file-validate not installed")
    result = subprocess.run([validator, str(target)], capture_output=True, text=True)
    # hints are advisory; errors and warnings are not
    assert result.returncode == 0, result.stdout + result.stderr
    assert "error" not in (result.stdout + result.stderr).lower()


def test_write_reports_an_unwritable_target(tmp_path: Path) -> None:
    blocked = tmp_path / "file"
    blocked.write_text("not a directory")
    with pytest.raises(RuntimeError, match="cannot write"):
        write(blocked / "whispy.desktop", refresh=False)
