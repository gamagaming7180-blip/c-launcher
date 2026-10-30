#!/usr/bin/env bash
# Power menu: drops down from the top-right corner under the bar's power button. Click the button again (or Esc) to close.
RICE="${HOME}/.config/hypr-rice"

# second click on the button closes an open menu
if pgrep -x rofi >/dev/null 2>&1; then pkill -x rofi; exit 0; fi

command -v rofi >/dev/null 2>&1 || { notify-send -a "Hypr Rice" "Power menu" "rofi is not installed" 2>/dev/null; exit 1; }

opts=(-dmenu -i -no-custom -p "Power" -format s)
[[ -f "$RICE/rofi/config.rasi" ]]     && opts=(-config "$RICE/rofi/config.rasi" "${opts[@]}")
[[ -f "$RICE/rofi/catppuccin.rasi" ]] && opts+=(-theme "$RICE/rofi/catppuccin.rasi")
# small card hanging under the button; no search box, five rows
opts+=(-theme-str 'window { location: northeast; anchor: northeast; width: 210px; x-offset: -12px; y-offset: 56px; }'
       -theme-str 'inputbar { enabled: false; } listview { lines: 5; scrollbar: false; fixed-height: true; }')

pick="$(printf '%s\n' "Lock" "Sleep" "Log out" "Reboot" "Shut down" | rofi "${opts[@]}" 2>/dev/null)" || exit 0

case "$pick" in
    "Lock")      hyprlock 2>/dev/null || loginctl lock-session ;;
    "Sleep")     systemctl suspend ;;
    "Log out")   hyprctl dispatch exit 2>/dev/null || loginctl terminate-user "$USER" ;;
    "Reboot")    systemctl reboot ;;
    "Shut down") systemctl poweroff ;;
esac
