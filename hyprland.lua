-- ~/.config/hypr-rice/hyprland.lua  (started with: Hyprland -c this file)
-- Hyprland 0.55+ Lua config. Each require() runs in its own scope, so an
-- error in one module will not stop the others from loading.

-- Monitors: preferred mode, auto position, auto scale.
-- Pin your refresh rate if "preferred" is not what you want, e.g.
--   hl.monitor({ output = "eDP-1", mode = "1920x1080@144", position = "0x0", scale = 1 })
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = "1.20",
})

require("modules/env")
require("modules/appearance")
require("modules/animations")
require("modules/input")
require("modules/binds")
require("modules/rules")
require("modules/autostart")

-- hypr-rice-update: control panel, wallpaper colours, touch, night light.
-- Delete this line (and modules/update.lua) to undo.
pcall(require, "modules/update")
