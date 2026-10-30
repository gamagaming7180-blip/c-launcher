-- Added by hypr-rice-update. Loaded from the bottom of hyprland.lua.
-- Every part is wrapped in pcall, so a wrong option name only disables that one part.
-- To remove the whole update: delete this file and the "modules/update" line in hyprland.lua.

local rice = os.getenv("HOME") .. "/.config/hypr-rice"
local mod  = "SUPER"

-- 1) Window border accents follow the wallpaper (colours are written by scripts/wallcolors.py)
pcall(function()
    local ok, c = pcall(dofile, rice .. "/generated/colors.lua")
    if ok and type(c) == "table" and c.accent and c.accent2 then
        hl.config({
            general = {
                col = {
                    active_border = { colors = { "rgba(" .. c.accent .. "ee)", "rgba(" .. c.accent2 .. "ee)" }, angle = 45 },
                },
            },
        })
    end
end)

-- 2) Touchscreen: map touch input to the screen. Skipped if your modules/input.lua already
--    sets touchdevice, so your own touch settings always win.
pcall(function()
    local f = io.open(rice .. "/modules/input.lua", "r")
    local txt = f and f:read("*a") or ""
    if f then f:close() end
    if not txt:find("touchdevice", 1, true) then
        hl.config({ input = { touchdevice = { enabled = true, output = "[[Auto]]" } } })
    end
end)

-- 3) Binds: SUPER + A = control panel, SUPER + SHIFT + W = wallpaper picker,
--    SUPER + ALT + W = next wallpaper
pcall(function()
    hl.bind(mod .. " + A",              hl.dsp.exec_cmd(rice .. "/scripts/panel-toggle.sh"))
    hl.bind(mod .. " + SHIFT + W",      hl.dsp.exec_cmd(rice .. "/scripts/wallpaper.sh pick"))
    hl.bind(mod .. " + ALT + W",        hl.dsp.exec_cmd(rice .. "/scripts/wallpaper.sh next"))
    hl.bind(mod .. " + ALT + N",        hl.dsp.exec_cmd(rice .. "/scripts/nightlight.sh toggle"))   -- night light
end)

-- 3b) Night light schedule (does nothing until you turn "Auto" on in the panel)
pcall(function()
    hl.on("hyprland.start", function()
        hl.exec_cmd(rice .. "/scripts/nightlight.sh daemon")
    end)
end)

-- 4) Blur behind the panel card only (the transparent rest of its layer is left alone)
pcall(function()
    hl.layer_rule({ name = "blur-rice-panel", match = { namespace = "rice-panel" }, blur = true, ignore_alpha = 0.3 })
end)

-- hypr-rice panel v3: keep the panel loaded so it opens instantly (about 80 MB of RAM).
-- Delete this block to go back to starting it on first click.
pcall(function()
    hl.on("hyprland.start", function()
        hl.exec_cmd(os.getenv("HOME") .. "/.config/hypr-rice/scripts/panel-toggle.sh --hidden")
    end)
end)
