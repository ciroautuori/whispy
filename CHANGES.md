# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [0.5.0] - 2026-07-28

### Added

- **The launcher entry is an application again.** `install.sh` wrote a
  `whispy.desktop` whose `Exec` was the dictation wrapper, so clicking "Whispy
  Dictate" started a recording: nothing opened, nothing was visible, and it
  stopped on its own eight seconds later. Clicking the icon now opens the
  control panel.
- **Switch provider from the launcher.** Right-clicking the icon offers
  "Dictate now" plus one entry per provider, with the active one marked. Only
  providers that can run right now are listed — one that needs an API key you
  have not set is not offered until the key exists, so the menu grows as you
  add keys and never presents an option that fails.
- `whispy use <provider>` — switch backend in one command.
- `whispy desktop` — rewrite the launcher entry on demand.
- `Config.set_key()` — edits a single line of whispy.conf. `save()` rewrites
  the whole file from the dataclass and would delete every comment you wrote,
  which is too high a price for changing one setting.

### Changed

- The provider dropdown in the control panel applies immediately. It used to
  need *Save Config*, so picking a provider and closing the window did nothing
  at all. The other fields keep the explicit save.
- Saving keys regenerates the launcher menu, so a cloud provider appears there
  as soon as its key is stored.
- `install.sh` generates the desktop entry through `whispy desktop` instead of
  writing it inline — the menu depends on which keys exist, so it cannot be
  frozen at install time.
- `Categories` is `Utility;` alone. It was `Utility;AudioVideo;`, two main
  categories, which makes launchers list the application twice.
- `PROVIDER_INFO` gained a `label` per provider, so display names live in the
  registry instead of a parallel map.

## [0.4.2] - 2026-07-28

### Changed

- **Transcripts keep their punctuation and their capitalization.**
  `clean_transcript` stripped trailing `.,;:!?` and forced the first letter
  upper, so dictating "ciao, come stai?" pasted "Ciao, come stai" and you
  retyped the question mark. Whisper punctuates and capitalizes well; the
  cleanup now removes model artifacts and normalizes whitespace, and nothing
  else. Forcing upper was also wrong every time you dictate into the middle of
  a sentence.
- `(...)` is no longer deleted wholesale. It was there to drop non-speech notes
  like "(musica)", but it ate real speech with it — "ho parlato con Marco (il
  collega) ieri" lost the aside. Bracketed `[...]` and starred `*...*`
  annotations are still removed, and a transcript that is *only* noise is still
  dropped.
- The cleanup runs **once**, in `whispy.transcribe.transcribe`. It used to run
  twice for the local provider — once inside it, once in the dispatcher. The
  second pass was redundant rather than harmful, but it meant the local
  provider carried its own copy of the cleanup rules; now every provider
  returns its backend's raw text and there is one place to reason about.

Ported from work on `fix/multi-provider` that never reached main
(`c56c386`, 20 Jul).

## [0.4.1] - 2026-07-28

### Fixed
- **Transcription was completely broken.** The provider registry imported
  `transcribe` from modules that had been refactored into classes, and from two
  module names that did not exist (`providers/openai.py`, `providers/groq.py`
  were named `*_provider.py`). `local` — the default provider — raised
  `ImportError: cannot import name 'transcribe' from 'whispy.providers.local'`
  on every single dictation. `openai` and `groq` raised `ModuleNotFoundError`.
  Five of the nine backends now resolve where three did not.
- **The failure was invisible.** `toggle.py` and the GUI test runner caught only
  `RuntimeError`, and `ptt.py` wrapped transcription in a bare
  `contextlib.suppress(Exception)`, so recording succeeded, no text appeared,
  and nothing was written to the log or shown as a notification. All three now
  report the cause.
- A crash inside the GUI's live-test thread left `testing_name` set forever,
  disabling every Test button with no message on screen. The worker now always
  emits exactly one result.
- `MAX_RECORD_SECONDS` above 30 was silently rewritten to 8, so the control
  panel's 3–300s setting appeared to do nothing. The configured value is used.
- `whispy version` printed `0.2.0` while the package shipped as `0.4.0`; a test
  now pins `__version__` to the `pyproject.toml` version.
- The provider-row separator was gridded onto the same row as the row body and
  was never visible.
- `whispy.gui.state` is documented as Tk-free so the ViewModel can be tested on
  a headless machine, but `whispy/gui/__init__.py` imported the View eagerly —
  so importing it pulled in tkinter and died with `libtk8.6.so: cannot open
  shared object file` anywhere Tk isn't installed. `WhispyGUI` and `main` now
  resolve lazily (PEP 562), and `gui/test_runner.py` imports `ttk` under
  `TYPE_CHECKING` since it only ever used it as an annotation.
- `whispy gui` without Tk prints the package to install (Arch, Debian, Fedora)
  instead of a traceback.
- The record/stop integration test skips where no recorder (arecord, rec, sox)
  exists rather than failing — it is the one test that touches real hardware.

### Added
- `whispy providers` — the backend/key table the code already documented but
  the CLI never exposed.
- `faster_whisper` is registered as a real provider (the module existed but no
  name mapped to it).
- `tests/test_providers.py` and `tests/test_error_surfacing.py`: every entry in
  the registry is resolved and its signature checked, and the swallowed-error
  paths are covered. The previous suite mocked `whispy.toggle.transcribe`
  everywhere and never called `get_provider`, which is why 56 green tests
  coexisted with a product that could not transcribe at all.

### Changed
- One provider contract instead of two: every backend is a module-level
  `transcribe(cfg, wav_path) -> str`. The unused `TranscribeProvider` ABC and
  the four class-based implementations that nothing instantiated are gone.
- `get_provider` resolves through the module name recorded in `PROVIDER_INFO`,
  so a file rename cannot silently desync the registry again, and it raises
  `RuntimeError` rather than letting `ImportError` escape to callers.
- OpenAI and Groq go through the existing stdlib HTTP path instead of their
  SDKs, and read their key from `OPENAI_API_KEY` / `GROQ_API_KEY` like every
  other cloud provider (the class versions read a `cfg.api_key` field that does
  not exist on `Config`, so they could never have authenticated). The now-unused
  `whispy[openai]` and `whispy[groq]` extras were removed.
- Provider names are dash- and case-insensitive (`faster-whisper` works).
- CI installs into a throwaway virtualenv instead of the runner's host Python,
  runs `ruff format --check` (which only `scripts/check.sh` did), declares
  `permissions: contents: read`, and cancels superseded runs per branch.
  `scripts/check.sh` lints `.` like CI does, not just `whispy/` and `tests/`.

## [0.3.0] - 2026-07-18

### Added
- **Push-to-talk** (`whispy ptt`): hold to record, release to transcribe. Global
  shortcuts in KDE and GNOME report only the key press and never the release, so
  the key is read directly through `evdev`. Requires the `input` group.
- `whispy-ptt.service` user unit, so push-to-talk survives reboots.
- `PTT_KEY` (default `META+F12`): single key or combo, with `META`/`SUPER`/`CTRL`
  aliases.
- `NOTIFY_LEVEL`: `normal` | `quiet` (errors only) | `off`.
- **Automatic CPU fallback**: when a GPU build cannot allocate its buffers —
  typically because another process (a model server, a game) is holding VRAM —
  transcription retries on CPU instead of surfacing a raw GGML assertion.
- `scripts/check.sh` — lint, format check, and tests in one command, plus issue
  and pull request templates.
- 33 new tests covering notifications, combo parsing, device selection, and the
  GPU-to-CPU fallback.

### Changed
- **Notifications rewritten**: a single bubble that updates itself through
  `--replace-id` instead of a stack that piles up, marked `--transient` so it
  never pollutes notification history. Timeouts cut from 30s to 2s for the
  recording cue and from 20s to 6s for transcription.
- On successful auto-paste the notification is now **closed** instead of
  repeating text already on screen. Errors still stay visible.
- Documentation is now in English throughout.

### Fixed
- The `ydotoold` virtual device was detected as a keyboard, so auto-paste could
  re-trigger recording through its own synthetic keystrokes. It is now excluded.

## [0.2.1] - 2026-07-17

### Fixed
- **KDE hotkey did nothing**: `CommandURL=whispy` had no absolute path, and KDE
  runs with `PATH=/usr/bin:/bin` — command not found. Fixed with a wrapper and an
  absolute path.
- **Keyboard lockup**: `ydotool key 29+47` left Ctrl stuck down (ydotool 1.x
  parser).
- **No transcription**: `rec` with silence detection wrote 0 bytes; `arecord -D
  pulse` is now preferred.
- **Corrupted WAVs** after stop: `arecord`'s `0x80000000` placeholder header is
  repaired before whisper reads it.
- Toggle no longer uses `fork`: `Popen(start_new_session=True)` plus `killpg` is
  reliable.

### Added
- pytest suite (23 tests): WAV headers, paste/ydotool, config, CLI, mocked
  toggle, microphone integration.
- `/tmp/whispy.log` logging plus notifications on start, stop, and errors.
- `install.sh` updates `khotkeysrc` and writes a `.desktop` file with an absolute
  path.

## [0.2.0] - 2026-07-17

### Removed
- Second Brain (web UI, FastAPI, store)
- Tray icon, KDE D-Bus hotkey, duplicate `bin/whispy`
- whisper-server backend and extra subcommands

### Changed
- Dictation only: a single `whispy` command toggles record → transcribe → paste

## [0.1.0] - 2025-07-16

### Added
- Initial release (dictation plus Second Brain, later removed in 0.2)
