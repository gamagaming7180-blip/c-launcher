-- Window and layer rules.

-- Ignore maximize requests from apps (stops windows fighting the tiler)
hl.window_rule({
    name  = "suppress-maximize",
    match = { class = ".*" },
    suppress_event = "maximize",
})

-- XWayland drag glitch fix
hl.window_rule({
    name  = "fix-xwayland-drags",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})

-- Small utility windows float
hl.window_rule({
    name  = "float-utils",
    match = { class = "^(pavucontrol|org.pulseaudio.pavucontrol|nm-connection-editor|blueman-manager|polkit-gnome-authentication-agent-1|org.kde.polkit-kde-authentication-agent-1|xdg-desktop-portal-gtk|org.gnome.Calculator)$" },
    float = true,
})

-- Don't let the screen sleep while something is fullscreen (video, games)
hl.window_rule({
    name  = "idle-inhibit-fullscreen",
    match = { class = ".*", fullscreen = true },
    idle_inhibit = "fullscreen",
})

-- Skip blur/shadow/animation work on things that don't need it
hl.window_rule({
    name  = "no-blur-fullscreen",
    match = { fullscreen = true },
    no_blur = true,
})

-- System monitor popup (SUPER + G, or click CPU/RAM in the bar): float it
-- just under the bar at the top right.
hl.window_rule({
    name  = "sysmon-popup",
    match = { class = "^sysmon$" },
    float = true,
    move  = "monitor_w-window_w-10 52",
})

---------------------------------------------------------------- layers
-- Blur only the shell surfaces. ignore_alpha stops blur leaking through
-- the transparent parts of the bar/launcher.
hl.layer_rule({ name = "blur-waybar", match = { namespace = "waybar" },        blur = true, ignore_alpha = 0.3 })
hl.layer_rule({ name = "blur-rofi",   match = { namespace = "rofi" },          blur = true, ignore_alpha = 0.3, animation = "slide top" })
hl.layer_rule({ name = "blur-mako",   match = { namespace = "notifications" }, blur = true, ignore_alpha = 0.3, animation = "slide right" })
