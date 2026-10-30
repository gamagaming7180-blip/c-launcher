#!/usr/bin/env bash
# Night light (warm screen colour) using hyprsunset.
#   nightlight.sh toggle | on [KELVIN] | off | set KELVIN | status
#   nightlight.sh auto on|off            turn the schedule on or off
#   nightlight.sh schedule 20:00 07:00   warm from 20:00 until 07:00 (default)
#   nightlight.sh daemon                 applies the schedule (started with the session)
# Warmth: 6500 = normal, 4500 = mild, 3500 = strong, 2500 = very orange.
RICE="$HOME/.config/hypr-rice"
GEN="$RICE/generated"
CONF="$GEN/nightlight.conf"
mkdir -p "$GEN"
TEMP=4200; AUTO=0; FROM=20:00; TO=07:00
[ -f "$CONF" ] && . "$CONF"

save() { printf 'TEMP=%s\nAUTO=%s\nFROM=%s\nTO=%s\n' "$TEMP" "$AUTO" "$FROM" "$TO" > "$CONF"; }
running() { pgrep -x hyprsunset >/dev/null; }
clamp() { local k=${1//[^0-9]/}; k=${k:-4200}; [ "$k" -lt 1500 ] && k=1500; [ "$k" -gt 6500 ] && k=6500; echo "$k"; }

start() {
    command -v hyprsunset >/dev/null || { notify-send -t 4000 "Night light" "Install hyprsunset: sudo pacman -S hyprsunset"; exit 1; }
    pkill -x hyprsunset 2>/dev/null; sleep 0.1
    setsid hyprsunset -t "$TEMP" >/dev/null 2>&1 &
}
stop() { pkill -x hyprsunset 2>/dev/null; }
mins() { local h=${1%%:*} m=${1##*:}; echo $(( 10#$h * 60 + 10#$m )); }
in_window() {
    local now f t; now=$(mins "$(date +%H:%M)"); f=$(mins "$FROM"); t=$(mins "$TO")
    if [ "$f" -le "$t" ]; then [ "$now" -ge "$f" ] && [ "$now" -lt "$t" ]
    else [ "$now" -ge "$f" ] || [ "$now" -lt "$t" ]; fi
}

case "${1:-status}" in
    on)       [ -n "$2" ] && { TEMP=$(clamp "$2"); save; }; start ;;
    off)      stop ;;
    toggle)   if running; then stop; else start; fi ;;
    set)      TEMP=$(clamp "$2"); save; running && start ;;
    auto)     [ "$2" = on ] && AUTO=1 || AUTO=0; save
              if [ "$AUTO" = 1 ]; then in_window && start; fi ;;
    schedule) FROM=${2:-$FROM}; TO=${3:-$TO}; save ;;
    daemon)
        exec 9>"$GEN/nightlight.lock"; flock -n 9 || exit 0
        last=""
        while sleep 30; do
            [ -f "$CONF" ] && . "$CONF"
            [ "$AUTO" = 1 ] || { last=""; continue; }
            if in_window; then want=on; else want=off; fi
            if [ "$want" != "$last" ]; then          # act only on changes, so manual toggles are not fought
                [ "$want" = on ] && start || stop
                last=$want
            fi
        done ;;
    status)   if running; then echo "on $TEMP"; else echo "off $TEMP"; fi
              echo "auto=$AUTO from=$FROM to=$TO" ;;
    *) echo "usage: nightlight.sh toggle|on [K]|off|set K|auto on|off|schedule FROM TO|status"; exit 1 ;;
esac
