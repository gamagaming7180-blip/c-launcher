#!/usr/bin/env bash
# Wallpaper control. Colours (bar, borders, launcher, notifications, lock screen) follow the image.
#   wallpaper.sh            random wallpaper        wallpaper.sh next | prev
#   wallpaper.sh pick       thumbnail picker        wallpaper.sh set /path/to/image
#   wallpaper.sh folder     open the main wallpaper folder in Thunar
#   wallpaper.sh list       show which folders are scanned and every image found
# The folders are scanned fresh on every call (subfolders included), so adding or
# removing an image needs nothing else. Extra folders: one per line in
# ~/.config/hypr-rice/wallpaper-dirs
# The choice is remembered across restarts and used by the lock screen.
RICE="$HOME/.config/hypr-rice"
GEN="$RICE/generated"
mkdir -p "$GEN"

# Folders to scan. The first one is the "main" folder that `folder` opens.
DIRS=("$HOME/Pictures/Wallpapers" "$RICE/wallpapers")
if [ -f "$RICE/wallpaper-dirs" ]; then
    while IFS= read -r line; do
        line="${line%%#*}"
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [ -n "$line" ] || continue
        DIRS+=("${line/#\~/$HOME}")
    done < "$RICE/wallpaper-dirs"
fi

list() {
    local d
    for d in "${DIRS[@]}"; do
        [ -d "$d" ] || continue
        find -L "$d" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \) 2>/dev/null
    done | sort -u
}

apply() {
    [ -f "$1" ] || { notify-send -t 3000 "Wallpaper" "Not found: $1"; exit 1; }
    pgrep -x hyprpaper >/dev/null || { hyprpaper -c "$RICE/hyprpaper.conf" >/dev/null 2>&1 & sleep 0.6; }
    hyprctl hyprpaper wallpaper ",$1,cover" >/dev/null
    echo "$1" > "$GEN/current-wallpaper"
    python3 "$RICE/scripts/wallcolors.py" "$1" --persist >/dev/null 2>&1
}

current() { cat "$GEN/current-wallpaper" 2>/dev/null; }

step() {   # $1 = +1 / -1
    mapfile -t all < <(list)
    [ "${#all[@]}" -gt 0 ] || { notify-send -t 3000 "Wallpaper" "No images found. Run: wallpaper.sh list"; exit 1; }
    cur="$(current)"; idx=-1
    for i in "${!all[@]}"; do [ "${all[$i]}" = "$cur" ] && idx=$i; done
    if [ "$idx" -lt 0 ]; then
        [ "$1" -gt 0 ] && n=0 || n=$(( ${#all[@]} - 1 ))
    else
        n=$(( (idx + $1 + ${#all[@]}) % ${#all[@]} ))
    fi
    apply "${all[$n]}"
}

case "${1:-random}" in
    random) mapfile -t all < <(list)
            [ "${#all[@]}" -gt 0 ] && apply "${all[RANDOM % ${#all[@]}]}" ;;
    next)   step 1 ;;
    prev)   step -1 ;;
    set)    apply "$2" ;;
    folder) mkdir -p "${DIRS[0]}"
            if command -v thunar >/dev/null; then thunar "${DIRS[0]}" >/dev/null 2>&1 &
            else xdg-open "${DIRS[0]}" >/dev/null 2>&1 & fi ;;
    list)   echo "Scanning:"; printf '  %s\n' "${DIRS[@]}"
            mapfile -t all < <(list)
            echo "Found ${#all[@]} images:"; printf '  %s\n' "${all[@]}" ;;
    pick)
        mapfile -t all < <(list)
        [ "${#all[@]}" -gt 0 ] || { notify-send -t 3000 "Wallpaper" "No images found. Run: wallpaper.sh list"; exit 1; }
        # -format i returns the position of the chosen entry (0 = Random), so two
        # files with the same name in different folders can never be mixed up.
        idx=$( { printf '%s\n' "Random"
                 for f in "${all[@]}"; do printf '%s\0icon\x1f%s\n' "$(basename "$f")" "$f"; done
               } | rofi -config "$RICE/rofi/config.rasi" -theme "$RICE/rofi/catppuccin.rasi" \
                     -dmenu -show-icons -i -no-custom -format i -p " Wallpaper" \
                     -theme-str 'window { width: 780px; } listview { columns: 3; lines: 3; fixed-columns: true; } element { orientation: vertical; padding: 10px; } element-icon { size: 170px; } element-text { horizontal-align: 0.5; }' )
        [ -n "$idx" ] && [ "$idx" -ge 0 ] 2>/dev/null || exit 0
        if [ "$idx" -eq 0 ]; then exec "$0" random; fi
        apply "${all[$((idx - 1))]}" ;;
    *) echo "usage: wallpaper.sh [random|next|prev|pick|set FILE|folder|list]"; exit 1 ;;
esac
