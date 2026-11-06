-- Window and layer rules. Each risky rule goes through safe(), so a rule name your Hyprland build
-- doesn't know only disables that one rule instead of the whole file.

local function safe(fn, ...) local ok, err = pcall(fn, ...); if not ok then print("vesper rules: " .. tostring(err)) end end

-- Ignore maximize requests from apps (stops windows fighting the tiler)
safe(hl.window_rule, {
    name  = "suppress-maximize",
    match = { class = ".*" },
    suppress_event = "maximize",
})

-- XWayland drag glitch fix
safe(hl.window_rule, {
    name  = "fix-xwayland-drags",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})

-- Small utility windows float
safe(hl.window_rule, {
    name  = "float-utils",
    match = { class = "^(pavucontrol|org.pulseaudio.pavucontrol|nm-connection-editor|blueman-manager|polkit-gnome-authentication-agent-1|org.kde.polkit-kde-authentication-agent-1|xdg-desktop-portal-gtk|org.gnome.Calculator|org.gnome.Loupe|imv|mpv)$" },
    float = true,
})

-- File dialogs and browser pop-ups float instead of tiling
safe(hl.window_rule, {
    name  = "float-dialogs",
    match = { title = "^(Open File|Open Folder|Save As|Save File|Choose .*|File Upload|Select .*)$" },
    float = true,
})

-- Picture-in-picture floats and stays on top
safe(hl.window_rule, {
    name  = "pip-float",
    match = { title = "^(Picture-in-Picture|Picture in picture)$" },
    float = true,
    pin   = true,
})

-- Don't let the screen sleep while something is fullscreen (video, games)
safe(hl.window_rule, {
    name  = "idle-inhibit-fullscreen",
    match = { class = ".*", fullscreen = true },
    idle_inhibit = "fullscreen",
})

-- Skip blur/shadow work on fullscreen windows
safe(hl.window_rule, {
    name  = "no-blur-fullscreen",
    match = { fullscreen = true },
    no_blur = true,
})

-- System monitor popup (SUPER + G, or click CPU/RAM in the bar): float it just under the bar, top right.
safe(hl.window_rule, {
    name  = "sysmon-popup",
    match = { class = "^sysmon$" },
    float = true,
    move  = "monitor_w-window_w-12 52",
})

---------------------------------------------------------------- layers
-- Blur only the shell surfaces. ignore_alpha stops blur leaking through the transparent gaps between capsules.
safe(hl.layer_rule, { name = "blur-waybar", match = { namespace = "waybar" },        blur = true, ignore_alpha = 0.3 })
safe(hl.layer_rule, { name = "blur-rofi",   match = { namespace = "rofi" },          blur = true, ignore_alpha = 0.3, animation = "popin 92%" })
safe(hl.layer_rule, { name = "blur-mako",   match = { namespace = "notifications" }, blur = true, ignore_alpha = 0.3, animation = "slide right" })
