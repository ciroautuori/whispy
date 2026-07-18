# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

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
- GitHub Actions CI — lint and tests on Python 3.11–3.13, plus a package build —
  with issue and pull request templates.
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
