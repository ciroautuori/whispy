"""Registry contract tests.

These exist because of a real outage: ``providers/__init__.py`` imported
``transcribe`` from modules that had been refactored into classes (and from
two module names that didn't exist), so *every* transcription raised
ImportError while the whole suite stayed green — nothing ever called
:func:`get_provider`. Anything that dispatches by name gets tested here.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

from whispy.config import Config
from whispy.providers import (
    PROVIDER_INFO,
    PROVIDER_NAMES,
    describe_providers,
    get_provider,
    normalize,
)


@pytest.mark.parametrize("name", PROVIDER_NAMES)
def test_every_provider_resolves_to_a_callable(name: str) -> None:
    """The exact check whose absence let the outage ship."""
    func = get_provider(name)
    assert callable(func)


@pytest.mark.parametrize("name", PROVIDER_NAMES)
def test_every_provider_takes_cfg_and_path(name: str) -> None:
    params = list(inspect.signature(get_provider(name)).parameters)
    assert len(params) == 2, f"{name}: expected transcribe(cfg, wav_path), got {params}"


@pytest.mark.parametrize("name", PROVIDER_NAMES)
def test_declared_module_exists_and_exports_transcribe(name: str) -> None:
    module_name = str(PROVIDER_INFO[name]["module"])
    module = importlib.import_module(f"whispy.providers.{module_name}")
    assert callable(getattr(module, "transcribe", None))


@pytest.mark.parametrize("name", PROVIDER_NAMES)
def test_info_entry_is_complete(name: str) -> None:
    info = PROVIDER_INFO[name]
    assert set(info) == {"module", "env_var", "default_model", "needs_key"}
    assert isinstance(info["needs_key"], bool)
    # a provider that needs a key must name the env var it reads it from
    assert bool(info["env_var"]) == info["needs_key"]


def test_unknown_provider_raises_runtime_error() -> None:
    # RuntimeError specifically: callers catch that to show the user a message.
    with pytest.raises(RuntimeError, match="unknown provider"):
        get_provider("nope")


def test_normalize_accepts_dashes_and_case() -> None:
    assert normalize("Faster-Whisper") == "faster_whisper"
    assert normalize("  LOCAL ") == "local"
    assert normalize("") == "local"


def test_blank_provider_defaults_to_local() -> None:
    assert get_provider("").__module__ == "whispy.providers.local"


def test_describe_providers_lists_them_all() -> None:
    table = describe_providers()
    for name in PROVIDER_NAMES:
        assert name in table


def test_transcribe_dispatches_through_the_registry(tmp_path: Path, monkeypatch) -> None:
    from whispy import transcribe as transcribe_mod

    seen: dict[str, object] = {}

    def fake(cfg: Config, wav_path: Path) -> str:
        seen["provider"] = cfg.provider
        return "  ciao mondo  "

    monkeypatch.setattr(transcribe_mod, "get_provider", lambda name: fake)
    cfg = Config(provider="groq")
    assert transcribe_mod.transcribe(cfg, tmp_path / "a.wav") == "Ciao mondo"
    assert seen["provider"] == "groq"


def test_transcribe_propagates_unknown_provider_as_runtime_error(tmp_path: Path) -> None:
    from whispy.transcribe import transcribe

    with pytest.raises(RuntimeError):
        transcribe(Config(provider="does-not-exist"), tmp_path / "a.wav")
