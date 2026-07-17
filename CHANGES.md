# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release of Whispy.
- Dictation toggle: press once to record, press again to transcribe and paste.
- `whispy` CLI with `record`, `transcribe`, `serve`, `brain`, and `version` subcommands.
- `whispy.conf` configuration with sensible defaults.
- sox and ALSA recording backends.
- whisper.cpp `server` and `cli` transcription backends.
- Wayland (`wtype`, `ydotool`, `wl-copy`) and X11 (`xdotool`, `xsel`) paste.
- **Second Brain** desktop webapp (FastAPI + pywebview, Python only):
  - HyperKanban nested task tree (workspace → area → board → task → subtask).
  - Kanban, Tree, Notes, Graph, and Stats views.
  - Obsidian-style `[[wikilink]]` backlinks.
  - Draggable graph view of all nodes and backlink edges.
  - Full-text search across titles, bodies, tags, descriptions.
  - Mobile-first responsive single-page UI with dark/light theme.
  - Single JSON file persistence (`brain.json`).
- `install.sh` for one-shot setup on Linux with two desktop entries.
- `whispy ingest` / `POST /api/ingest` to bridge dictation into the brain.
