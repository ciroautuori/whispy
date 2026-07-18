# Whispy

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)
![Ruff](https://img.shields.io/badge/Ruff-passed-261230?logo=ruff&logoColor=white)
![Wayland](https://img.shields.io/badge/Wayland-ready-brightgreen)
![Stars](https://img.shields.io/github/stars/ciroautuori/whispy?style=social)
![Last Commit](https://img.shields.io/github/last-commit/ciroautuori/whispy)
![Version](https://img.shields.io/badge/version-0.3.0-green)

**Hold a key. Speak. Release. The text lands at your cursor.**

Local voice dictation for Linux — offline, no account, no subscription.

```
  ┌─ hold Meta+F12 ───────────────────────────────────┐
  │                                                   │
  │   🎙  "remind me to buy bread tomorrow"           │
  │                                                   │
  └─ release ─────────────────────────────────────────┘
                       ↓  ~1.5s
  remind me to buy bread tomorrow▮
```

Whisper runs **on your machine** — on CUDA if you have it. Nothing leaves your computer: no cloud, no telemetry, no account.

Built on [whisper.cpp](https://github.com/ggerganov/whisper.cpp), for KDE, GNOME, Hyprland, and any Wayland or X11 desktop.

---

## Quick Start

### Arch Linux

```bash
sudo pacman -S alsa-utils wl-clipboard ydotool libnotify python-evdev
yay -S whisper.cpp-cuda          # or whisper.cpp for CPU-only

git clone https://github.com/ciroautuori/whispy.git
cd whispy
./install.sh
```

### Debian / Ubuntu / Fedora

```bash
# Debian/Ubuntu — Fedora: swap apt for dnf
sudo apt install alsa-utils wl-clipboard ydotool libnotify-bin python3-evdev

git clone https://github.com/ciroautuori/whispy.git
cd whispy
./install.sh
```

`whisper-cli` is not packaged on most distros — build it from [whisper.cpp](https://github.com/ggerganov/whisper.cpp) and make sure it lands on your `PATH`.

### Get a model

```bash
mkdir -p ~/.local/share/whispy/models
cd ~/.local/share/whispy/models

# small and fast (~150 MB)
curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin

# recommended if you have a GPU (~1.6 GB, far more accurate)
curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

Whispy picks the model on its own: it prefers `large-v3-turbo` and falls back to `base`.

### Enable push-to-talk

Reading the keyboard requires the `input` group — log out and back in after this:

```bash
sudo usermod -aG input $USER
systemctl --user enable --now whispy-ptt
```

Hold `Meta+F12`, speak, release. That's the whole thing.

---

## How It Works

```
┌──────────────────────────────────────────────────────────────┐
│                          Whispy                              │
│                                                              │
│  ┌────────────────────────────────────────────────────┐      │
│  │              Key listener (evdev)                  │      │
│  │                                                    │      │
│  │   key down ──► start arecord ──► /dev/shm (RAM)    │      │
│  │   key up   ──► stop, then transcribe               │      │
│  └────────────────────────────────────────────────────┘      │
│                          │                                   │
│  ┌────────────────────────────────────────────────────┐      │
│  │              whisper.cpp (local)                   │      │
│  │                                                    │      │
│  │   16 kHz mono WAV → whisper-cli → text             │      │
│  │   CUDA when available, CPU otherwise               │      │
│  │   hallucination filter drops silence artifacts     │      │
│  └────────────────────────────────────────────────────┘      │
│                          │                                   │
│  ┌────────────────────────────────────────────────────┐      │
│  │              Injection                             │      │
│  │                                                    │      │
│  │   wl-copy → clipboard → ydotool Ctrl+V → cursor    │      │
│  │   clipboard always set, so Ctrl+V works regardless │      │
│  └────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

Audio lives in `/dev/shm` (RAM), is deleted right after transcription, and never touches the disk or the network.

---

## Why?

Linux desktop dictation either doesn't exist or ships your voice to someone else's server. Whispy does one thing: it takes what you say and puts it where your cursor is.

- **Fully local** — whisper.cpp on your hardware, zero network calls
- **Fast** — ~1.5s for a sentence with `large-v3-turbo` on GPU
- **True push-to-talk** — hold to record, release to transcribe, like a radio
- **Quiet** — one notification that updates itself, then disappears
- **Small** — ~700 lines of Python, no mandatory runtime dependencies
- **Wayland-first** — works where `xdotool` cannot reach

### Why push-to-talk needs evdev

Global shortcuts in KDE and GNOME report only the **key press**, never the release. Push-to-talk is therefore impossible through a normal desktop hotkey. Whispy reads the keyboard directly through `evdev`, which reports both edges — that's the only reason the `input` group is needed.

---

## Modes

| Mode | Command | How it stops | Needs |
|------|---------|--------------|-------|
| **Push-to-talk** | `whispy ptt` | when you release the key | `evdev` + `input` group |
| **Toggle** | `whispy` | second press, or `MAX_RECORD_SECONDS` | nothing extra |

### Push-to-talk (recommended)

```bash
systemctl --user enable --now whispy-ptt    # survives reboots
journalctl --user -u whispy-ptt -f          # watch it work
```

The daemon idles at zero cost while you're not speaking.

### Toggle

Press once to start, press again to transcribe. If you forget the second press, it stops on its own after `MAX_RECORD_SECONDS`.

Bind `/home/YOUR_USER/.local/bin/whispy` to a shortcut — **use the absolute path**: KDE hotkeys run with `PATH=/usr/bin:/bin` and won't find the command otherwise.

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `whispy` | One toggle step: start recording, or stop and transcribe |
| `whispy ptt` | Push-to-talk in the foreground (useful for debugging) |
| `whispy version` | Print the version |

Logs go to `/tmp/whispy.log` — `tail -f` it while you dictate.

---

## Configuration

`~/.config/whispy/whispy.conf`, all keys optional:

```ini
WHISPER_MODEL=                  # empty = auto-detect
WHISPER_LANGUAGE=en             # en, it, … ("auto" to detect)
WHISPER_THREADS=8
AUTOPASTE=1                     # 0 = clipboard only, no injection
PTT_KEY=META+F12                # push-to-talk key
NOTIFY_LEVEL=normal             # normal | quiet (errors only) | off
MAX_RECORD_SECONDS=8            # toggle safety net
KEEP_AUDIO=0                    # 1 keeps the WAV for inspection
```

### Choosing the key

`PTT_KEY` takes a single key or a combo: `MENU`, `RIGHTCTRL`, `META+F12`, `CTRL+ALT+K`. Names follow `evdev`, with `META`, `SUPER`, `CTRL`, `ALT`, and `SHIFT` as convenience aliases.

The **Menu key** (☰) is an excellent choice: almost nothing else uses it, so it never collides.

> If you pick a combo built on `META`, make sure your desktop hasn't already bound it — otherwise one press fires two things.

### Notification levels

| Level | Behavior |
|-------|----------|
| `normal` | One bubble that updates through the cycle, closed on success |
| `quiet` | Errors only |
| `off` | Silence |

On success with auto-paste, the notification is **closed** rather than repeating text you can already see. Errors stay on screen.

---

## Troubleshooting

### Push-to-talk doesn't react

```bash
systemctl --user status whispy-ptt
journalctl --user -u whispy-ptt -n 30
```

| Cause | Fix |
|-------|-----|
| Not in the `input` group | `sudo usermod -aG input $USER`, then **log out and back in** |
| Keyboard plugged in after start | `systemctl --user restart whispy-ptt` |
| `PTT_KEY` already used by the desktop | Pick another one, e.g. `MENU` |

### It transcribes but doesn't paste

`ydotoold` must be running:

```bash
systemctl --user enable --now ydotoold
```

The text is in the clipboard either way — `Ctrl+V` always works. Set `AUTOPASTE=0` to disable injection entirely.

### "No text" or wrong transcriptions

- Speak for **at least one second**: anything under `0.7s` is discarded
- Set `WHISPER_LANGUAGE` explicitly instead of leaving `auto`
- Switch to `large-v3-turbo`; `base` is weak on non-English speech
- The last failed recording is kept at `/tmp/whispy-last-failed.wav`

### It feels slow

```bash
whisper-cli --help | grep -i gpu     # CUDA build?
nvidia-smi                            # GPU visible?
```

A CPU build with `large-v3-turbo` takes seconds, not milliseconds — use `ggml-base.bin` or install a CUDA build.

If something else is holding your VRAM (a local model server, a game), the GPU build cannot allocate its buffers. Whispy notices and retries on CPU, so dictation still works — just slower. Free the VRAM to get the fast path back.

If you're on **toggle** mode and the wait is always identical, that's not slowness: it's `MAX_RECORD_SECONDS` expiring because the second press never came.

---

## Requirements

| Tool | Purpose | Required |
|------|---------|----------|
| `whisper-cli` | Transcription | Yes |
| `arecord` (alsa-utils) | Recording | Yes — `sox`/`rec` works as fallback |
| `wl-copy` (wl-clipboard) | Clipboard | Yes |
| `ydotool` + `ydotoold` | Auto-paste on Wayland | Only for `AUTOPASTE=1` |
| `notify-send` (libnotify) | Notifications | Only for `NOTIFY_LEVEL≠off` |
| `python-evdev` | Reading the keyboard | Only for push-to-talk |

Python 3.11+. No mandatory Python runtime dependencies — `evdev` is an optional extra.

---

## Development

```bash
pip install -e '.[dev,ptt]'
pytest                                          # no hardware required
ruff check whispy tests && ruff format --check whispy tests
```

Tests stub out `subprocess` and `evdev` devices, so they run anywhere — no microphone, no keyboard, no GPU. They cover WAV header repair, ydotool argument parsing, config loading, notification replacement, key combo parsing, and device selection.

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Whispy stays small: if a feature doesn't serve *speech → cursor*, it probably doesn't belong.

---

## Tech Stack

- **[whisper.cpp](https://github.com/ggerganov/whisper.cpp)** — local transcription, CUDA-accelerated
- **[evdev](https://python-evdev.readthedocs.io/)** — raw keyboard events, press *and* release
- **[ydotool](https://github.com/ReimuNotMoe/ydotool)** — keystroke injection on Wayland
- **ALSA / wl-clipboard / libnotify** — recording, clipboard, notifications
- **Python 3.11+** — standard library only at runtime

---

## License

MIT

---

Built by [Ciro Autuori](https://github.com/ciroautuori).
