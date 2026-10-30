#!/usr/bin/env bash
# Click the clock (or SUPER + A): show / hide the control panel.
# The panel keeps running in the background (about 80 MB) so it opens instantly; this just signals it.
#   panel-toggle.sh             toggle
#   panel-toggle.sh --restart   kill and start a fresh panel (if it ever misbehaves)
RICE="$HOME/.config/hypr-rice"
LOCK="${XDG_RUNTIME_DIR:-/tmp}/hypr-rice-panel.lock"
LOG="$HOME/.cache/hypr-rice-panel.log"
mkdir -p "$HOME/.cache"
[ -f "$LOG" ] && [ "$(stat -c %s "$LOG" 2>/dev/null || echo 0)" -gt 200000 ] && : > "$LOG"

if [ "${1:-}" = "--restart" ]; then
    pkill -f '^(\S*/)?python3?([.0-9]+)? (\S*/)?scripts/panel\.py' 2>/dev/null
    sleep 0.4
fi

pid="$(cat "$LOCK" 2>/dev/null)"
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q 'panel\.py'; then
    kill -USR1 "$pid"
    exit 0
fi
[ -n "$pid" ] && rm -f "$LOCK"   # stale lock from a dead panel

# gtk-layer-shell must be loaded before libwayland-client; panel.py also does this itself.
[ -e /usr/lib/libgtk-layer-shell.so ] && export LD_PRELOAD="/usr/lib/libgtk-layer-shell.so${LD_PRELOAD:+:$LD_PRELOAD}"
exec python3 "$RICE/scripts/panel.py" "$@" 2>>"$LOG"
