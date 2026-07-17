<div align="center">

# 🎙️ Whispy

**Local speech-to-text + Second Brain for the desktop. Press to record → transcribe → paste, and keep a Notion+Obsidian hybrid brain in one Python app.**

🎤 Dictate anywhere · 🗂️ HyperKanban nested tasks · 📝 Markdown notes · 🔗 Backlinks · 🕸️ Graph view · 📱 Mobile-first · 🐍 Python only

</div>

---

## What is Whispy?

Whispy is **two tools in one pure-Python desktop app**:

1. **A dictation toggle** — press a hotkey (`Super+F12`), talk, press again → your words are transcribed locally with `whisper.cpp` and pasted at the cursor. No cloud, no subscription.
2. **A Second Brain** — a compact desktop webapp (FastAPI + pywebview, *Python only — no Rust, no Tauri, no Electron*) that blends the best of **Notion** (nested HyperKanban boards, properties, databases) and **Obsidian** (markdown notes, `[[wikilink]]` backlinks, graph view).

Everything runs 100% on your machine. The brain is a single JSON file you own.

---

## ✨ Features

**Dictation**
- 🖱️ One hotkey — toggle record / transcribe-and-paste
- 🔒 Fully offline via `whisper.cpp` (GPU-accelerated when available)
- ⚡ `whisper-server` (warm model) or `whisper-cli` backends
- 🐧 Wayland (`wtype`/`ydotool`/`wl-copy`) + X11 (`xdotool`/`xsel`) paste
- 📝 `whispy ingest` — pipe transcribed text straight into a brain note

**Second Brain**
- 🌳 **HyperKanban tree** — workspaces, areas, boards, tasks, subtasks nest infinitely; indent/outdent, move, reorder
- 🗂️ **Kanban view** — tasks grouped into Todo / Doing / Review / Done columns
- 📝 **Notes view** — Obsidian-style markdown with live backlinks
- 🔗 **Backlinks** — `[[note title]]` in any body auto-links; see who links back
- 🕸️ **Graph view** — draggable canvas of all nodes + backlink edges, click to open
- 📊 **Stats view** — totals, by status/priority/type, overdue count
- 🔎 **Full-text search** — title, body, tags, descriptions
- 🌓 Dark/light theme, persisted
- 📱 Mobile-first responsive UI — works great on a phone-width window

---

## Quick start

### 1. System prerequisites

| Tool | Why | Install |
|------|-----|---------|
| `whisper.cpp` (`whisper-cli` / `whisper-server`) | Speech recognition | `yay -S whisper.cpp-cuda` (Arch) · `brew install whisper-cpp` (mac) |
| `sox` (`rec`) or `alsa-utils` (`arecord`) | Capture microphone | `sudo pacman -S sox alsa-utils` |
| `wtype` (Wayland) / `xdotool` (X11) | Paste at cursor | `sudo pacman -S wtype xdotool` |
| `wl-clipboard` / `xsel` | Clipboard | `sudo pacman -S wl-clipboard xsel` |

### 2. Install Whispy

```bash
git clone https://github.com/ciroautuori/whispy.git
cd whispy
./install.sh
```

…or manually:

```bash
pip install -e ".[desktop]"   # desktop = pywebview + Qt/GTK backends
# or just the core (use a browser to view the brain):
pip install -e .
```

### 3. Open the Second Brain desktop app

```bash
whispy brain        # native window (pywebview)
# …or run the server only and open in a browser:
whispy serve --port 58182
```

### 4. (Optional) Dictation setup

```bash
# Download a model
mkdir -p ~/.local/share/whispy/models
curl -L -o ~/.local/share/whispy/models/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin

# Edit ~/.config/whispy/whispy.conf
# Bind Super+F12 → `whispy` in your desktop settings (KDE/GNOME/Hyprland)
```

Press `Super+F12`, talk, press again — text appears at the cursor.

---

## How it works

```
┌──────────────────────────────────────────────────────────────┐
│                          Whispy                               │
│                                                               │
│   ┌──────────────────┐        ┌────────────────────────────┐   │
│   │ Dictation toggle │        │   Second Brain (desktop)  │   │
│   │  Super+F12       │        │                            │   │
│   │   → record       │        │  FastAPI (:58182)         │   │
│   │   → whisper.cpp  │        │   + pywebview native window│   │
│   │   → paste cursor │        │                            │   │
│   └────────┬─────────┘        │  Tree · Kanban · Notes    │   │
│            │ whispy ingest   │  Graph · Stats · Search   │   │
│            └─────────────────►  Backlinks (Obsidian)     │   │
│                              │  HyperKanban nested tree  │   │
│                              │  brain.json (single file) │   │
│                              └────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Dictation and the brain are deliberately decoupled: you can use either
one standalone, or bridge them with `whispy ingest` to drop transcribed
voice notes straight into your knowledge base.

---

## Architecture

```
whispy/
├── __init__.py      # version
├── __main__.py      # CLI: toggle · record · transcribe · serve · brain · version
├── toggle.py        # hotkey toggle loop: record ⇄ transcribe+paste
├── config.py        # whispy.conf loader (dataclass)
├── audio.py         # recording backend (sox / arecord)
├── transcribe.py    # whisper.cpp backends (server / cli)
├── paste.py         # clipboard injection (wayland / x11 / fallback)
├── store.py         # HyperKanban tree store (JSON, Notion+Obsidian model)
├── server.py        # FastAPI: tree/kanban/graph/backlinks/stats/search/ingest
└── webapp.py        # pywebview desktop window launcher

web/
├── index.html       # mobile-first single-page UI
├── styles.css       # dark/light theme
└── main.js          # tree, kanban, notes, graph, editor, search
```

Every module is importable and testable on its own. No global state in the
core logic; the UI is a thin vanilla-JS client talking to the REST API.

---

## CLI

```bash
whispy                # toggle record/transcribe+paste (bind to a hotkey)
whispy record         # force-start a recording
whispy transcribe     # transcribe the latest recording and paste
whispy serve          # run the Second Brain REST+UI server
whispy brain          # open the Second Brain in a native desktop window
whispy version        # print the installed version
python -m whispy      # same as `whispy`
```

---

## REST API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/api/tree` | Nested tree (HyperKanban) |
| `GET` | `/api/nodes/{id}` | Single node + children |
| `POST` | `/api/nodes` | Create a node |
| `PATCH` | `/api/nodes/{id}` | Update a node |
| `DELETE` | `/api/nodes/{id}` | Delete a node (+ subtree) |
| `POST` | `/api/nodes/{id}/move` | Re-parent / reorder |
| `POST` | `/api/nodes/{id}/indent` | Indent / outdent |
| `POST` | `/api/nodes/{id}/toggle` | Cycle status (todo→doing→done) |
| `GET` | `/api/search?q=` | Full-text search |
| `GET` | `/api/graph` | Nodes + backlink edges |
| `GET` | `/api/backlinks/{id}` | Nodes linking to this one |
| `GET` | `/api/stats` | Aggregate statistics |
| `POST` | `/api/ingest` | Create a note from text (dictation bridge) |
| `GET` | `/health` | Health check |

---

## Second Brain model

Inspired by **Notion** (databases, properties, kanban) and **Obsidian**
(markdown + wikilinks + graph), and by the **HyperTask** nested-tree
task model:

```
Workspace
└── Area
    └── Board
        └── Task
            └── Subtask … (infinite)
Note (anywhere; markdown + [[backlinks]])
```

Each node carries: title, markdown body, type, status, priority, due date,
tags, position (for ordering), and a parent pointer for the nested tree.
`[[Wikilink Title]]` inside any body creates a backlink automatically —
click through in the editor or visualize all relationships in the graph view.

---

## Configuration

File: `${XDG_CONFIG_HOME:-~/.config}/whispy/whispy.conf`
Brain: `${XDG_DATA_HOME:-~/.local/share}/whispy/brain.json`

| Key | Default | Description |
|-----|---------|-------------|
| `BACKEND` | `cli` | `cli` (whisper-cli) or `server` (warm whisper-server) |
| `WHISPER_MODEL` | `…/models/ggml-base.bin` | Path to a `ggml-*.bin` model |
| `WHISPER_LANGUAGE` | `auto` | ISO code (`it`, `en`, …) or `auto` |
| `WHISPER_THREADS` | `4` | CPU threads for inference |
| `AUTOPASTE` | `1` | `1` → paste at cursor; `0` → print to stdout |
| `SILENCE_DURATION` | `1.5` | Silence seconds before auto-stop (sox) |
| `SILENCE_THRESHOLD` | `3` | Silence threshold percent (sox) |
| `MAX_RECORD_SECONDS` | `120` | Hard cap |
| `KEEP_AUDIO` | `0` | Keep the WAV for debugging |
| `RECORD_DEVICE` | `default` | ALSA device name (arecord) |

---

## Development

```bash
git clone https://github.com/ciroautuori/whispy.git
cd whispy
pip install -e ".[dev]"
ruff check whispy && ruff format whispy
pytest -q
whispy brain      # launch the app and click around
```

---

## Tech stack

- **Python 3.11+** (stdlib + FastAPI at runtime; pywebview for the desktop window)
- **[FastAPI](https://fastapi.tiangola.com/)** — REST API for the brain
- **[uvicorn](https://www.uvicorn.org/)** — ASGI server
- **[pywebview](https://pywebview.flowrl.com/)** — native desktop window (Qt/GTK/WebKit/EdgeChromium)
- **[whisper.cpp](https://github.com/ggerganov/whisper.cpp)** — local speech-to-text
- **sox / ALSA** — audio capture · **wtype / ydotool / xdotool** — keyboard injection
- **Vanilla HTML/CSS/JS** — zero frontend build, no node_modules

## Roadmap

- [ ] `whispy-server` warm-model daemon for sub-second dictation
- [ ] Transclusion and live markdown preview in the editor
- [ ] Daily notes / calendar view
- [ ] Notion API + Google Tasks sync
- [ ] Noise suppression via RNNoise
- [ ] macOS / Windows native recording backends
- [ ] PWA / installable on mobile via the served UI
- [ ] Vector search over note bodies

## License

MIT © [Ciro Autuori](https://github.com/ciroautuori)

---

Built because talking is faster than typing, and your knowledge belongs to you.
