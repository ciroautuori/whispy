# Desktop entry and provider switching

**Date:** 2026-07-28
**Status:** approved

## Problem

Two things make Whispy harder to use than it needs to be.

**The application icon does the wrong thing.** `install.sh` writes a
`whispy.desktop` whose `Exec` is the dictation wrapper, so clicking "Whispy
Dictate" in the launcher starts a recording. Nothing opens, nothing is
visible, and the recording stops on its own eight seconds later. The entry
looks broken because it behaves nothing like an application.

**Switching provider is a chore.** It means opening the control panel,
picking from a dropdown, and remembering to press *Save Config* — miss that
last step and nothing happened. There is no way to switch without a GUI.

## Goals

- Clicking the icon opens the control panel.
- Switching provider takes one click, from the launcher, without opening
  anything.
- The switcher never offers a provider that cannot work right now.

## Non-goals

- A tray icon. It would be the most convenient option but needs a resident
  process and a tray dependency; the desktop entry gets us most of the way
  for none of the cost.
- A bespoke application icon. The system `audio-input-microphone` icon stays.

## Design

### Desktop entry

`Exec` points at the control panel. Desktop **Actions** provide the rest:

```
Apri pannello        (default click)
Detta ora            → the dictation wrapper
─────────────
● Local              → whispy use local
  Faster-Whisper     → whispy use faster_whisper
```

Only *ready* providers are listed. A provider is ready when it needs no API
key (`local`, `faster_whisper`, `ollama`) or when its environment variable is
present in `whispy.env` or the environment. So the menu grows as keys are
added and never offers an option that would fail.

Action identifiers are restricted to `A-Za-z0-9-` by the Desktop Entry
specification, so `faster_whisper` becomes the action `provider-faster-whisper`
while still invoking `whispy use faster_whisper`.

### Components

**`whispy/desktop.py`** (new)

| Function | Responsibility |
|---|---|
| `ready_providers(keys)` | Which providers can run right now |
| `render(active, ready, ...)` | Pure — returns the file contents as a string |
| `write(...)` | Reads config and keys, renders, writes, refreshes the DE cache |

`render` is pure so the whole menu can be tested without a desktop, a display,
or a filesystem. The provider list and labels come from `PROVIDER_INFO`, so
there is no second copy to keep in sync.

**`whispy/providers/__init__.py`** — gains a `label` per provider ("Hugging
Face", "OpenAI"), keeping display names in the registry rather than a
parallel map.

**`whispy/config.py`** — gains `set_key(key, value)`, a single-line edit of
`whispy.conf`. Necessary because `Config.save()` rewrites the whole file and
would delete the user's comments.

**`whispy/__main__.py`** — two commands:

- `whispy use <provider>` — validate against the registry, write `PROVIDER=`,
  regenerate the desktop entry, notify.
- `whispy desktop` — regenerate the entry on demand.

**`whispy/gui/app.py`** — regenerates the entry after *Save Keys*, so a
provider appears in the menu as soon as its key is stored. The provider
dropdown applies immediately rather than waiting for *Save Config*; the other
fields keep the explicit save, since the provider is the one setting that gets
changed often.

**`install.sh`** — calls `whispy desktop` instead of writing the file inline.

### Flow

```
right-click → "Groq" → whispy use groq
                         ├─ known provider?        (registry)
                         ├─ PROVIDER=groq          (rest of the file untouched)
                         ├─ regenerate .desktop    (● moves to Groq)
                         └─ notify "Provider: Groq"
```

### Error handling

| Situation | Behaviour |
|---|---|
| Unknown provider name | Exit 1, print the valid names |
| Provider needs a key that is absent | Set it anyway, but warn: it is reachable only from the CLI, and refusing would be surprising |
| Config or applications dir not writable | Clear message, exit 1 |
| `update-desktop-database` missing | Ignore; the file is still written |

### Testing

`render` is pure, so its output is asserted directly: the menu for a given set
of keys, the active marker, action identifiers valid per the specification,
`Exec` quoting. `set_key` is tested for preserving comments and unrelated
lines. `whispy use` is tested for rejecting unknown names. The generated file
is checked with `desktop-file-validate` where available.

## Known limits

The `●` marker on the active provider depends on the desktop environment
reloading its `.desktop` cache. `update-desktop-database` is invoked, but KDE
may lag. The notification is the authoritative feedback; the marker is
cosmetic.
