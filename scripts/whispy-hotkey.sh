#!/usr/bin/env bash
# Hotkey entry point. Installed to ~/.local/bin/whispy-hotkey — pip never touches it.
#
# Desktop hotkeys run with a bare environment: KDE gives PATH=/usr/bin:/bin and
# no session variables, so everything the paste path needs is set up here.
export PATH="${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export YDOTOOL_SOCKET="${YDOTOOL_SOCKET:-${XDG_RUNTIME_DIR}/.ydotool_socket}"
export XDG_SESSION_TYPE="${XDG_SESSION_TYPE:-wayland}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"

echo "$(date '+%Y-%m-%d %H:%M:%S') hotkey-wrapper pid=$$" >> /tmp/whispy.log 2>/dev/null || true

PY="$(command -v python3 || command -v python || true)"
if [[ -z "$PY" ]]; then
  echo "no python" >> /tmp/whispy.log
  notify-send -u critical Whispy "python not found" 2>/dev/null || true
  exit 1
fi

exec "$PY" -m whispy "$@"
