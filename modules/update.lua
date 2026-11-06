-- Loaded from the bottom of hyprland.lua. Every part is wrapped in pcall, so a wrong option name
-- only disables that one part. To remove it: delete this file and the "modules/update" line in hyprland.lua.
-- (Border / glow colours now come from modules/appearance.lua, which reads generated/colors.lua.)

local rice = os.getenv("HOME") .. "/.config/hypr-rice"
local mod  = "SUPER"

-- Touchscreen: map touch input to the screen. Skipped if your modules/input.lua already sets touchdevice.
pcall(function()
    local f = io.open(rice .. "/modules/input.lua", "r")
    local txt = f and f:read("*a") or ""
    if f then f:close() end
    if not txt:find("touchdevice", 1, true) then
        hl.config({ input = { touchdevice = { enabled = true, output = "[[Auto]]" } } })
    end
end)

-- SUPER + A = control panel, SUPER + SHIFT + W = wallpaper picker, SUPER + ALT + W = next wallpaper,
-- SUPER + ALT + N = night light
pcall(function()
    hl.bind(mod .. " + A",              hl.dsp.exec_cmd(rice .. "/scripts/panel-toggle.sh"))
    hl.bind(mod .. " + SHIFT + W",      hl.dsp.exec_cmd(rice .. "/scripts/wallpaper.sh pick"))
    hl.bind(mod .. " + ALT + W",        hl.dsp.exec_cmd(rice .. "/scripts/wallpaper.sh next"))
    hl.bind(mod .. " + ALT + N",        hl.dsp.exec_cmd(rice .. "/scripts/nightlight.sh toggle"))
end)

-- Night light schedule (does nothing until you turn "Auto" on in the panel)
pcall(function()
    hl.on("hyprland.start", function()
        hl.exec_cmd(rice .. "/scripts/nightlight.sh daemon")
    end)
end)

-- Blur behind the panel card only (the transparent rest of its layer is left alone)
pcall(function()
    hl.layer_rule({ name = "blur-rice-panel", match = { namespace = "rice-panel" }, blur = true, ignore_alpha = 0.3 })
end)

-- Keep the panel loaded so it opens instantly (about 80 MB of RAM).
pcall(function()
    hl.on("hyprland.start", function()
        hl.exec_cmd(rice .. "/scripts/panel-toggle.sh --hidden")
    end)
end)
