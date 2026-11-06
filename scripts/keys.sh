#!/usr/bin/env bash
# Keybind cheat sheet (SUPER + F1). Read-only list in a rofi card; Esc closes it.
RICE="$HOME/.config/hypr-rice"
THEME="$RICE/rofi/vesper.rasi"
cat <<'KEYS' | rofi -config "$RICE/rofi/config.rasi" -theme "$THEME" -dmenu -i -no-custom -p "󰌌" \
    -theme-str 'window { width: 760px; } listview { lines: 14; } element-text { font: "JetBrainsMono Nerd Font 11"; }'
SUPER + Return           terminal
SUPER + SPACE            app grid
SUPER + A                control panel (wifi, volume, brightness, media)
SUPER + V                clipboard history
SUPER + Tab              window switcher
SUPER + E / B            files / browser
SUPER + G                system monitor
SUPER + Q                close window
SUPER + F / M            fullscreen / maximize
SUPER + T                toggle floating
SUPER + P / Y            pseudo-tile / flip split
SUPER + arrows or H J K ;   move focus
SUPER + SHIFT + arrows   move window
SUPER + CTRL + arrows    resize window
SUPER + 1..0             workspace 1..10
SUPER + SHIFT + 1..0     send window to workspace
SUPER + S / SHIFT + S    scratchpad / send to scratchpad
SUPER + W                random wallpaper (colours follow it)
SUPER + SHIFT + W        wallpaper picker
SUPER + ALT + W          next wallpaper
SUPER + L                lock
SUPER + SHIFT + E        log out
SUPER + SHIFT + R        reload Hyprland
SUPER + SHIFT + B        restart the bar
SUPER + SHIFT + C        colour picker
SUPER + SHIFT + D        health check
SUPER + ALT + K          on-screen keyboard
SUPER + ALT + R          screen recording on/off
SUPER + ALT + N          night light
SUPER + N / SHIFT + N    dismiss notification / all
Print / SHIFT + Print    screenshot region / screen
KEYS
