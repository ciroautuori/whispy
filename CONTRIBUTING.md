# Contributing to Whispy

Thanks for considering a contribution! Whispy is a small, focused project and
the easier the change is to review, the faster it lands.

## Getting started

```bash
git clone https://github.com/ciroautuori/whispy.git
cd whispy
pip install -e ".[dev]"
```

## Code style

- We use [ruff](https://docs.astral.sh/ruff) for linting and formatting.
  Run `ruff check whispy` and `ruff format whispy` before pushing.
- Target Python 3.11+ — do not add runtime dependencies on third-party
  packages unless strictly necessary. Whispy's selling point is a tiny,
  stdlib-only runtime.
- Keep modules independent. `audio`, `transcribe`, `paste`, `toggle`, and
  `config` should each remain importable in isolation.
- Prefer composition over global state. No module-level mutable singletons.

## Commit messages

Use the [Conventional Commits](https://www.conventionalcommits.org) format:

```
feat(toggle): handle SIGINT gracefully during recording
fix(paste): fall back to stdout when wtype missing
docs(readme): document the server backend
```

## Pull requests

1. Open an issue describing what you intend to change (bug, feature, refactor).
2. Fork the repo and create a branch: `feat/<short-slug>` or `fix/<short-slug>`.
3. Make your changes, keeping diffs small and focused.
4. Run `ruff check` and `ruff format` — CI will enforce this.
5. Add a changelog entry under `CHANGES.md` if the change is user-facing.
6. Open the PR, linking the issue. Describe how you tested the change.

## Testing hardware-specific features locally

Recording and pasting need a real desktop session. For non-hardware logic
(config parsing, postprocessing, debounce), add unit tests under `tests/`
using the stdlib `unittest` or `pytest` frameworks. Mock subprocesses.

## Reporting issues

Include:
- OS + desktop (KDE/GNOME/Sway/Hyprland/…)
- Session type (`echo $XDG_SESSION_TYPE`)
- `whisper-cli --version` output
- Relevant lines from `/tmp/whispy.log` if present
- The exact hotkey binding and how it invokes whispy

## Areas that need help

- macOS recording backend (CoreAudio)
- Windows recording backend (waveapi / WASAPI)
- Translations of the README and UI strings
