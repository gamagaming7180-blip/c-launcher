#!/usr/bin/env bash
# screenshot.sh region|screen
# Saves to ~/Pictures/Screenshots, copies to the clipboard and shows a notification with a thumbnail.
# The region selector uses the current wallpaper accent from generated/colors.lua, so it follows the palette.
RICE="$HOME/.config/hypr-rice"
DIR="$HOME/Pictures/Screenshots"

for t in grim wl-copy; do
    command -v "$t" >/dev/null 2>&1 || { notify-send -a Screenshot "Screenshot failed" "$t is not installed"; exit 1; }
done
mkdir -p "$DIR"

accent="$(sed -n 's/.*accent *= *"\([0-9a-fA-F]\{6\}\)".*/\1/p' "$RICE/generated/colors.lua" 2>/dev/null | head -n1)"
accent="${accent:-9fceef}"
file="$DIR/$(date +%F_%H-%M-%S).png"

case "${1:-region}" in
    region)
        command -v slurp >/dev/null 2>&1 || { notify-send -a Screenshot "Screenshot failed" "slurp is not installed"; exit 1; }
        geom="$(slurp -b 0b0b0f99 -c "${accent}ff" -w 2)" || exit 0     # Esc cancels quietly
        grim -g "$geom" "$file" || exit 1
        ;;
    screen)
        grim "$file" || exit 1
        ;;
    *)
        echo "usage: screenshot.sh region|screen" >&2
        exit 2
        ;;
esac

wl-copy < "$file"
notify-send -a Screenshot -i "$file" -t 2500 "Screenshot saved" "Copied to the clipboard"
