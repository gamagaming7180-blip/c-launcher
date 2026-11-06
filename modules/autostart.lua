-- Everything here is event-driven (no polling daemons).
local rice = os.getenv("HOME") .. "/.config/hypr-rice"

hl.on("hyprland.start", function()
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
    hl.exec_cmd("systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")

    hl.exec_cmd("hyprpaper -c " .. rice .. "/hyprpaper.conf")                 -- wallpaper
    hl.exec_cmd("waybar -c " .. rice .. "/waybar/config.jsonc -s " .. rice .. "/waybar/style.css")                    -- bar
    hl.exec_cmd("mako -c " .. rice .. "/mako/config")                      -- notifications
    hl.exec_cmd("hypridle -c " .. rice .. "/hypridle.conf")                  -- dim -> lock -> screen off -> suspend
    hl.exec_cmd("hyprpolkitagent")           -- auth prompts (systemd user service also works)

    -- Clipboard history (text + images). Pick with SUPER + V.
    hl.exec_cmd("wl-paste --type text  --watch cliphist store")
    hl.exec_cmd("wl-paste --type image --watch cliphist store")

    -- GTK apps follow the dark look (harmless if gsettings or the icon theme is missing)
    hl.exec_cmd("gsettings set org.gnome.desktop.interface color-scheme prefer-dark")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface icon-theme Papirus-Dark")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-theme Bibata-Modern-Ice")

    -- 2-in-1: rotate the screen with the accelerometer, if iio-hyprland is installed
    -- disabled by vesper-touch fix (the daemon rotates the screen): hl.exec_cmd("command -v iio-hyprland >/dev/null && iio-hyprland")
end)
