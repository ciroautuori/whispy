#!/usr/bin/env bash
# Whispy installer — Python package + optional system deps + desktop entry.
# Safe to re-run. No Rust, no Tauri, no Electron — Python only.
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "→ Installing whispy (prefix: $PREFIX)"

# ── Python package (runtime + desktop UI deps) ─────────────────────
if command -v uv >/dev/null 2>&1; then
    uv tool install -e "$SCRIPT_DIR" --force --with "whispy[desktop]"
    ln -sf "$(uv tool dir)"/bin/whispy "$PREFIX/bin/whispy" 2>/dev/null || true
elif command -v pip >/dev/null 2>&1; then
    pip install -e "$SCRIPT_DIR[desktop]" --user --quiet
fi

# ── Default config ──────────────────────────────────────────────────
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/whispy"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/whispy"
mkdir -p "$CONFIG_DIR" "$DATA_DIR/models"
if [[ ! -f "$CONFIG_DIR/whispy.conf" ]]; then
    cat > "$CONFIG_DIR/whispy.conf" <<'CONF'
# Whispy configuration
BACKEND="cli"
WHISPER_MODEL=""
WHISPER_LANGUAGE="auto"
WHISPER_THREADS=4
AUTOPASTE=1
SILENCE_DURATION=1.5
SILENCE_THRESHOLD=3
MAX_RECORD_SECONDS=120
CONF
    echo "→ Wrote default config to $CONFIG_DIR/whispy.conf"
fi

# ── Desktop entries ─────────────────────────────────────────────────
mkdir -p "$PREFIX/share/applications"
cat > "$PREFIX/share/applications/whispy.desktop" <<'DESK'
[Desktop Entry]
Name=Whispy Dictate
Comment=Press once to record, press again to transcribe and paste
Exec=whispy
Icon=microphone-sensitivity-high-symbolic
Type=Application
Terminal=false
Categories=Utility;AudioVideo;
DESK

cat > "$PREFIX/share/applications/whispy-brain.desktop" <<'DESK'
[Desktop Entry]
Name=Whispy Brain
Comment=Notion + Obsidian hybrid second brain — HyperKanban, notes, graph
Exec=whispy brain
Icon=accessories-text-editor-symbolic
Type=Application
Terminal=false
Categories=Utility;Office;
DESK
echo "→ Desktop entries installed (whispy, whispy-brain)"

# ── Optional system tools check ─────────────────────────────────────
echo ""
echo "System tools status:"
for tool in whisper-cli whisper-server rec arecord wtype ydotool xdotool wl-copy; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "  ✓ $tool"
    else
        echo "  ✗ $tool (optional)"
    fi
done

echo ""
echo "✔ Done."
echo "  Bind hotkey (e.g. Super+F12) →: $PREFIX/bin/whispy"
echo "  Open Second Brain desktop app →: whispy brain"
