# Contributing

Whispy stays small: **speech → text at the cursor**.

Before adding code, one question decides it: *does this serve getting a voice to the cursor?* If not, it doesn't go in — and that's fine.

---

## Setup

```bash
git clone https://github.com/ciroautuori/whispy.git
cd whispy
pip install -e '.[dev,ptt]'
```

On Arch, prefer the system package for push-to-talk:

```bash
sudo pacman -S python-evdev
sudo usermod -aG input $USER    # log out and back in
```

---

## Before opening a PR

```bash
./scripts/check.sh      # lint + format + tests, the same checks a reviewer applies
```

Then **actually use it** — dictate a real sentence. The tests never touch a microphone or a keyboard, so they cannot tell you whether the experience is good.

```bash
whispy ptt                 # foreground, so you see logs while you speak
tail -f /tmp/whispy.log
```

---

## How the tests work

They run anywhere, with no hardware: no microphone, no keyboard, no GPU. `subprocess` calls and `evdev` devices are stubbed. If a change can only be tested with real hardware, that usually means the logic needs separating from the I/O.

| File | Covers |
|------|--------|
| `test_audio_header.py` | Repairing `arecord` WAV headers after a kill |
| `test_paste.py` | `ydotool` arguments — the 1.x parser has traps |
| `test_notify.py` | Notification replacement, levels, closing |
| `test_ptt.py` | Key combo parsing, device selection |
| `test_toggle.py` | Toggle state machine |
| `test_integration_record.py` | Record → stop → transcribe, with whisper mocked |
| `test_config.py` | Config parsing and model resolution |
| `test_transcribe.py` | Transcript cleanup, hallucination filtering |
| `test_providers.py` | Every backend in the registry resolves and has the right signature |
| `test_error_surfacing.py` | Failures reach the log, the notification, and the GUI |
| `test_gui_state.py` | The Tk-free ViewModel behind the control panel |
| `test_cli.py` | Every argv shape, and version consistency |

### A rule paid for in production

`v0.4.0` shipped with **every** transcription raising `ImportError`, and the
suite was green: each test mocked `whispy.toggle.transcribe`, so nothing ever
called `get_provider()`. Mocking the seam under test proves only that the mock
works.

So: if you add a name that something looks up at runtime — a provider, a config
key, a CLI subcommand — add the test that *resolves* it. `test_providers.py` is
the shape to copy.

---

## Style

- **English everywhere** — code, comments, commit messages, user-facing strings
- Comments explain **why**, not what — especially the `ydotool`, `arecord`, and KDE quirks, which look arbitrary but aren't
- Module docstrings: one line stating what the module does
- No mandatory runtime dependencies; `evdev` is an optional extra
- `ruff` settles formatting, not opinions

---

## Reporting a bug

Logs make a bug fixable:

```bash
tail -50 /tmp/whispy.log
journalctl --user -u whispy-ptt -n 50    # push-to-talk
```

Include your distro, desktop environment, Wayland or X11, whisper build, and model.
