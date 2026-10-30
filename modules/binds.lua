-- Keybinds. SUPER is the main modifier.
-- Binds must never block: external work goes through hl.dsp.exec_cmd.

local mod = "SUPER"
local rice = os.getenv("HOME") .. "/.config/hypr-rice"

local terminal    = "kitty --config " .. rice .. "/kitty/kitty.conf"
local fileManager = "thunar"
local browser     = "firefox"
local rofi        = "rofi -config " .. rice .. "/rofi/config.rasi -theme " .. rice .. "/rofi/catppuccin.rasi"
local launcher    = rofi .. " -show drun"
local lock        = "hyprlock -c " .. rice .. "/hyprlock.conf"

---------------------------------------------------------------- apps
hl.bind(mod .. " + Return",        hl.dsp.exec_cmd(terminal))
hl.bind(mod .. " + SPACE",         hl.dsp.exec_cmd(launcher))
hl.bind(mod .. " + E",             hl.dsp.exec_cmd(fileManager))
hl.bind(mod .. " + B",             hl.dsp.exec_cmd(browser))
hl.bind(mod .. " + V",             hl.dsp.exec_cmd("cliphist list | " .. rofi .. " -dmenu -p ' Clipboard' | cliphist decode | wl-copy"))
hl.bind(mod .. " + Tab",           hl.dsp.exec_cmd(rofi .. " -show window"))
hl.bind(mod .. " + G",             hl.dsp.exec_cmd(rice .. "/scripts/sysmon-toggle.sh"))   -- system monitor

---------------------------------------------------------------- session
hl.bind(mod .. " + L",             hl.dsp.exec_cmd(lock))
hl.bind(mod .. " + SHIFT + E",     hl.dsp.exec_cmd("command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"))
hl.bind(mod .. " + SHIFT + R",     hl.dsp.exec_cmd("hyprctl reload"))

---------------------------------------------------------------- windows
hl.bind(mod .. " + Q",             hl.dsp.window.close())
hl.bind(mod .. " + T",             hl.dsp.window.float({ action = "toggle" }))
hl.bind(mod .. " + F",             hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }))
hl.bind(mod .. " + M",             hl.dsp.window.fullscreen({ mode = "maximized",  action = "toggle" }))
hl.bind(mod .. " + P",             hl.dsp.window.pseudo())
hl.bind(mod .. " + Y",             hl.dsp.layout("togglesplit"))

-- Focus: arrows + vim keys
hl.bind(mod .. " + left",  hl.dsp.focus({ direction = "left" }))
hl.bind(mod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mod .. " + up",    hl.dsp.focus({ direction = "up" }))
hl.bind(mod .. " + down",  hl.dsp.focus({ direction = "down" }))
hl.bind(mod .. " + H",     hl.dsp.focus({ direction = "left" }))
hl.bind(mod .. " + K",     hl.dsp.focus({ direction = "up" }))
hl.bind(mod .. " + J",     hl.dsp.focus({ direction = "down" }))
-- SUPER+L is lock, so "focus right" on the vim row is SUPER+semicolon
hl.bind(mod .. " + semicolon", hl.dsp.focus({ direction = "right" }))

-- Move windows around
hl.bind(mod .. " + SHIFT + left",  hl.dsp.window.move({ direction = "left" }))
hl.bind(mod .. " + SHIFT + right", hl.dsp.window.move({ direction = "right" }))
hl.bind(mod .. " + SHIFT + up",    hl.dsp.window.move({ direction = "up" }))
hl.bind(mod .. " + SHIFT + down",  hl.dsp.window.move({ direction = "down" }))

-- Resize (hold to repeat)
local step = 40
hl.bind(mod .. " + CTRL + left",  hl.dsp.window.resize({ x = -step, y = 0,     relative = true }), { repeating = true })
hl.bind(mod .. " + CTRL + right", hl.dsp.window.resize({ x =  step, y = 0,     relative = true }), { repeating = true })
hl.bind(mod .. " + CTRL + up",    hl.dsp.window.resize({ x = 0,     y = -step, relative = true }), { repeating = true })
hl.bind(mod .. " + CTRL + down",  hl.dsp.window.resize({ x = 0,     y =  step, relative = true }), { repeating = true })

-- Mouse: drag to move, right-drag to resize
hl.bind(mod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

---------------------------------------------------------------- workspaces
for i = 1, 10 do
    local key = i % 10   -- workspace 10 lives on the 0 key
    hl.bind(mod .. " + " .. key,           hl.dsp.focus({ workspace = i }))
    hl.bind(mod .. " + SHIFT + " .. key,   hl.dsp.window.move({ workspace = i }))
end

hl.bind(mod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mod .. " + mouse_up",   hl.dsp.focus({ workspace = "e-1" }))
hl.bind(mod .. " + ALT + right", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mod .. " + ALT + left",  hl.dsp.focus({ workspace = "e-1" }))

-- Scratchpad
hl.bind(mod .. " + S",         hl.dsp.workspace.toggle_special("magic"))
hl.bind(mod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "special:magic" }))

---------------------------------------------------------------- screenshots
local shots = "$HOME/Pictures/Screenshots"
hl.bind("Print",
    hl.dsp.exec_cmd("mkdir -p " .. shots .. " && grim -g \"$(slurp -b 1e1e2e99 -c cba6f7ff -w 2)\" - | tee " .. shots .. "/$(date +%F_%H-%M-%S).png | wl-copy && notify-send -t 2000 'Screenshot' 'Region copied + saved'"))
hl.bind("SHIFT + Print",
    hl.dsp.exec_cmd("mkdir -p " .. shots .. " && grim - | tee " .. shots .. "/$(date +%F_%H-%M-%S).png | wl-copy && notify-send -t 2000 'Screenshot' 'Screen copied + saved'"))

---------------------------------------------------------------- notifications / wallpaper
hl.bind(mod .. " + N",         hl.dsp.exec_cmd("makoctl dismiss"))
hl.bind(mod .. " + SHIFT + N", hl.dsp.exec_cmd("makoctl dismiss --all"))
hl.bind(mod .. " + W",         hl.dsp.exec_cmd(rice .. "/scripts/wallpaper.sh"))

---------------------------------------------------------------- media keys (work on lock screen)
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),      { locked = true, repeating = true })
hl.bind("XF86AudioMute",        hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),     { locked = true })
hl.bind("XF86AudioMicMute",     hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"),   { locked = true })
hl.bind("XF86MonBrightnessUp",  hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"),                  { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown",hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"),                  { locked = true, repeating = true })
hl.bind("XF86AudioNext",  hl.dsp.exec_cmd("playerctl next"),       { locked = true })
hl.bind("XF86AudioPrev",  hl.dsp.exec_cmd("playerctl previous"),   { locked = true })
hl.bind("XF86AudioPlay",  hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })

-- HYPR_RICE_SCREEN_RECORDING_V1_BEGIN
-- SUPER+ALT+R toggles screen recording; the top Waybar button does the same.
hl.bind(mod .. " + ALT + R", hl.dsp.exec_cmd(rice .. "/scripts/screen-record-toggle.sh toggle"))
-- HYPR_RICE_SCREEN_RECORDING_V1_END
