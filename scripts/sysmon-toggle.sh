#!/usr/bin/env bash
# Click the bar's CPU/RAM pill: open the monitor; click again (or press q) to close it.
RICE="$HOME/.config/hypr-rice"

# Already open? Close it.
if pkill -f -- '--class sysmon'; then
    exit 0
fi

exec kitty --config "$RICE/kitty/kitty.conf" \
    --class sysmon --title "System Monitor" \
    -o initial_window_width=64c -o initial_window_height=24c \
    -o remember_window_size=no -o window_padding_width=10 -o background_opacity=0.94 \
    python3 "$RICE/scripts/sysmon.py"
