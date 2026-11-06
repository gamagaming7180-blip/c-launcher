#!/usr/bin/env bash
# Vesper health check: what is installed, what is running, what is missing. Output goes to a notification
# and to the terminal. Run it, then paste the output if something looks off.
RICE="$HOME/.config/hypr-rice"
out=""; bad=0
chk() { if command -v "$1" >/dev/null 2>&1; then out+="ok       $1"$'\n'; else out+="MISSING  $1  ($2)"$'\n'; bad=$((bad+1)); fi; }
run() { if pgrep -x "$1" >/dev/null 2>&1; then out+="running  $1"$'\n'; else out+="NOT RUNNING  $1"$'\n'; bad=$((bad+1)); fi; }
chk Hyprland "compositor"; chk waybar "bar"; chk rofi "launcher (rofi-wayland on Arch)"; chk mako "notifications"
chk hyprpaper "wallpaper"; chk hyprlock "lock screen"; chk hypridle "idle"; chk kitty "terminal"
chk brightnessctl "brightness"; chk wpctl "volume (pipewire)"; chk playerctl "media keys"; chk grim "screenshots"; chk slurp "screenshots"
chk cliphist "clipboard"; chk wl-copy "clipboard (wl-clipboard)"; chk python3 "scripts"
python3 -c "import PIL" 2>/dev/null && out+="ok       python-pillow"$'\n' || { out+="MISSING  python-pillow (wallpaper colours)"$'\n'; bad=$((bad+1)); }
fc-list 2>/dev/null | grep -qi "JetBrainsMono Nerd" && out+="ok       JetBrainsMono Nerd Font"$'\n' || { out+="MISSING  JetBrainsMono Nerd Font (icons in the bar)"$'\n'; bad=$((bad+1)); }
for p in waybar mako hyprpaper hypridle; do run "$p"; done
[[ -f "$RICE/generated/palette.json" ]] && out+="ok       palette generated"$'\n' || { out+="MISSING  palette: run scripts/wallcolors.py --reapply"$'\n'; bad=$((bad+1)); }
printf '%s' "$out"
notify-send -a "Vesper" "Health check: $([ $bad -eq 0 ] && echo all good || echo "$bad problem(s)")" "$(printf '%s' "$out" | grep -E 'MISSING|NOT RUNNING' | head -6)" 2>/dev/null
