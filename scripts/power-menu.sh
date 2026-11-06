#!/usr/bin/env bash
# Power menu: a small glass card hanging under the bar's power button. Click the button again (or Esc) to close.
RICE="${HOME}/.config/hypr-rice"

# second click on the button closes an open menu
if pgrep -x rofi >/dev/null 2>&1; then pkill -x rofi; exit 0; fi

command -v rofi >/dev/null 2>&1 || { notify-send -a "Vesper" "Power menu" "rofi is not installed" 2>/dev/null; exit 1; }

opts=(-dmenu -i -no-custom -p "" -format s)
[[ -f "$RICE/rofi/config.rasi" ]] && opts=(-config "$RICE/rofi/config.rasi" "${opts[@]}")
THEME="$RICE/rofi/vesper.rasi"; [[ -f "$THEME" ]] || THEME="$RICE/rofi/catppuccin.rasi"
[[ -f "$THEME" ]] && opts+=(-theme "$THEME")
# compact card, no search box, five rows
opts+=(-theme-str 'window { location: northeast; anchor: northeast; width: 230px; x-offset: -12px; y-offset: 46px; border-radius: 24px; }'
       -theme-str 'mainbox { padding: 10px; } inputbar { enabled: false; } listview { lines: 5; scrollbar: false; fixed-height: true; } element { padding: 10px 16px; }')

pick="$(printf '%s\n' "󰌾  Lock" "󰤄  Sleep" "󰍃  Log out" "󰜉  Reboot" "󰐥  Shut down" | rofi "${opts[@]}" 2>/dev/null)" || exit 0

case "$pick" in
    *Lock)      hyprlock -c "$RICE/hyprlock.conf" 2>/dev/null || loginctl lock-session ;;
    *Sleep)     systemctl suspend ;;
    *"Log out") hyprctl dispatch 'hl.dsp.exit()' 2>/dev/null || loginctl terminate-user "$USER" ;;
    *Reboot)    systemctl reboot ;;
    *"Shut down") systemctl poweroff ;;
esac
