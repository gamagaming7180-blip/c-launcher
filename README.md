# C Launcher — Complete System Blueprint & Architecture

## 1. Clean File Tree
```
aod.py
generated/colors.json
generated/colors.lua
generated/current-wallpaper
generated/nightlight.conf
generated/nightlight.lock
hypridle.conf
hyprland.lua
hyprlock.conf
hyprpaper.conf
kitty/kitty.conf
mako/config
modules/animations.lua
modules/appearance.lua
modules/appearance.lua.bak
modules/autostart.lua
modules/binds.lua
modules/env.lua
modules/input.lua
modules/rules.lua
modules/update.lua
rofi/catppuccin.rasi
rofi/config.rasi
scripts/fingerprint-lock.py
scripts/fingerprint.sh
scripts/launcher_theme.py
scripts/lock-quip.sh
scripts/media-card.py
scripts/media-controls.py
scripts/media-equalizer.py
scripts/mediaspec.py
scripts/nightlight.sh
scripts/osd.py
scripts/panel-toggle.sh
scripts/panel.py
scripts/panelcore.py
scripts/power-menu.sh
scripts/restart-rice-waybar.sh
scripts/screen-record-toggle.sh
scripts/screen-record-toggle.sh.bak
scripts/sysmon-toggle.sh
scripts/sysmon.py
scripts/wallcolors.py
scripts/wallpaper.sh
wallpaper-dirs
waybar/colors.css
waybar/config.jsonc
waybar/config.jsonc.bak
waybar/style.css
waybar/update.css
```

## File: `hyprland.lua`
```
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

```

## File: `modules/binds.lua`
```
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

```

## File: `modules/autostart.lua`
```
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
end)

```

## File: `scripts/panel-toggle.sh`
```
#!/usr/bin/env bash
# Click the clock (or SUPER + A): show / hide the control panel.
# The panel keeps running in the background (about 80 MB) so it opens instantly; this just signals it.
#   panel-toggle.sh             toggle
#   panel-toggle.sh --restart   kill and start a fresh panel (if it ever misbehaves)
RICE="$HOME/.config/hypr-rice"
LOCK="${XDG_RUNTIME_DIR:-/tmp}/hypr-rice-panel.lock"
LOG="$HOME/.cache/hypr-rice-panel.log"
mkdir -p "$HOME/.cache"
[ -f "$LOG" ] && [ "$(stat -c %s "$LOG" 2>/dev/null || echo 0)" -gt 200000 ] && : > "$LOG"

if [ "${1:-}" = "--restart" ]; then
    pkill -f '^(\S*/)?python3?([.0-9]+)? (\S*/)?scripts/panel\.py' 2>/dev/null
    sleep 0.4
fi

pid="$(cat "$LOCK" 2>/dev/null)"
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q 'panel\.py'; then
    kill -USR1 "$pid"
    exit 0
fi
[ -n "$pid" ] && rm -f "$LOCK"   # stale lock from a dead panel

# gtk-layer-shell must be loaded before libwayland-client; panel.py also does this itself.
[ -e /usr/lib/libgtk-layer-shell.so ] && export LD_PRELOAD="/usr/lib/libgtk-layer-shell.so${LD_PRELOAD:+:$LD_PRELOAD}"
exec python3 "$RICE/scripts/panel.py" "$@" 2>>"$LOG"

```

## File: `scripts/panel.py`
```
#!/usr/bin/env python3
"""panel v4: quick-settings card that drops from the top when you click the clock (or SUPER + A).

Design notes
  * A fresh small window is built on every open and destroyed on close. v3 hid and re-showed one
    big window, and the second show() hung inside gtk-layer-shell. Never re-mapping avoids that.
  * No full-screen backdrop, no revealers, no size-interpolating stacks: fewer moving parts.
  * All slow work (nmcli, bluetoothctl, wpctl ...) runs in worker threads; the UI only paints results.
  * The process stays alive in the background (signal toggles it); a watchdog logs a stack dump if the
    main loop ever stalls.

  panel.py            toggle (open if closed)
  panel.py --hidden   start in the background without opening
Needs python-gobject gtk3 gtk-layer-shell. Everything else is optional; its control hides if missing.
"""
import ctypes
import datetime
import math
import fcntl
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

WINDOWED = os.environ.get("HYPR_PANEL_WINDOWED") == "1"       # development: plain window, no layer-shell
try:   # gtk-layer-shell must load before libwayland-client
    ctypes.CDLL("libgtk-layer-shell.so.0", mode=ctypes.RTLD_GLOBAL)
except OSError:
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panelcore as pc  # noqa: E402

try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import GLib, Gtk, Gdk, Pango  # noqa: E402
    GtkLayerShell = None
    if not WINDOWED:
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import GtkLayerShell  # noqa: E402
except (ImportError, ValueError):
    print("Panel needs: sudo pacman -S python-gobject gtk3 gtk-layer-shell", file=sys.stderr)
    pc.notify("Panel", "Needs python-gobject gtk3 gtk-layer-shell")
    sys.exit(1)

LOCK = os.path.join(pc.RUNTIME, "hypr-rice-panel.lock")
# Where the clock pill sits in your bar (pixels from the top of the screen, horizontally centred) and where the card
# lands. The droplet starts exactly on the pill. If it starts in the wrong spot, change these three numbers.
PILL_W, PILL_H, PILL_Y = 165, 30, 6
CARD_TOP = 56
GLASS = 0.88                 # how solid the glass is: 0 = clear, 1 = opaque (about 0.30 if text is hard to read)
IDLE_CLOSE_S = 5.0           # the panel closes itself after this many seconds with no activity on it
ACT = [time.monotonic()]     # last activity time


def poke():
    ACT[0] = time.monotonic()
RICE = pc.RICE
AOD = os.path.join(RICE, "aod.py")


def aod_on():
    try:
        os.kill(int(open("/tmp/hypr-aod.pid").read()), 0)
        return os.path.exists("/tmp/hypr-aod-sticky")
    except Exception:
        return False


G = dict(  # Nerd Font glyphs; swap any one here if it renders wrong
    vol="\U000f057e", mute="\U000f075f", bri="\U000f00e0", wifi="\U000f0928", wifi_off="\U000f092d",
    bt="\U000f00af", bt_on="\U000f00b1", bt_off="\U000f00b2", hotspot="\U000f0003", plane="\U000f001d",
    dnd="\U000f009b", night="\U000f0594", mic="\U000f036c", micoff="\U000f036d", prof="\U000f04c5",
    coffee="\U000f0176", rec="\U000f044a", aod="\U000f0150", prev="\U000f04ae", next="\U000f04ad", play="\U000f040a",
    pause="\U000f03e4", bat="\U000f0079", lock="\U000f033e", sleep="\U000f0904", logout="\U000f0343",
    reboot="\U000f0709", off="\U000f0425", speaker="\U000f04c3", headphones="\U000f02cb", back="\U000f004d",
    scan="\U000f0450", forget="\U000f0156", lockico="\U000f033e")
BARS = ["\U000f091f", "\U000f0922", "\U000f0925", "\U000f0928"]

CSS = """
.rp, .rp * { font-family: "JetBrainsMono Nerd Font", "Noto Sans", sans-serif; font-size: 12px; }
window.rp { background-color: transparent; }
.rp .cardflat { background-color: transparent; border: 1px solid transparent; border-radius: 24px; padding: 16px; }
.rp .card { background-color: alpha(@base, 0.58); border: 1px solid alpha(@text, 0.12); border-radius: 24px;
            padding: 16px; }
.rp button { background-image: none; background-color: transparent; box-shadow: none; text-shadow: none;
             border: 1px solid transparent; border-radius: 14px; padding: 0; margin: 0; min-height: 0;
             min-width: 0; color: @text; outline-style: none; }
.rp button:disabled { opacity: 0.4; }
.rp .time { font-size: 32px; font-weight: 800; }
.rp .date { color: @subtext; font-size: 11px; font-weight: 600; }
.rp .pill { background-color: alpha(@text, 0.09); border-radius: 12px; padding: 3px 10px; font-weight: 700; }
.rp .pill.low { background-color: alpha(@red, 0.30); color: @red; }
.rp .pill.chg { background-color: alpha(@accent2, 0.28); color: @accent2; }
.rp .tile { background-color: alpha(@text, 0.07); border: 1px solid alpha(@text, 0.06); border-radius: 18px;
            padding: 10px 11px; }
.rp .tile:hover { background-color: alpha(@text, 0.12); }
.rp .tile.on { background-color: alpha(@accent, 0.30); border-color: alpha(@accent, 0.55); }
.rp .tico { font-size: 18px; color: @subtext; }
.rp .tile.on .tico { color: @text; }
.rp .tname { font-weight: 700; font-size: 12px; }
.rp .tsub { color: @subtext; font-size: 10px; }
.rp .tile.on .tsub { color: alpha(@text, 0.8); }
.rp .chev { background-color: alpha(@text, 0.10); border-radius: 11px; font-size: 13px; padding: 1px 8px;
            margin: 6px; color: @text; }
.rp .chev:hover { background-color: alpha(@text, 0.2); }
.rp .srow { background-color: alpha(@text, 0.07); border-radius: 18px; padding: 4px 12px 4px 6px; }
.rp .sico { font-size: 16px; padding: 4px 9px; border-radius: 13px; }
.rp .sico:hover { background-color: alpha(@text, 0.12); }
.rp .sval { color: @subtext; font-size: 10px; font-weight: 700; min-width: 44px; }
.rp scale trough { min-height: 6px; border-radius: 3px; background-color: alpha(@text, 0.18); border: none;
                   background-image: none; }
.rp scale highlight { background-color: @accent; border-radius: 3px; border: none; background-image: none; }
.rp scale slider { min-width: 16px; min-height: 16px; margin: -5px; border-radius: 8px; border: none;
                   background-color: @text; background-image: none; box-shadow: 0 1px 3px rgba(0,0,0,0.5); }
.rp .media { background-color: alpha(@text, 0.07); border-radius: 18px; padding: 10px 12px; }
.rp .mtitle { font-weight: 800; font-size: 13px; }
.rp .msub { color: @subtext; font-size: 10px; }
.rp .ctl { border-radius: 16px; min-width: 34px; min-height: 34px; font-size: 15px; }
.rp .ctl:hover { background-color: alpha(@text, 0.12); }
.rp .ctl.play { background-color: @accent; color: @base; }
.rp .dock { background-color: alpha(@text, 0.06); border-radius: 18px; padding: 3px; }
.rp .dock button { padding: 8px 0; border-radius: 15px; font-size: 15px; }
.rp .dock button:hover { background-color: alpha(@text, 0.13); }
.rp .dock button.confirm { background-color: alpha(@red, 0.85); color: @base; font-size: 10px; font-weight: 800; }
.rp .ptitle { font-size: 16px; font-weight: 800; }
.rp .psub { color: @subtext; font-size: 11px; }
.rp .psub.err { color: @red; }
.rp .back { background-color: alpha(@text, 0.09); border-radius: 15px; min-width: 30px; min-height: 30px;
            font-size: 16px; }
.rp .back:hover { background-color: alpha(@text, 0.16); }
.rp .sect { color: @subtext; font-size: 10px; font-weight: 800; padding: 8px 4px 2px 4px; }
.rp .empty { color: @subtext; padding: 24px 0; }
.rp .row { border-radius: 14px; padding: 7px 9px; }
.rp .row:hover { background-color: alpha(@text, 0.09); }
.rp .row.active { background-color: alpha(@accent, 0.22); }
.rp .rico { color: @accent2; font-size: 17px; min-width: 26px; }
.rp .row.active .rico { color: @accent; }
.rp .rname { font-weight: 700; }
.rp .rsub { color: @subtext; font-size: 10px; }
.rp .rtag { color: @subtext; font-size: 11px; }
.rp .xbtn { color: @subtext; padding: 4px 9px; font-size: 13px; }
.rp .xbtn:hover { color: @red; background-color: alpha(@red, 0.18); }
.rp .chip { background-color: alpha(@text, 0.09); border-radius: 13px; padding: 7px 12px; font-weight: 700; }
.rp .chip:hover { background-color: alpha(@text, 0.16); }
.rp .chip.primary { background-color: alpha(@accent, 0.85); color: @base; }
.rp entry { background-color: alpha(@text, 0.10); color: @text; border: 1px solid alpha(@text, 0.14);
            border-radius: 12px; padding: 6px 10px; min-height: 20px; box-shadow: none; background-image: none; }
.rp entry:focus { border-color: @accent; }
.rp switch { background-color: alpha(@text, 0.20); background-image: none; border: none; border-radius: 14px;
             min-width: 46px; min-height: 26px; box-shadow: none; color: transparent; }
.rp switch:checked { background-color: @accent; }
.rp switch slider { background-color: @text; background-image: none; border: none; border-radius: 11px;
                    min-width: 22px; min-height: 22px; margin: 2px; box-shadow: none; }
.rp switch:checked slider { background-color: @base; }
.rp scrolledwindow, .rp viewport { background-color: transparent; }
.rp scrollbar { background-color: transparent; border: none; }
.rp scrollbar slider { background-color: alpha(@text, 0.25); border-radius: 3px; min-width: 4px; border: none;
                       margin: 0; }
/* ---- v5.1 "liquid glass": more see-through, edge highlights, tinted by the wallpaper accents ---- */
.rp label { text-shadow: 0 1px 2px rgba(0, 0, 0, 0.30); }
.rp .card { background-color: alpha(@base, %GLASS%);
            background-image: linear-gradient(to bottom right, alpha(@accent, 0.22), alpha(@accent2, 0.06), alpha(@accent, 0.14));
            border: 1px solid alpha(@text, 0.24); border-radius: 28px;
            box-shadow: inset 0 0 0 0 transparent, inset 0 -1px 0 alpha(@text, 0.06); }
.rp .tile { background-color: alpha(@text, 0.07);
            background-image: linear-gradient(to bottom, alpha(@text, 0.08), alpha(@text, 0.01));
            border: 1px solid alpha(@text, 0.17); border-radius: 20px;
            box-shadow: inset 0 0 0 0 transparent; }
.rp .tile:hover { background-color: alpha(@text, 0.16); }
.rp .tile.on { background-color: alpha(@accent, 0.34);
               background-image: linear-gradient(to bottom right, alpha(@accent, 0.48), alpha(@accent2, 0.26));
               border-color: alpha(@accent, 0.75);
               box-shadow: inset 0 0 0 0 transparent, 0 0 16px alpha(@accent, 0.30); }
.rp .srow, .rp .media, .rp .dock { background-color: alpha(@text, 0.07); border: 1px solid alpha(@text, 0.14);
                                   box-shadow: inset 0 0 0 0 transparent; }
.rp .srow { border-radius: 20px; }
.rp .dock { border-radius: 20px; }
.rp .pill { background-color: alpha(@text, 0.14); border: 1px solid alpha(@text, 0.16); }
.rp scale trough { background-color: alpha(@text, 0.24); }
.rp scale highlight { background-image: linear-gradient(to right, @accent, @accent2); }
.rp scale slider { background-color: rgba(255, 255, 255, 0.96);
                   box-shadow: 0 1px 4px rgba(0, 0, 0, 0.45), inset 0 0 0 1px rgba(255, 255, 255, 0.5); }
.rp .chip, .rp .back, .rp .chev { background-color: alpha(@text, 0.09); border: 1px solid alpha(@text, 0.14); }
.rp .chip.primary { background-image: linear-gradient(to right, alpha(@accent, 0.95), alpha(@accent2, 0.85));
                    border-color: alpha(@text, 0.25); }
.rp .row:hover { background-color: alpha(@text, 0.12); }
.rp .row.active { background-color: alpha(@accent, 0.28); border: 1px solid alpha(@accent, 0.45); }
.rp entry { background-color: alpha(@text, 0.12); border-color: alpha(@text, 0.20); }
.rp switch { background-color: alpha(@text, 0.26); }
.rp switch:checked { background-image: linear-gradient(to right, @accent, @accent2); }
.rp .netcard { background-color: alpha(@accent, 0.14); border: 1px solid alpha(@accent, 0.40); border-radius: 18px;
               padding: 10px 12px; }
.rp .netname { font-weight: 800; font-size: 14px; }
.rp .qrbox { background-color: #ffffff; border-radius: 12px; padding: 8px; }
""".replace("%GLASS%", str(GLASS))


# ------------------------------------------------------------------ tiny widget helpers
def lab(text="", cls=None, xalign=0.0, ellipsize=0):
    w = Gtk.Label(label=text)
    w.set_xalign(xalign)
    if cls:
        w.get_style_context().add_class(cls)
    if ellipsize:
        w.set_ellipsize(Pango.EllipsizeMode.END)
        w.set_max_width_chars(ellipsize)
    return w


def box(vertical=False, spacing=0, cls=None):
    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)
    if cls:
        b.get_style_context().add_class(cls)
    return b


def btn(content=None, cls="", fn=None):
    """Flat button. `content` is a text string or a widget. Always starts with no child, because some
    GTK builds pre-create an empty label that would block add()."""
    b = Gtk.Button()
    old = b.get_child()
    if old is not None:
        b.remove(old)
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.set_focus_on_click(False)
    for c in cls.split():
        b.get_style_context().add_class(c)
    if isinstance(content, str):
        b.add(lab(content, xalign=0.5))
    elif content is not None:
        b.add(content)
    if fn:
        b.connect("clicked", lambda *_: (poke(), fn()))
    return b


def setcls(w, name, on):
    (w.get_style_context().add_class if on else w.get_style_context().remove_class)(name)


def clear(c):
    for ch in c.get_children():
        c.remove(ch)
        ch.destroy()


def set_text(btn_, text):
    ch = btn_.get_child()
    if isinstance(ch, Gtk.Label):
        ch.set_text(text)


def css_provider():
    text = (pc.css_colors() + CSS).encode()
    p = Gtk.CssProvider()
    try:
        p.load_from_data(text)
        return p
    except GLib.Error:
        pass
    good = []
    for part in [r + "}" for r in (pc.css_colors() + CSS).split("}") if r.strip()]:
        t = Gtk.CssProvider()
        try:
            t.load_from_data(part.encode())
            good.append(part)
        except GLib.Error as exc:
            print("panel: skipped a CSS rule:", exc.message, file=sys.stderr)
    p = Gtk.CssProvider()
    p.load_from_data("\n".join(good).encode())
    return p


def bg(fn, then=None):
    """Run fn() in a thread, then(result) on the GTK thread."""
    def work():
        try:
            res = fn()
        except Exception as exc:
            print("panel worker error:", repr(exc), file=sys.stderr)
            res = None
        if then:
            GLib.idle_add(lambda: (then(res), False)[1])
    threading.Thread(target=work, daemon=True).start()


# netplus
def bt_glyph(icon):
    i = icon or ""
    for key, g in (("mouse", "\U000f037d"), ("keyboard", "\U000f030c"), ("phone", "\U000f011c"),
                   ("gaming", "\U000f0297"), ("joystick", "\U000f0297"), ("head", G["headphones"]),
                   ("audio", G["headphones"])):
        if key in i:
            return g
    return G["bt"]


def wifi_qr_pixbuf(ssid):
    """QR code that joins the saved network `ssid`, as a pixbuf (never left on disk), or None."""
    import re
    try:
        from gi.repository import GdkPixbuf
    except Exception:
        return None
    pw = (pc.sh(["nmcli", "-s", "-g", "802-11-wireless-security.psk", "connection", "show", "id", ssid], 5.0) or "").strip()
    esc = lambda s: re.sub(r'([\\;,:"])', r'\\\1', s)
    text = "WIFI:T:%s;S:%s;%s;" % ("WPA" if pw else "nopass", esc(ssid), ("P:" + esc(pw) + ";") if pw else "")
    path = os.path.join(pc.RUNTIME, "hypr-rice-wifi-qr.png")
    try:
        r = pc.run(["qrencode", "-t", "PNG", "-s", "6", "-m", "1", "-o", path, text], 5.0)
        if r is None or r.returncode != 0:
            return None
        pix = GdkPixbuf.Pixbuf.new_from_file(path)
        return pix
    except Exception:
        return None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def wifi_glyph(sig):
    return BARS[0 if sig < 25 else 1 if sig < 50 else 2 if sig < 75 else 3]


# ------------------------------------------------------------------ shared state (survives close/open)
class Cache:
    rec = (False, 0)
    rec_seen = 0.0
    snap = None
    wifi_nets = None
    bt_devs = None


def snapshot():
    """Everything the main page shows, gathered in parallel."""
    jobs = {"vol": pc.volume, "bri": pc.brightness, "media": pc.media}
    if pc.have("nmcli"):
        jobs.update(wifi=pc.wifi, hotspot=pc.hotspot_active)
    if pc.have("bluetoothctl"):
        jobs.update(bt=pc.bluetooth, bt_names=pc.bt_connected)
    if pc.have("rfkill"):
        jobs["plane"] = pc.airplane
    if pc.have("makoctl"):
        jobs["dnd"] = pc.dnd
    if pc.have("wpctl"):
        jobs["mic"] = pc.mic_muted
    if pc.nightlight_available():
        jobs["night"] = pc.nightlight
    if pc.have("powerprofilesctl"):
        jobs["prof"] = pc.profile
    if pc.caffeine_available():
        jobs["caff"] = pc.caffeine_on
    if pc.rec_available():
        jobs["rec"] = pc.rec_status
    if os.path.isfile(AOD):
        jobs["aod"] = aod_on
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {k: ex.submit(f) for k, f in jobs.items()}
        out = {}
        for k, f in futs.items():
            try:
                out[k] = f.result(timeout=8)
            except Exception:
                out[k] = None
    return out


# ------------------------------------------------------------------ droplet: pill -> panel
def rrect(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _ease_out(x):
    return 1 - (1 - x) ** 3


def _back(x, c=1.5):
    x -= 1
    return 1 + (c + 1) * x ** 3 + c * x ** 2


def _clamp(x):
    return max(0.0, min(1.0, x))


# ---- droplet animation (shared by panel / media card / volume pop-up) ------------------------------------------
# Phase 1: a bead of glass swells under the pill, hanging from a neck.  Phase 2: the neck thins and snaps, the bead
# drops a little.  Phase 3: the bead opens (wide, then tall, with a tiny settle) into the card.
DROP_T1, DROP_T2 = 0.30, 0.46          # end of the swell, end of the drop; the rest is the opening


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _lerp(a, b, k):
    return a + (b - a) * k


def draw_droplet(cr, t, pill_cx, pill_w, pill_h, pill_y, card, base, a1, a2, glass, radius, rd_f=18.0):
    """Quick grow: the card starts as the pill it comes from and expands to full size, contents fading in.
    Returns (x, y, w, h, r, content_alpha) so the caller can clip and fade the contents."""
    import cairo
    cx0, cy0, cw, ch = card
    e = _ease_out(_clamp(t))
    x = _lerp(pill_cx - pill_w / 2.0, cx0, e)
    y = _lerp(float(pill_y), cy0, e)
    w = _lerp(float(pill_w), cw, e)
    h = _lerp(float(pill_h), ch, e)
    r = _lerp(min(pill_h / 2.0, radius), radius, e)
    cr.save()
    rrect(cr, x, y, w, h, r)
    cr.set_source_rgba(base[0], base[1], base[2], glass)
    cr.fill_preserve()
    g = cairo.LinearGradient(x, y, x + w, y + h)                                # soft wallpaper tint
    g.add_color_stop_rgba(0.0, a1[0], a1[1], a1[2], 0.22 * (0.4 + 0.6 * e))
    g.add_color_stop_rgba(0.5, a2[0], a2[1], a2[2], 0.06 * (0.4 + 0.6 * e))
    g.add_color_stop_rgba(1.0, a1[0], a1[1], a1[2], 0.14 * (0.4 + 0.6 * e))
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, 0.12)
    cr.set_line_width(1.0)
    cr.stroke()
    cr.restore()
    return (x, y, w, h, r, _smooth((t - 0.30) / 0.70))


class Stage(Gtk.Box):
    """Fills the whole window. While animating it draws a droplet that starts on the clock pill, stretches down,
    widens and settles into the card, then fades the contents in. At rest it draws nothing special."""
    __gtype_name__ = "RiceStage"

    def __init__(self, card):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.card = card
        self.t = 0.0
        self.animating = True
        self._tick = None
        self._gen = 0

    def _rgba(self, name, fallback):
        try:
            ok, c = self.get_style_context().lookup_color(name)
            if ok:
                return c.red, c.green, c.blue
        except Exception:
            pass
        return fallback

    def do_draw(self, cr):
        if not self.animating:
            return Gtk.Box.do_draw(self, cr)
        try:
            cx, cy = self.card.translate_coordinates(self, 0, 0) or (16, CARD_TOP)
            cw, ch = self.card.get_allocated_width(), self.card.get_allocated_height()
            W = self.get_allocated_width()
            base = self._rgba("base", (0.12, 0.12, 0.18))
            a1 = self._rgba("accent", (0.8, 0.65, 0.97))
            a2 = self._rgba("accent2", (0.54, 0.7, 0.98))
            res = draw_droplet(cr, self.t, W / 2.0, PILL_W, PILL_H, PILL_Y, (cx, cy, cw, ch), base, a1, a2, GLASS, 28, 20.0)
            if res is not None and res[5] > 0.0:                   # the card is open enough: fade its contents in
                x, y, w, h, r, ca = res
                cr.save()
                rrect(cr, x, y, w, h, r)
                cr.clip()
                cr.push_group()
                Gtk.Box.do_draw(self, cr)
                cr.pop_group_to_source()
                cr.paint_with_alpha(ca)
                cr.restore()
        except Exception:
            # Drawing the animation failed: log it once, stop animating and show the plain panel instead.
            import traceback
            traceback.print_exc()
            sys.stderr.flush()
            GLib.idle_add(self._give_up)
            return Gtk.Box.do_draw(self, cr)
        return False

    def _give_up(self):
        self._gen += 1
        self.t = 1.0
        self._settle()
        return False

    def _settle(self):
        self.animating = False
        ctx = self.card.get_style_context()
        ctx.remove_class("cardflat")
        ctx.add_class("card")
        self.queue_draw()

    def run(self, mode, done=None):
        """Animate in or out. The clock is wall time, advanced both by the frame clock (smooth) and by a plain
        timer (so it can never stall if the compositor stops sending frame callbacks), plus a hard stop."""
        self._gen += 1
        gen = self._gen
        if self._tick is not None:
            self.remove_tick_callback(self._tick)
            self._tick = None
        ctx = self.card.get_style_context()
        ctx.remove_class("card")
        ctx.add_class("cardflat")                  # the droplet draws the background while it moves
        self.animating = True
        if mode == "out":
            self.t = 1.0
        else:
            self.t = 0.0
        dur = 0.26 if mode == "in" else 0.18
        t0 = time.monotonic()
        state = {"over": False}

        def finish():
            if state["over"] or gen != self._gen:
                return
            state["over"] = True
            if self._tick is not None:
                self.remove_tick_callback(self._tick)
                self._tick = None
            if mode == "in":
                self.t = 1.0
                self._settle()
            else:
                self.t = 0.0
            if done:
                try:
                    done()
                except Exception:
                    import traceback
                    traceback.print_exc()

        def advance():
            if state["over"] or gen != self._gen:
                return False
            f = _clamp((time.monotonic() - t0) / dur)
            self.t = f if mode == "in" else 1.0 - f
            self.queue_draw()
            if f >= 1.0:
                finish()
                return False
            return True

        self._tick = self.add_tick_callback(lambda _w, _c: advance())
        GLib.timeout_add(40, advance)              # fallback clock; keeps going until the animation is over
        GLib.timeout_add(int(dur * 1000) + 350, lambda: (finish(), False)[1])   # hard stop

    def _rescue(self):
        self._give_up()


# ------------------------------------------------------------------ the window
class PanelWindow(Gtk.Window):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.alive = True
        self.focused_once = False
        self.page = "main"
        self.tiles = {}
        self.touched = {}
        self.confirm_btn = None
        self.dock_icons = {}
        self.get_style_context().add_class("rp")
        self.set_title("rice-panel")
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        if WINDOWED:
            self.set_default_size(420, 700)
        else:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "rice-panel")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_exclusive_zone(self, -1)          # measure from the very top of the screen
            mode = getattr(GtkLayerShell.KeyboardMode, "ON_DEMAND", GtkLayerShell.KeyboardMode.EXCLUSIVE)
            GtkLayerShell.set_keyboard_mode(self, mode)
        self.set_size_request(452, -1)

        card = box(True, 0, "cardflat")
        card.set_margin_start(16)
        card.set_margin_end(16)
        card.set_margin_bottom(16)
        card.set_margin_top(CARD_TOP)
        self.card = card
        self.stage = Stage(card)
        self.stage.pack_start(card, True, True, 0)
        self.add(self.stage)
        self.leaving = False
        card.connect("size-allocate", lambda *_: GLib.idle_add(self.set_input_region))
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        card.pack_start(self.stack, True, True, 0)
        self.stack.add_named(self.build_main(), "main")
        self.stack.add_named(self.build_wifi(), "wifi")
        self.stack.add_named(self.build_bt(), "bt")
        self.stack.add_named(self.build_sound(), "sound")

        self.connect("key-press-event", self.on_key)
        self.connect("destroy", lambda *_: setattr(self, "alive", False))
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK)
        self.connect("motion-notify-event", lambda *_: poke() or False)
        self.last_pos = None
        poke()
        self.stage.show_all()
        self.tick()
        if Cache.snap:
            self.apply(Cache.snap)
        self.timer = GLib.timeout_add_seconds(2, self.poll)
        GLib.timeout_add_seconds(1, lambda: (self.tick(), self.alive)[1])
        GLib.timeout_add(400, self.idle_check)
        self.refresh()

    # ---- window behaviour
    def on_key(self, _w, ev):
        poke()
        if ev.keyval == Gdk.KEY_Escape:
            if self.page != "main":
                self.go("main")
            else:
                self.ctl.close()
            return True
        return False

    def idle_check(self):
        """Close after IDLE_CLOSE_S without a click, key, slider move or pointer movement over the panel."""
        if not self.alive or self.leaving:
            return False
        gw = self.get_window()
        if gw is not None:
            try:
                ptr = self.get_display().get_default_seat().get_pointer()
                _w, x, y, mask = gw.get_device_position(ptr)
                if (x, y) != self.last_pos or mask & Gdk.ModifierType.BUTTON1_MASK:
                    poke()
                self.last_pos = (x, y)
            except Exception:
                pass
        if time.monotonic() - ACT[0] > IDLE_CLOSE_S:
            self.ctl.close()
            return False
        return True

    def set_input_region(self):
        """Only the card takes clicks, so the bar (and the clock pill) stay clickable around it."""
        if WINDOWED or not self.alive:
            return False
        try:
            import cairo
            gw = self.get_window()
            a = self.card.get_allocation()
            if gw is not None and a.width > 1:
                gw.input_shape_combine_region(cairo.Region(cairo.RectangleInt(a.x, a.y, a.width, a.height)), 0, 0)
        except Exception:
            pass
        return False

    def animate_in(self):
        self.stage.run("in")

    def animate_out(self):
        if self.leaving or not self.alive:
            return
        self.leaving = True
        self.stage.run("out", lambda: GLib.idle_add(lambda: (self.destroy(), False)[1]))

    def go(self, name):
        if self.page == "bt":
            self.bt_scan_stop()
        self.page = name
        self.stack.set_visible_child_name(name)
        if name == "wifi":
            self.wifi_refresh(rescan=True)
        elif name == "bt":
            self.bt_refresh()
        elif name == "sound":
            self.sound_refresh()
        else:
            self.refresh()

    def recent(self, key, secs=1.5):
        return time.monotonic() - self.touched.get(key, 0) < secs

    # ---- main page
    def build_main(self):
        m = box(True, 12)
        head = box(False, 8)
        col = box(True)
        self.l_time, self.l_date = lab("", "time"), lab("", "date")
        col.pack_start(self.l_time, False, False, 0)
        col.pack_start(self.l_date, False, False, 0)
        self.l_bat = lab("", "pill", xalign=0.5)
        self.l_bat.set_valign(Gtk.Align.CENTER)
        head.pack_start(col, True, True, 0)
        head.pack_end(self.l_bat, False, False, 0)
        m.pack_start(head, False, False, 0)

        specs = []
        if pc.have("nmcli"):
            specs += [("wifi", G["wifi"], "Wi-Fi", self.t_wifi, "wifi"), ("hotspot", G["hotspot"], "Hotspot", self.t_hotspot, None)]
        if pc.have("bluetoothctl"):
            specs.append(("bt", G["bt"], "Bluetooth", self.t_bt, "bt"))
        if pc.have("rfkill"):
            specs.append(("plane", G["plane"], "Airplane", self.t_plane, None))
        if pc.have("makoctl"):
            specs.append(("dnd", G["dnd"], "Do not disturb", lambda: self.act("dnd", pc.toggle_dnd), None))
        if pc.have("wpctl"):
            specs.append(("mic", G["mic"], "Mic", lambda: self.act("mic", pc.toggle_mic), None))
        if pc.nightlight_available():
            specs.append(("night", G["night"], "Night light", lambda: self.act("night", pc.toggle_nightlight), None))
        if pc.have("powerprofilesctl"):
            specs.append(("prof", G["prof"], "Power mode", lambda: self.act("prof", pc.cycle_profile), None))
        if pc.caffeine_available():
            specs.append(("caff", G["coffee"], "Stay awake", self.t_caff, None))
        if pc.rec_available():
            specs.append(("rec", G["rec"], "Screen record", self.t_rec, None))
        if os.path.isfile(AOD):
            specs.append(("aod", G["aod"], "Always-on", self.t_aod, None))
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_column_homogeneous(True)
        for i, (key, icon, name, fn, page) in enumerate(specs):
            grid.attach(self.make_tile(key, icon, name, fn, page), i % 3, i // 3, 1, 1)
        if specs:
            m.pack_start(grid, False, False, 0)

        self.vol = self.make_slider(G["vol"], 0, 150, self.on_vol, self.on_mute)
        m.pack_start(self.vol["row"], False, False, 0)
        self.bri = None
        if pc.have("brightnessctl"):
            self.bri = self.make_slider(G["bri"], 1, 100, self.on_bri)
            m.pack_start(self.bri["row"], False, False, 0)
        self.vol["row"].set_visible(pc.have("wpctl"))
        self.nl = None
        if pc.nightlight_available():
            self.nl = self.make_slider(G["night"], 2500, 6500, self.on_warmth, None, "{:.0f}K")
            self.nl_is_auto = False
            self.nl_auto = None
            if not pc.NL_NATIVE:
                self.nl_auto = btn("Auto", "chip", self.on_night_auto)
                self.nl["row"].pack_end(self.nl_auto, False, False, 4)
            m.pack_start(self.nl["row"], False, False, 0)

        self.rec_region = False
        self.rec_audio = ""                                   # "" | "mic" | "sys" | "both"
        self.rec_row = None
        if pc.rec_available():
            self.rec_row = box(False, 6)
            self.chip_region = btn("Region", "chip", self.on_rec_region)
            self.chip_region.set_sensitive(pc.have("slurp"))
            self.chips_audio = {k: btn(t, "chip", (lambda k=k: self.on_rec_audio(k)))
                                for k, t in (("mic", "Mic"), ("sys", "Sound"), ("both", "Both"))}
            self.rec_row.pack_start(lab(G["rec"], "psub"), False, False, 4)
            self.rec_row.pack_start(self.chip_region, False, False, 0)
            for c in self.chips_audio.values():
                self.rec_row.pack_start(c, False, False, 0)
            m.pack_start(self.rec_row, False, False, 0)

        self.media = box(False, 10, "media")
        mc = box(True, 1)
        self.m_title, self.m_sub = lab("", "mtitle", ellipsize=22), lab("", "msub", ellipsize=28)
        mc.pack_start(self.m_title, False, False, 0)
        mc.pack_start(self.m_sub, False, False, 0)
        mc.set_valign(Gtk.Align.CENTER)
        self.media.pack_start(mc, True, True, 0)
        self.b_prev = btn(G["prev"], "ctl", lambda: self.media_cmd("previous"))
        self.b_play = btn(G["play"], "ctl play", lambda: self.media_cmd("play-pause"))
        self.b_next = btn(G["next"], "ctl", lambda: self.media_cmd("next"))
        for b in (self.b_prev, self.b_play, self.b_next):
            self.media.pack_end(b, False, False, 0)
        self.media.set_no_show_all(True)
        self.player = None
        m.pack_start(self.media, False, False, 0)

        dock = box(False, 0, "dock")
        logout = "command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch exit"
        lockcmd = f"hyprlock -c {RICE}/hyprlock.conf" if os.path.isfile(f"{RICE}/hyprlock.conf") else "hyprlock"
        for icon, cmd, confirm in ((G["lock"], lockcmd, False), (G["sleep"], "systemctl suspend", False),
                                   (G["logout"], logout, True), (G["reboot"], "systemctl reboot", True),
                                   (G["off"], "systemctl poweroff", True)):
            b = btn(icon, "", None)
            self.dock_icons[b] = icon
            b.connect("clicked", self.session_click, icon, cmd, confirm)
            dock.pack_start(b, True, True, 0)
        m.pack_start(dock, False, False, 0)
        return m

    def make_tile(self, key, icon, name, fn, page):
        ico, title, sub = lab(icon, "tico"), lab(name, "tname", ellipsize=12), lab("", "tsub", ellipsize=14)
        col = box(True, 1)
        col.pack_start(ico, False, False, 0)
        col.pack_start(title, False, False, 2)
        col.pack_start(sub, False, False, 0)
        b = btn(col, "tile", fn)
        b.set_size_request(-1, 76)
        if page:
            ov = Gtk.Overlay()
            ov.add(b)
            ch = btn("›", "chev", lambda p=page: self.go(p))
            ch.set_halign(Gtk.Align.END)
            ch.set_valign(Gtk.Align.START)
            ov.add_overlay(ch)
            widget = ov
        else:
            widget = b
        self.tiles[key] = dict(btn=b, ico=ico, sub=sub, on=False)
        return widget

    def tile(self, key, on, sub, icon=None):
        t = self.tiles.get(key)
        if not t:
            return
        t["on"] = on
        setcls(t["btn"], "on", on)
        t["sub"].set_text(sub)
        if icon:
            t["ico"].set_text(icon)

    def make_slider(self, icon, lo, hi, on_change, on_icon=None, fmt="{:.0f}%"):
        row = box(False, 0, "srow")
        b = btn(icon, "sico", on_icon)
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, 1)
        sc.set_draw_value(False)
        sc.set_hexpand(True)
        val = lab(fmt.format(lo), "sval", xalign=1.0)
        sc.connect("value-changed", lambda s: val.set_text(fmt.format(s.get_value())))
        sc.connect("change-value", lambda s, st, v: (poke(), on_change(max(lo, min(hi, v))))[1] or False)
        row.pack_start(b, False, False, 0)
        row.pack_start(sc, True, True, 4)
        row.pack_start(val, False, False, 0)
        return dict(row=row, scale=sc, btn=b)

    # ---- actions (optimistic: flip the UI now, do the work in a thread, then re-read)
    def act(self, key, fn):
        t = self.tiles.get(key)
        if t:
            self.tile(key, not t["on"], t["sub"].get_text())
        bg(fn, lambda _: self.refresh())

    def t_wifi(self):
        on = bool((Cache.snap or {}).get("wifi") and Cache.snap["wifi"][0])
        bg(lambda: pc.set_wifi(not on), lambda _: self.refresh())

    def t_bt(self):
        on = bool((Cache.snap or {}).get("bt"))
        bg(lambda: pc.set_bluetooth(not on), lambda _: self.refresh())

    def t_plane(self):
        on = bool((Cache.snap or {}).get("plane"))
        bg(lambda: pc.set_airplane(not on), lambda _: self.refresh())

    def t_hotspot(self):
        on = bool((Cache.snap or {}).get("hotspot"))
        self.tile("hotspot", not on, "Starting…" if not on else "Stopping…")

        def done(r):
            if r and not r[0]:
                pc.notify("Hotspot", r[1])
            self.refresh()
        bg(lambda: pc.hotspot_set(not on), done)

    def t_caff(self):
        on = bool((Cache.snap or {}).get("caff"))
        bg(lambda: pc.set_caffeine(not on), lambda _: self.refresh())

    def t_aod(self):
        self.ctl.close()                                      # get out of the way, then toggle the display
        pc.spawn(f"sleep 0.4; python3 {AOD} toggle")

    def on_vol(self, v):
        self.touched["vol"] = time.monotonic()
        self._debounce("vol", lambda: pc.set_volume(v))

    def on_bri(self, v):
        self.touched["bri"] = time.monotonic()
        self._debounce("bri", lambda: pc.set_brightness(v))

    def on_rec_region(self):
        self.rec_region = not self.rec_region
        setcls(self.chip_region, "primary", self.rec_region)

    def on_rec_audio(self, which):
        self.rec_audio = "" if self.rec_audio == which else which     # tap the chosen one again = no audio
        for k, c in self.chips_audio.items():
            setcls(c, "primary", self.rec_audio == k)

    def t_rec(self):
        on = bool(Cache.rec[0])
        if on:
            self.tile("rec", False, "Saving…")
            bg(pc.rec_stop, lambda _: self.refresh())
            return
        region, audio = self.rec_region, self.rec_audio
        if region:
            self.ctl.close()                                  # get out of the way so you can drag a box
            bg(lambda: pc.rec_start(True, audio))
        else:
            self.tile("rec", True, "Starting…")
            bg(lambda: pc.rec_start(False, audio), lambda _: self.refresh())

    def on_warmth(self, v):
        self.touched["warm"] = time.monotonic()
        self._debounce("warm", lambda: pc.set_warmth(v), 250)

    def on_night_auto(self):
        want = not self.nl_is_auto
        self.nl_is_auto = want
        setcls(self.nl_auto, "primary", want)
        bg(lambda: pc.set_night_auto(want), lambda _: self.refresh())

    def on_mute(self):
        bg(pc.toggle_mute, lambda _: self.refresh())

    def _debounce(self, key, fn, delay=90):
        src = getattr(self, "_deb", {})
        self._deb = src
        if key in src:
            GLib.source_remove(src[key])
        src[key] = GLib.timeout_add(delay, lambda: (bg(fn), src.pop(key, None), False)[2])

    def media_cmd(self, c):
        if self.player:
            p = self.player
            bg(lambda: pc.player_cmd(p, c), lambda _: GLib.timeout_add(250, lambda: (self.refresh(), False)[1]))

    def session_click(self, b, icon, cmd, confirm):
        if confirm and self.confirm_btn is not b:
            if self.confirm_btn is not None:
                self.reset_confirm()
            self.confirm_btn = b
            set_text(b, "Sure?")
            setcls(b, "confirm", True)
            GLib.timeout_add(2500, lambda: (self.reset_confirm(b), False)[1])
            return
        self.ctl.close()
        pc.spawn(f"sleep 0.25; {cmd}")

    def reset_confirm(self, only=None):
        b = self.confirm_btn
        if b is None or (only is not None and only is not b) or not self.alive:
            return
        self.confirm_btn = None
        setcls(b, "confirm", False)
        set_text(b, self.dock_icons.get(b, ""))

    # ---- refresh / paint
    def paint_rec(self):
        on, secs = Cache.rec
        if on and secs:
            secs += int(time.monotonic() - Cache.rec_seen)
        self.tile("rec", bool(on), (f"Recording {secs // 60}:{secs % 60:02d}" if secs else "Recording") if on else "Ready",
                  G["rec"])

    def tick(self):
        if "rec" in self.tiles and Cache.rec[0]:
            self.paint_rec()
        now = datetime.datetime.now()
        self.l_time.set_text(now.strftime("%H:%M"))
        self.l_date.set_text(now.strftime("%A, %d %B"))
        b = pc.battery()
        if b:
            self.l_bat.set_text(f"{G['bat']}  {b[0]}%" + ("  ⚡" if b[1] == "Charging" else ""))
            setcls(self.l_bat, "low", b[0] <= 20 and b[1] != "Charging")
            setcls(self.l_bat, "chg", b[1] == "Charging")
        else:
            self.l_bat.set_text("")

    def poll(self):
        if not self.alive:
            return False
        if self.page == "main":
            self.refresh()
        return True

    def refresh(self):
        if not self.alive:
            return

        def done(s):
            if s is not None and self.alive:
                Cache.snap = s
                if self.page == "main":
                    self.apply(s)
        bg(snapshot, done)

    def apply(self, s):
        v = s.get("vol")
        if v is not None and not self.recent("vol"):
            self.vol["scale"].set_value(v[0])
        if v is not None:
            set_text(self.vol["btn"], G["mute"] if v[1] else G["vol"])
        if self.bri and s.get("bri") is not None and not self.recent("bri"):
            self.bri["scale"].set_value(s["bri"])
        if self.bri:
            self.bri["row"].set_visible(s.get("bri") is not None)
        w = s.get("wifi")
        if "wifi" in self.tiles and w is not None:
            self.tile("wifi", w[0], (w[1] or "Not connected") if w[0] else "Off", G["wifi"] if w[0] else G["wifi_off"])
        if "hotspot" in self.tiles and s.get("hotspot") is not None:
            self.tile("hotspot", s["hotspot"], "On" if s["hotspot"] else "Off")
        if "bt" in self.tiles:
            names = s.get("bt_names") or []
            on = bool(s.get("bt"))
            self.tile("bt", on, (", ".join(names) if names else "On") if on else "Off",
                      G["bt_on"] if names else (G["bt"] if on else G["bt_off"]))
        r = s.get("rec")
        if "rec" in self.tiles and r is not None:
            Cache.rec, Cache.rec_seen = r, time.monotonic()
            self.paint_rec()
        for k in ("plane", "dnd", "caff", "aod"):
            if k in self.tiles and s.get(k) is not None:
                self.tile(k, bool(s[k]), "On" if s[k] else "Off")
        if "mic" in self.tiles and s.get("mic") is not None:
            self.tile("mic", not s["mic"], "Muted" if s["mic"] else "Live", G["micoff"] if s["mic"] else G["mic"])
        n = s.get("night")
        if "night" in self.tiles and n:
            self.tile("night", n["on"], f"{n['temp']}K" if n["on"] else "Off")
            if self.nl:
                if not self.recent("warm", 3.0):
                    self.nl["scale"].set_value(n["temp"])
                self.nl_is_auto = bool(n["auto"])
                if self.nl_auto:
                    setcls(self.nl_auto, "primary", self.nl_is_auto)
                    self.nl_auto.set_tooltip_text(f"{n['frm']} to {n['to']}")
        if "prof" in self.tiles and s.get("prof"):
            self.tile("prof", s["prof"] == "performance", s["prof"].replace("-", " "))
        m = s.get("media")
        self.player = m["player"] if m else None
        if m:
            self.m_title.set_text(m["title"] or "Unknown title")
            self.m_sub.set_text(m["artist"] or m["player"])
            set_text(self.b_play, G["pause"] if m["status"] == "Playing" else G["play"])
            self.media.show_all()
        else:
            self.media.hide()

    # ---- Wi-Fi page
    def page_header(self, title, sub_attr, extra=None):
        h = box(False, 8)
        h.pack_start(btn(G["back"], "back", lambda: self.go("main")), False, False, 0)
        col = box(True)
        col.pack_start(lab(title, "ptitle"), False, False, 0)
        sub = lab("", "psub", ellipsize=34)
        setattr(self, sub_attr, sub)
        col.pack_start(sub, False, False, 0)
        h.pack_start(col, True, True, 0)
        if extra is not None:
            h.pack_end(extra, False, False, 0)
        return h

    def list_area(self, attr):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(280)
        sw.set_max_content_height(340)
        sw.set_propagate_natural_height(True)
        lst = box(True, 2)
        sw.add(lst)
        setattr(self, attr, lst)
        return sw

    def row(self, icon, name, sub, tag, active, fn, extra=None):
        r = box(False, 8, "row")
        setcls(r, "active", active)
        col = box(True, 1)
        col.set_valign(Gtk.Align.CENTER)
        col.pack_start(lab(name, "rname", ellipsize=26), False, False, 0)
        if sub:
            col.pack_start(lab(sub, "rsub", ellipsize=34), False, False, 0)
        inner = box(False, 8)
        inner.pack_start(lab(icon, "rico", xalign=0.5), False, False, 0)
        inner.pack_start(col, True, True, 0)
        inner.pack_end(lab(tag, "rtag", xalign=1.0), False, False, 0)
        b = btn(inner, "", fn)
        r.pack_start(b, True, True, 0)
        if extra is not None:
            r.pack_end(extra, False, False, 0)
        return r

    def build_wifi(self):
        p = box(True, 8)
        self.wifi_sw = Gtk.Switch()
        self.wifi_sw.set_valign(Gtk.Align.CENTER)
        self.wifi_sw_id = self.wifi_sw.connect("notify::active", self.wifi_switch)
        p.pack_start(self.page_header("Wi-Fi", "w_sub", self.wifi_sw), False, False, 0)
        self.w_qr, self.w_qr_ssid = None, None
        self.w_card = box(True, 6, "netcard")
        self.w_card.set_no_show_all(True)
        p.pack_start(self.w_card, False, False, 0)
        p.pack_start(self.list_area("w_list"), False, False, 0)
        self.w_pw = box(False, 6)
        self.w_entry = Gtk.Entry()
        self.w_entry.set_visibility(False)
        self.w_entry.set_placeholder_text("Password")
        self.w_entry.connect("activate", lambda *_: self.wifi_join())
        self.w_pw.pack_start(self.w_entry, True, True, 0)
        self.w_pw.pack_start(btn("Join", "chip primary", self.wifi_join), False, False, 0)
        self.w_pw.set_no_show_all(True)
        self.w_target = None
        p.pack_start(self.w_pw, False, False, 0)
        links = box(False, 6)
        links.pack_start(btn("Rescan", "chip", lambda: self.wifi_refresh(rescan=True)), True, True, 0)
        if pc.have("nm-connection-editor"):
            links.pack_start(btn("Network editor", "chip", lambda: pc.spawn(["nm-connection-editor"])), True, True, 0)
        p.pack_start(links, False, False, 0)
        return p

    def wifi_switch(self, sw, _p):
        on = sw.get_active()
        bg(lambda: pc.set_wifi(on), lambda _: GLib.timeout_add(1200, lambda: (self.wifi_refresh(), False)[1]))

    def wifi_refresh(self, rescan=False):
        if not self.alive:
            return
        if Cache.wifi_nets is not None:
            self.wifi_paint(Cache.wifi_nets)

        def first():
            return dict(st=pc.wifi(), nets=pc.wifi_list(), saved=pc.wifi_saved(), ip=pc.wifi_ip())

        def after(r):
            if r and self.alive:
                Cache.wifi_nets = r
                self.wifi_paint(r)
        bg(first, after)
        if rescan:
            def scan():
                pc.wifi_rescan()
                time.sleep(2.5)
                return first()
            bg(scan, after)

    def wifi_paint(self, r):
        if self.page != "wifi":
            return
        st = r["st"] or (False, "")
        self.wifi_sw.handler_block(self.wifi_sw_id)
        self.wifi_sw.set_active(bool(st[0]))
        self.wifi_sw.handler_unblock(self.wifi_sw_id)
        self.w_sub.set_text((st[1] if st[1] else "Not connected") if st[0] else "Off")
        setcls(self.w_sub, "err", False)
        nets = r["nets"] if st[0] else []
        act = next((n for n in nets if n["active"]), None)
        clear(self.w_card)
        if act:
            secured = act["security"] not in ("", "--")
            if act["ssid"] != self.w_qr_ssid:
                self.w_qr = None
            self.w_card.pack_start(lab(act["ssid"], "netname", ellipsize=30), False, False, 0)
            bits = [b for b in (act["band"], "%d%% signal" % act["signal"], act["security"] if secured else "Open", r["ip"]) if b]
            self.w_card.pack_start(lab("  \u00b7  ".join(bits), "rsub", ellipsize=52), False, False, 0)
            acts = box(False, 6)
            acts.pack_start(btn("Disconnect", "chip", lambda: bg(pc.wifi_disconnect, lambda _: self.wifi_refresh())), True, True, 0)
            if pc.have("qrencode"):
                acts.pack_start(btn("Hide QR" if self.w_qr is not None else "Share", "chip",
                                    lambda s=act["ssid"]: self.wifi_share(s)), True, True, 0)
            self.w_card.pack_start(acts, False, False, 0)
            if self.w_qr is not None:
                q = box(True, 0, "qrbox")
                q.set_halign(Gtk.Align.CENTER)
                q.pack_start(Gtk.Image.new_from_pixbuf(self.w_qr), False, False, 0)
                self.w_card.pack_start(q, False, False, 0)
                self.w_card.pack_start(lab("Scan with a phone camera to join", "rsub", 0.5), False, False, 0)
            self.w_card.show()
            for c in self.w_card.get_children():
                c.show_all()
        else:
            self.w_card.hide()
        clear(self.w_list)
        if not nets:
            self.w_list.pack_start(lab("Wi-Fi is off" if not st[0] else "No networks found", "empty", 0.5), False, False, 0)
        rest = [n for n in nets if not n["active"]]
        groups = (("SAVED", [n for n in rest if n["ssid"] in r["saved"]]),
                  ("AVAILABLE", [n for n in rest if n["ssid"] not in r["saved"]]))
        for title, group in groups:
            if not group:
                continue
            self.w_list.pack_start(lab(title, "sect"), False, False, 0)
            for n in group:
                saved = n["ssid"] in r["saved"]
                secured = n["security"] not in ("", "--")
                sub = "  \u00b7  ".join(b for b in (n["band"], "%d%%" % n["signal"], "" if secured else "Open") if b)
                x = btn(G["forget"], "xbtn", lambda s=n["ssid"]: self.wifi_forget(s)) if saved else None
                self.w_list.pack_start(self.row(wifi_glyph(n["signal"]), n["ssid"], sub, G["lockico"] if secured else "", False,
                                                lambda nn=n, sv=saved: self.wifi_tap(nn, sv), x), False, False, 0)
        self.w_list.show_all()

    def wifi_share(self, ssid):
        if self.w_qr is not None:
            self.w_qr = None
            if Cache.wifi_nets is not None:
                self.wifi_paint(Cache.wifi_nets)
            return

        def done(pix):
            if not self.alive:
                return
            if pix is None:
                self.w_sub.set_text("Couldn't read this network's password")
                setcls(self.w_sub, "err", True)
                return
            self.w_qr, self.w_qr_ssid = pix, ssid
            if Cache.wifi_nets is not None:
                self.wifi_paint(Cache.wifi_nets)
        bg(lambda: wifi_qr_pixbuf(ssid), done)

    def wifi_tap(self, n, saved):
        if n["active"]:
            bg(pc.wifi_disconnect, lambda _: self.wifi_refresh())
            return
        if n["security"] in ("", "--") or saved:
            self.wifi_connect(n["ssid"], None)
        else:
            self.w_target = n["ssid"]
            self.w_entry.set_text("")
            self.w_pw.show_all()
            self.w_entry.grab_focus()
            self.w_sub.set_text(f"Password for {n['ssid']}")

    def wifi_join(self):
        if self.w_target:
            ssid, pw = self.w_target, self.w_entry.get_text()
            self.w_pw.hide()
            self.wifi_connect(ssid, pw)

    def wifi_connect(self, ssid, pw):
        self.w_sub.set_text(f"Connecting to {ssid}…")

        def done(r):
            if not self.alive:
                return
            if r and r[0]:
                pc.notify("Wi-Fi", r[1])
            elif r and r[2]:
                self.w_target = ssid
                self.w_pw.show_all()
                self.w_sub.set_text("Wrong or missing password")
                setcls(self.w_sub, "err", True)
                return
            elif r:
                self.w_sub.set_text(r[1])
                setcls(self.w_sub, "err", True)
            self.wifi_refresh()
        bg(lambda: pc.wifi_connect(ssid, pw), done)

    def wifi_forget(self, ssid):
        bg(lambda: pc.wifi_forget(ssid), lambda _: self.wifi_refresh())

    # ---- Bluetooth page
    def build_bt(self):
        p = box(True, 8)
        self.bt_sw = Gtk.Switch()
        self.bt_sw.set_valign(Gtk.Align.CENTER)
        self.bt_sw_id = self.bt_sw.connect("notify::active", self.bt_switch)
        p.pack_start(self.page_header("Bluetooth", "b_sub", self.bt_sw), False, False, 0)
        p.pack_start(self.list_area("b_list"), False, False, 0)
        links = box(False, 6)
        links.pack_start(btn("Scan", "chip", self.bt_scan), True, True, 0)
        if pc.have("blueman-manager"):
            links.pack_start(btn("More settings", "chip", lambda: pc.spawn(["blueman-manager"])), True, True, 0)
        p.pack_start(links, False, False, 0)
        self.bt_seen = set()
        self.bt_proc = None
        return p

    def bt_switch(self, sw, _p):
        on = sw.get_active()
        bg(lambda: pc.set_bluetooth(on), lambda _: GLib.timeout_add(900, lambda: (self.bt_refresh(), False)[1]))

    def bt_refresh(self):
        if not self.alive:
            return
        if Cache.bt_devs is not None:
            self.bt_paint(Cache.bt_devs)

        def get():
            return dict(on=pc.bluetooth(), devs=pc.bt_devices(self.bt_seen))

        def after(r):
            if r and self.alive:
                Cache.bt_devs = r
                self.bt_paint(r)
        bg(get, after)

    def bt_paint(self, r):
        if self.page != "bt":
            return
        self.bt_sw.handler_block(self.bt_sw_id)
        self.bt_sw.set_active(bool(r["on"]))
        self.bt_sw.handler_unblock(self.bt_sw_id)
        devs = r["devs"] if r["on"] else []
        nconn = sum(1 for d in devs if d["connected"])
        self.b_sub.set_text("Off" if not r["on"] else ("%d connected" % nconn if nconn else "Ready"))
        clear(self.b_list)
        if not devs:
            self.b_list.pack_start(lab("Bluetooth is off" if not r["on"] else "No devices. Tap Scan", "empty", 0.5), False, False, 0)
        groups = (("CONNECTED", [d for d in devs if d["connected"]]),
                  ("PAIRED", [d for d in devs if d["paired"] and not d["connected"]]),
                  ("NEARBY", [d for d in devs if not d["paired"] and not d["connected"]]))
        for title, group in groups:
            if not group:
                continue
            self.b_list.pack_start(lab(title, "sect"), False, False, 0)
            for d in group:
                sub = "Connected" if d["connected"] else "Paired" if d["paired"] else "Tap to pair"
                tag = "%s %d%%" % (G["bat"], d["battery"]) if d["battery"] is not None else ""
                x = btn(G["forget"], "xbtn", lambda m=d["mac"]: self.bt_forget(m)) if d["paired"] else None
                self.b_list.pack_start(self.row(bt_glyph(d["icon"]), d["name"], sub, tag, d["connected"],
                                                lambda dd=d: self.bt_tap(dd), x), False, False, 0)
        self.b_list.show_all()

    def bt_tap(self, d):
        mac = d["mac"]
        self.b_sub.set_text(("Disconnecting " if d["connected"] else "Connecting to ") + d["name"] + "…")

        def work():
            if d["connected"]:
                pc.run(["bluetoothctl", "disconnect", mac], 12.0)
            else:
                if not d["paired"]:
                    pc.run(["bluetoothctl", "pair", mac], 30.0)
                    pc.run(["bluetoothctl", "trust", mac], 5.0)
                pc.run(["bluetoothctl", "connect", mac], 15.0)
        bg(work, lambda _: self.bt_refresh())

    def bt_forget(self, mac):
        bg(lambda: pc.run(["bluetoothctl", "remove", mac], 6.0), lambda _: self.bt_refresh())

    def bt_scan(self):
        self.b_sub.set_text("Scanning…")

        def work():
            pc.run(["bluetoothctl", "--timeout", "8", "scan", "on"], 12.0)
            out = pc.sh(["bluetoothctl", "devices"], 4.0)
            return {l.split()[1].upper() for l in out.splitlines() if l.startswith("Device")}

        def done(macs):
            if macs:
                self.bt_seen |= macs
            self.bt_refresh()
        bg(work, done)

    def bt_scan_stop(self):
        bg(lambda: pc.run(["bluetoothctl", "scan", "off"], 3.0))

    # ---- Sound page
    def build_sound(self):
        p = box(True, 8)
        p.pack_start(self.page_header("Sound", "s_sub"), False, False, 0)
        p.pack_start(self.list_area("s_list"), False, False, 0)
        if pc.have("pavucontrol"):
            p.pack_start(btn("Volume mixer", "chip", lambda: pc.spawn(["pavucontrol"])), False, False, 0)
        return p

    def sound_refresh(self):
        def get():
            return dict(sink=pc.audio_devices("sink"), source=pc.audio_devices("source"))

        def after(r):
            if not r or not self.alive or self.page != "sound":
                return
            clear(self.s_list)
            self.s_sub.set_text("Output and input")
            for kind, title, ico in (("sink", "OUTPUT", G["speaker"]), ("source", "INPUT", G["mic"])):
                self.s_list.pack_start(lab(title, "sect"), False, False, 0)
                if not r[kind]:
                    self.s_list.pack_start(lab("None found", "empty", 0.5), False, False, 0)
                for d in r[kind]:
                    ic = G["headphones"] if "head" in d["hint"] or "bluez" in d["hint"] else ico
                    self.s_list.pack_start(self.row(ic, d["name"], "", "✓" if d["default"] else "", d["default"],
                                                    lambda dd=d: self.sound_pick(dd)), False, False, 0)
            self.s_list.show_all()
        bg(get, after)

    def sound_pick(self, d):
        bg(lambda: pc.set_default_audio(d["kind"], d["id"]), lambda _: self.sound_refresh())


# ------------------------------------------------------------------ controller (lives for the whole session)
class Controller:
    def __init__(self):
        self.win = None
        self.prov = None
        self.reload_css()
        self.colors_mtime = self._mtime()

    @staticmethod
    def _mtime():
        try:
            return os.path.getmtime(pc.COLORS_CSS)
        except OSError:
            return 0

    def reload_css(self):
        screen = Gdk.Screen.get_default()
        if self.prov:
            Gtk.StyleContext.remove_provider_for_screen(screen, self.prov)
        self.prov = css_provider()
        Gtk.StyleContext.add_provider_for_screen(screen, self.prov, Gtk.STYLE_PROVIDER_PRIORITY_USER + 100)

    def toggle(self):
        if self.win is not None:
            self.close()
        else:
            self.open()
        return True

    def open(self):
        if self.win is not None:
            return
        m = self._mtime()
        if m != self.colors_mtime:
            self.colors_mtime = m
            self.reload_css()
        self.win = PanelWindow(self)
        poke()
        self.win.show()
        self.win.animate_in()
        # if the wallpaper changed by hand, re-sample accents for next time
        bg(pc.sync_wallpaper_colors, lambda changed: self.reload_css() if changed else None)

    def close(self):
        w, self.win = self.win, None
        if w is not None:
            w.animate_out()
        return True


# ------------------------------------------------------------------ process plumbing
def claim_lock():
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        try:
            os.kill(int(os.read(fd, 32).decode().strip() or 0), signal.SIGUSR1)
        except (OSError, ValueError):
            pass
        sys.exit(0)
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    return fd


def add_unix_signal(signum, handler):
    for name in ("signal_add", "signal_add_full"):
        try:
            from gi.repository import GLibUnix
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                getattr(GLibUnix, name)(GLib.PRIORITY_HIGH, signum, handler)
            return
        except Exception:
            continue
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signum, handler)
        return
    except Exception:
        pass
    flag = {"hit": False}
    signal.signal(signum, lambda *_: flag.__setitem__("hit", True))
    GLib.timeout_add(150, lambda: (flag["hit"] and (flag.__setitem__("hit", False), handler()), True)[1])


def start_watchdog():
    """If the main loop stops answering for 6 s, log every thread's stack once."""
    import faulthandler
    faulthandler.enable(all_threads=True)
    beat = {"t": time.monotonic()}

    def run():
        dumped = False
        while True:
            GLib.idle_add(lambda: (beat.__setitem__("t", time.monotonic()), False)[1])
            time.sleep(2)
            late = time.monotonic() - beat["t"]
            if late > 6 and not dumped:
                dumped = True
                print("panel: MAIN LOOP STALLED for %.0fs; thread stacks follow" % late, file=sys.stderr, flush=True)
                faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
            elif late <= 6:
                dumped = False
    threading.Thread(target=run, daemon=True).start()


def main():
    hidden = "--hidden" in sys.argv
    _lock = claim_lock()  # noqa: F841 (held for the process lifetime)
    try:
        ctl = Controller()
    except Exception:
        import traceback
        traceback.print_exc()
        pc.notify("Panel failed to start", "See ~/.cache/hypr-rice-panel.log")
        sys.exit(1)
    start_watchdog()
    # Never open or close a window from inside the signal callback itself: gtk-layer-shell needs a Wayland
    # round trip during show(), which deadlocks there. Hand the work to a normal idle callback instead.
    add_unix_signal(signal.SIGUSR1, lambda: (GLib.idle_add(lambda: (ctl.toggle(), False)[1]), True)[1])
    add_unix_signal(signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    add_unix_signal(signal.SIGINT, lambda: (Gtk.main_quit(), False)[1])
    if not hidden:
        GLib.idle_add(lambda: (ctl.open(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()

```

## File: `scripts/panelcore.py`
```
"""panelcore: everything the control panel does, with no GTK in it.

Each function shells out to a standard tool and returns plain Python values.
Every call is safe when the tool is missing (returns None / "" / [] / False).
Nothing here blocks the UI: panel.py calls all of it from worker threads.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess as sp
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

RICE = os.path.expanduser("~/.config/hypr-rice")
CACHE = os.path.expanduser("~/.cache/hypr-rice-panel")
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
ENV = {**os.environ, "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}


# ---------------------------------------------------------------- plumbing
def have(cmd):
    return bool(shutil.which(cmd))


def run(cmd, timeout=3.0, stdin=None):
    """Run a command; return CompletedProcess or None if missing / timed out."""
    if not have(cmd[0]):
        return None
    try:
        return sp.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV, input=stdin)
    except (OSError, sp.SubprocessError):
        return None


def sh(cmd, timeout=3.0):
    """stdout text of a command, '' on any failure."""
    r = run(cmd, timeout)
    return r.stdout if r else ""


def spawn(cmd):
    """Start a command fully detached (it outlives the panel)."""
    if isinstance(cmd, str):
        cmd = ["bash", "-c", cmd]
    try:
        sp.Popen(cmd, stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL, start_new_session=True)
    except OSError:
        pass


def notify(title, body=""):
    spawn(["notify-send", "-a", "Control panel", "-t", "3500", title, body])


def split_terse(line):
    """Split nmcli --terse output, honouring \\: and \\\\ escapes."""
    fields, part, esc = [], [], False
    for ch in line.rstrip("\n"):
        if esc:
            part.append(ch)
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            fields.append("".join(part))
            part = []
        else:
            part.append(ch)
    fields.append("".join(part))
    return fields


def tidy(text, limit=140):
    text = re.sub(r"\s+", " ", (text or "").strip())
    text = re.sub(r"^Error:\s*", "", text)
    return text[:limit]


# ---------------------------------------------------------------- audio / light
def volume():
    """-> (percent 0..150, muted) or None"""
    m = re.search(r"Volume:\s*([\d.]+)(\s*\[MUTED\])?", sh(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]))
    return (round(float(m.group(1)) * 100), bool(m.group(2))) if m else None


def set_volume(pct):
    sh(["wpctl", "set-volume", "-l", "1", "@DEFAULT_AUDIO_SINK@", f"{int(pct)}%"])


def toggle_mute():
    sh(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])


def mic_muted():
    out = sh(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"])
    return None if not out else "[MUTED]" in out


def toggle_mic():
    sh(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"])


def brightness():
    """-> percent or None  (brightnessctl -m: dev,class,cur,pct,max)"""
    parts = sh(["brightnessctl", "-m"]).strip().split(",")
    try:
        return int(parts[3].rstrip("%"))
    except (IndexError, ValueError):
        return None


def set_brightness(pct):
    sh(["brightnessctl", "-q", "set", f"{max(1, int(pct))}%"])


def audio_devices(kind="sink"):
    """Outputs (kind='sink') or inputs ('source'): [dict(id, name, default, kind)] sorted default-first.
    Uses pactl (works on PipeWire and PulseAudio)."""
    if not have("pactl"):
        return []
    default = sh(["pactl", f"get-default-{kind}"]).strip()
    out = []
    raw = sh(["pactl", "-f", "json", "list", f"{kind}s"], 4.0)
    try:
        for d in json.loads(raw):
            name = d.get("name", "")
            if kind == "source" and (name.endswith(".monitor") or d.get("monitor_of_sink") not in (None, 4294967295)):
                continue
            out.append(dict(id=name, name=d.get("description") or name, default=name == default, kind=kind,
                            hint=" ".join([name, str(d.get("properties", {}).get("device.form_factor", "")),
                                           str(d.get("properties", {}).get("device.bus", ""))]).lower()))
    except (ValueError, TypeError, AttributeError):
        out = []
        for line in sh(["pactl", "list", "short", f"{kind}s"], 4.0).splitlines():
            p = line.split("\t")
            if len(p) < 2 or (kind == "source" and p[1].endswith(".monitor")):
                continue
            pretty = re.sub(r"^(alsa_output|alsa_input|bluez_output|bluez_input)\.", "", p[1]).replace("_", " ").replace(".", " ")
            out.append(dict(id=p[1], name=pretty, default=p[1] == default, kind=kind, hint=p[1].lower()))
    return sorted(out, key=lambda d: (not d["default"], d["name"].lower()))


def set_default_audio(kind, name):
    """Make `name` the default and move every playing stream to it."""
    sh(["pactl", f"set-default-{kind}", name])
    streams, move = ("sink-inputs", "move-sink-input") if kind == "sink" else ("source-outputs", "move-source-output")
    for line in sh(["pactl", "list", "short", streams]).splitlines():
        sid = line.split("\t")[0]
        if sid.isdigit():
            sh(["pactl", move, sid, name])


# ---------------------------------------------------------------- Wi-Fi
def wifi():
    """-> (enabled, active connection name or '') or None"""
    st = sh(["nmcli", "radio", "wifi"]).strip()
    if not st:
        return None
    name = ""
    for line in sh(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"]).splitlines():
        f = split_terse(line)
        if len(f) >= 2 and f[1] == "802-11-wireless" and f[0] != HOTSPOT:
            name = f[0]
            break
    return (st == "enabled", name)


def set_wifi(on):
    sh(["nmcli", "radio", "wifi", "on" if on else "off"], 6.0)


def wifi_device():
    for line in sh(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"]).splitlines():
        f = split_terse(line)
        if len(f) >= 2 and f[1] == "wifi":
            return f[0]
    return ""


def wifi_saved():
    """Names of saved Wi-Fi profiles (normally the same as the SSID)."""
    names = set()
    for line in sh(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]).splitlines():
        f = split_terse(line)
        if len(f) >= 2 and f[1] == "802-11-wireless" and f[0] != HOTSPOT:
            names.add(f[0])
    return names


def wifi_list():
    """Nearby networks from NetworkManager's cache (instant), strongest first, one per SSID.
    [dict(ssid, signal, security, active, band)]"""
    out = sh(["nmcli", "-t", "-e", "yes", "-f", "IN-USE,SSID,SIGNAL,SECURITY,FREQ", "device", "wifi", "list"], 5.0)
    best = {}
    for line in out.splitlines():
        f = split_terse(line)
        if len(f) < 5 or not f[1].strip():
            continue
        try:
            sig = max(0, min(100, int(f[2])))
        except ValueError:
            sig = 0
        m = re.match(r"\d+", f[4])
        freq = int(m.group(0)) if m else 0
        item = dict(ssid=f[1], signal=sig, security=f[3].strip(), active=f[0].strip() == "*",
                    band="5 GHz" if freq >= 4900 else ("2.4 GHz" if freq else ""))
        old = best.get(f[1])
        if not old or item["active"] or (not old["active"] and sig > old["signal"]):
            best[f[1]] = item
    return sorted(best.values(), key=lambda n: (not n["active"], -n["signal"], n["ssid"].lower()))


def wifi_rescan():
    sh(["nmcli", "device", "wifi", "rescan"], 6.0)


def wifi_ip():
    dev = wifi_device()
    if not dev:
        return ""
    for line in sh(["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", dev]).splitlines():
        if ":" in line:
            return line.split(":", 1)[1].split("/")[0]
    return ""


def wifi_connect(ssid, password=None):
    """-> (ok, message, needs_password).
    A saved network is simply brought up. A new one is created, and if that fails the half-made profile
    is deleted again, so a wrong password never leaves a broken entry behind."""
    saved = ssid in wifi_saved()
    if saved and password:
        run(["nmcli", "connection", "modify", "id", ssid, "wifi-sec.psk", password], 6.0)
    if saved:
        cmd = ["nmcli", "-w", "25", "connection", "up", "id", ssid]
    else:
        cmd = ["nmcli", "-w", "25", "device", "wifi", "connect", ssid] + (["password", password] if password else [])
    r = run(cmd, 40.0)
    if r is None:
        return False, "nmcli is not available", False
    if r.returncode == 0:
        return True, f"Connected to {ssid}", False
    msg = tidy(r.stderr or r.stdout)
    if not saved and ssid in wifi_saved():
        run(["nmcli", "connection", "delete", "id", ssid], 6.0)
    needs = bool(re.search(r"secret|password|psk|auth|activation failed|no suitable", msg, re.I))
    return False, msg or "Could not connect", needs


def wifi_disconnect():
    dev = wifi_device()
    if dev:
        sh(["nmcli", "device", "disconnect", dev], 8.0)


def wifi_forget(ssid):
    sh(["nmcli", "connection", "delete", "id", ssid], 6.0)


# ---------------------------------------------------------------- hotspot
HOTSPOT = "rice-hotspot"


def hotspot_active():
    for line in sh(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"]).splitlines():
        if split_terse(line)[0] == HOTSPOT:
            return True
    return False


def hotspot_info():
    """-> (ssid, password) of the saved hotspot, or ('', '') if never set up."""
    if HOTSPOT not in {split_terse(l)[0] for l in sh(["nmcli", "-t", "-f", "NAME", "connection", "show"]).splitlines()}:
        return "", ""
    ssid = sh(["nmcli", "-g", "802-11-wireless.ssid", "connection", "show", HOTSPOT]).strip()
    psk = sh(["nmcli", "-s", "-g", "802-11-wireless-security.psk", "connection", "show", HOTSPOT]).strip()
    return ssid, psk


def _random_password(n=10):
    return hashlib.sha256(os.urandom(16)).hexdigest()[:n]


def hotspot_save(ssid=None, password=None):
    """Create or update the hotspot profile. -> (ok, message)"""
    cur_ssid, cur_psk = hotspot_info()
    ssid = (ssid or cur_ssid or (os.uname().nodename[:20] or "rice-hotspot")).strip()
    password = (password or cur_psk or _random_password()).strip()
    if len(password) < 8 or len(password) > 63:
        return False, "Password must be 8-63 characters"
    if not cur_ssid:
        dev = wifi_device()
        if not dev:
            return False, "No Wi-Fi adapter found"
        r = run(["nmcli", "connection", "add", "type", "wifi", "ifname", dev, "con-name", HOTSPOT,
                 "autoconnect", "no", "ssid", ssid, "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg",
                 "ipv4.method", "shared", "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password], 8.0)
    else:
        r = run(["nmcli", "connection", "modify", HOTSPOT, "802-11-wireless.ssid", ssid,
                 "wifi-sec.psk", password], 8.0)
    if r is None or r.returncode:
        return False, tidy(r.stderr if r else "nmcli is not available")
    return True, "Saved"


def hotspot_set(on):
    """-> (ok, message)"""
    if not on:
        r = run(["nmcli", "connection", "down", HOTSPOT], 10.0)
        return True, "Hotspot off"
    ok, msg = hotspot_save()
    if not ok:
        return False, msg
    if not (wifi() or (False,))[0]:
        set_wifi(True)
        time.sleep(1.2)
    r = run(["nmcli", "-w", "20", "connection", "up", HOTSPOT], 30.0)
    if r and r.returncode == 0:
        return True, "Hotspot on"
    return False, tidy(r.stderr if r else "nmcli is not available") or "Could not start the hotspot"


# ---------------------------------------------------------------- airplane mode
def airplane():
    """-> True if every wifi + bluetooth radio is soft-blocked, None if rfkill is missing."""
    out = sh(["rfkill", "-n", "-o", "TYPE,SOFT"])
    rows = [l.split() for l in out.splitlines() if l.strip()]
    rows = [r for r in rows if r[0] in ("wlan", "bluetooth") and len(r) >= 2]
    if not rows:
        return None
    return all(r[1] == "blocked" for r in rows)


def set_airplane(on):
    if have("rfkill"):
        sh(["rfkill", "block" if on else "unblock", "wifi"])
        sh(["rfkill", "block" if on else "unblock", "bluetooth"])
    else:
        sh(["nmcli", "radio", "all", "off" if on else "on"])


# ---------------------------------------------------------------- Bluetooth
def bluetooth():
    """-> powered bool or None (no bluetooth tools / no adapter)"""
    out = sh(["bluetoothctl", "show"], 3.0)
    if not out or "Powered" not in out:
        return None
    return "Powered: yes" in out


def set_bluetooth(on):
    if on:
        sh(["rfkill", "unblock", "bluetooth"])
    sh(["bluetoothctl", "power", "on" if on else "off"], 5.0)


def _bt_info(mac):
    out = sh(["bluetoothctl", "info", mac], 3.0)
    d = dict(mac=mac, name=mac, icon="", paired=False, connected=False, trusted=False, battery=None, rssi=None)
    for line in out.splitlines():
        k, _, v = line.strip().partition(": ")
        if k == "Alias" and v:
            d["name"] = v
        elif k == "Name" and d["name"] == mac:
            d["name"] = v
        elif k == "Icon":
            d["icon"] = v
        elif k in ("Paired", "Connected", "Trusted"):
            d[k.lower()] = v == "yes"
        elif k == "Battery Percentage":
            m = re.search(r"\((\d+)\)", v)
            d["battery"] = int(m.group(1)) if m else None
        elif k == "RSSI":
            m = re.search(r"-?\d+", v)
            d["rssi"] = int(m.group(0)) if m else None
    return d


def bt_devices(seen=()):
    """Paired devices plus anything seen during this scan, with live state.
    Sorted: connected, paired, then nearby by signal."""
    macs = set()
    for line in sh(["bluetoothctl", "devices"], 4.0).splitlines():
        m = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s", line)
        if m:
            macs.add(m.group(1).upper())
    if not macs:
        return []
    with ThreadPoolExecutor(max_workers=6) as ex:
        infos = list(ex.map(_bt_info, sorted(macs)))
    seen = {s.upper() for s in seen}
    keep = [d for d in infos if d["paired"] or d["connected"] or d["mac"] in seen]
    keep = [d for d in keep if d["name"] != d["mac"].replace(":", "-")]       # unnamed randomised addresses
    return sorted(keep, key=lambda d: (not d["connected"], not d["paired"], -(d["rssi"] if d["rssi"] is not None else -999),
                                       d["name"].lower()))


def bt_connected():
    """Names of connected devices (verified per device, since old BlueZ ignores the 'Connected' filter)."""
    macs = [m.group(1).upper() for l in sh(["bluetoothctl", "devices", "Connected"], 3.0).splitlines()
            for m in [re.match(r"Device\s+([0-9A-Fa-f:]{17})\s", l)] if m]
    return [d["name"] for d in map(_bt_info, macs[:6]) if d["connected"]]


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][A-Z0-9]|[\x01\x02\x07]")
_PROMPT = re.compile(r"\[[^\[\]]*\]#\s?")


class BtSession:
    """One long-lived `bluetoothctl` on a pseudo-terminal. It scans, pairs, connects and answers the pairing
    prompts, and reports everything through callback(kind, **info):
        seen(mac, name)  changed(mac)  confirm(passkey)  pin()  result(step, ok, text)  line(text)"""

    def __init__(self, callback):
        self.cb = callback
        self.pid = None
        self.fd = None
        self.alive = False
        self.scanning = False
        self.lock = threading.Lock()

    def start(self):
        import pty
        import termios
        if not have("bluetoothctl") or self.alive:
            return self.alive
        try:
            master, slave = pty.openpty()
            attrs = termios.tcgetattr(slave)
            attrs[3] &= ~termios.ECHO
            termios.tcsetattr(slave, termios.TCSANOW, attrs)
            proc = sp.Popen(["bluetoothctl"], stdin=slave, stdout=slave, stderr=slave, close_fds=True,
                            start_new_session=True, env=ENV)
            os.close(slave)
        except (OSError, sp.SubprocessError):
            return False
        self.proc, self.fd, self.alive = proc, master, True
        threading.Thread(target=self._read, daemon=True).start()
        self.send("agent KeyboardDisplay")
        self.send("default-agent")
        return True

    def send(self, line):
        if not self.alive:
            return
        try:
            with self.lock:
                os.write(self.fd, (line + "\n").encode())
        except OSError:
            self.alive = False

    def scan(self, on):
        self.scanning = on
        self.send("scan on" if on else "scan off")

    def stop(self):
        if not self.alive:
            return
        try:
            self.send("scan off")
            self.send("quit")
            time.sleep(0.1)
        finally:
            self.alive = False
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1.5)
            except Exception:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except Exception:
                    pass
            try:
                os.close(self.fd)
            except OSError:
                pass

    # -- reading
    def _read(self):
        buf = ""
        last_prompt = ""
        while self.alive:
            try:
                data = os.read(self.fd, 4096)
            except OSError:
                break
            if not data:
                break
            buf += _ANSI.sub("", data.decode(errors="replace")).replace("\r", "\n")
            *lines, buf = buf.split("\n")
            for ln in lines:
                ln = _PROMPT.sub("", ln).strip()
                if ln and ln == last_prompt:               # the prompt we already reacted to, now newline-terminated
                    last_prompt = ""
                    continue
                self._line(ln)
            tail = _PROMPT.sub("", buf).strip()
            if tail and tail != last_prompt and re.search(r"\((yes/no|y/n)\):?$|Enter (PIN code|passkey)[^:]*:?$", tail, re.I):
                last_prompt = tail
                self._line(tail)
        self.alive = False

    def _line(self, ln):
        if not ln:
            return
        e = self.cb
        m = re.match(r"\[NEW\]\s+Device\s+([0-9A-F:]{17})\s+(.+)", ln, re.I)
        if m:
            return e("seen", mac=m.group(1).upper(), name=m.group(2))
        m = re.match(r"\[CHG\]\s+Device\s+([0-9A-F:]{17})\s+(.+?):\s*(.*)", ln, re.I)
        if m:
            mac, key, val = m.group(1).upper(), m.group(2), m.group(3)
            if key in ("Name", "Alias", "RSSI") and val:
                e("seen", mac=mac, name=val if key != "RSSI" else "")
            return e("changed", mac=mac)
        m = re.search(r"Confirm passkey\s+(\d+)", ln, re.I)
        if m:
            return e("confirm", passkey=m.group(1))
        if re.search(r"Authorize service|Request authorization", ln, re.I):
            self.send("yes")
            return
        if re.search(r"Enter (PIN code|passkey)", ln, re.I):
            return e("pin")
        if re.search(r"Pairing successful", ln, re.I):
            return e("result", step="pair", ok=True, text="Paired")
        m = re.search(r"Failed to pair:\s*(.*)", ln, re.I)
        if m:
            return e("result", step="pair", ok=False, text=_bt_error(m.group(1)))
        if re.search(r"Connection successful", ln, re.I):
            return e("result", step="connect", ok=True, text="Connected")
        m = re.search(r"Failed to connect:\s*(.*)", ln, re.I)
        if m:
            return e("result", step="connect", ok=False, text=_bt_error(m.group(1)))
        if re.search(r"Successful disconnected|Disconnection successful", ln, re.I):
            return e("result", step="disconnect", ok=True, text="Disconnected")
        m = re.search(r"Failed to disconnect:\s*(.*)", ln, re.I)
        if m:
            return e("result", step="disconnect", ok=False, text=_bt_error(m.group(1)))
        if re.search(r"Device has been removed", ln, re.I):
            return e("result", step="remove", ok=True, text="Removed")


def _bt_error(text):
    t = text.strip()
    if "AuthenticationCanceled" in t or "AuthenticationRejected" in t:
        return "Pairing was declined"
    if "AuthenticationTimeout" in t:
        return "Pairing timed out"
    if "AlreadyExists" in t:
        return "Already paired"
    if "InProgress" in t:
        return "Busy, try again"
    if "page-timeout" in t or "ConnectionAttemptFailed" in t or "Host is down" in t:
        return "Device not reachable"
    return tidy(re.sub(r"org\.bluez\.Error\.", "", t)) or "Failed"


# ---------------------------------------------------------------- power / misc
def dnd():
    """-> bool or None (mako not running)"""
    if not have("makoctl"):
        return None
    r = run(["makoctl", "mode"], 2)
    return None if (r is None or r.returncode) else "do-not-disturb" in r.stdout.split()


def toggle_dnd():
    sh(["makoctl", "mode", "-t", "do-not-disturb"])


NL = os.path.join(RICE, "scripts", "nightlight.sh")


NL_NATIVE = not os.path.isfile(NL)          # no helper script: drive hyprsunset directly
NL_TEMP_FILE = os.path.join(CACHE, "nightlight-temp")


def nightlight_available():
    return have("hyprsunset") and (not NL_NATIVE or have("pgrep"))


def _hs_pid_temp():
    """(running, temperature) of a hyprsunset started with -t, read from /proc."""
    for pid in sh(["pgrep", "-x", "hyprsunset"]).split():
        try:
            args = open(f"/proc/{pid}/cmdline").read().split("\0")
        except OSError:
            continue
        if "-t" in args and args.index("-t") + 1 < len(args):
            try:
                return True, int(args[args.index("-t") + 1])
            except ValueError:
                pass
        return True, None
    return False, None


def _hs_start(kelvin):
    kelvin = int(max(1000, min(6500, kelvin)))
    sh(["pkill", "-x", "hyprsunset"])
    time.sleep(0.15)
    spawn(["hyprsunset", "-t", str(kelvin)])
    try:
        os.makedirs(CACHE, exist_ok=True)
        open(NL_TEMP_FILE, "w").write(str(kelvin))
    except OSError:
        pass


def _hs_saved():
    try:
        return int(open(NL_TEMP_FILE).read().strip())
    except (OSError, ValueError):
        return 4000


def nightlight():
    """-> dict(on, temp, auto, frm, to) or None"""
    if NL_NATIVE:
        on, temp = _hs_pid_temp()
        return dict(on=on, temp=temp or _hs_saved(), auto=False, frm="", to="")
    out = sh([NL, "status"]).split("\n")
    try:
        on, temp = out[0].split()
        kv = dict(x.split("=") for x in out[1].split())
        return dict(on=on == "on", temp=int(temp), auto=kv["auto"] == "1", frm=kv["from"], to=kv["to"])
    except (ValueError, IndexError, KeyError):
        return None


def toggle_nightlight():
    if NL_NATIVE:
        if _hs_pid_temp()[0]:
            sh(["pkill", "-x", "hyprsunset"])
        else:
            _hs_start(_hs_saved())
        return
    sh([NL, "toggle"])


def set_warmth(kelvin):
    if NL_NATIVE:
        _hs_start(kelvin)
        return
    sh([NL, "on", str(int(kelvin))])


def set_night_auto(on):
    if not NL_NATIVE:
        sh([NL, "auto", "on" if on else "off"])


PROFILES = ["power-saver", "balanced", "performance"]


def profile():
    return sh(["powerprofilesctl", "get"]).strip() or None


def cycle_profile():
    cur = profile()
    if not cur:
        return
    avail = sh(["powerprofilesctl", "list"])
    order = [p for p in PROFILES if p in avail] or PROFILES
    sh(["powerprofilesctl", "set", order[(order.index(cur) + 1) % len(order)] if cur in order else order[0]])


def _num(path):
    try:
        return float(open(path).read().strip())
    except (OSError, ValueError):
        return None


def battery():
    """-> (percent 0..100, status) or None (desktop). Some firmware reports a capacity above 100, so when
    that happens the percentage is worked out from the charge / energy counters instead, then clamped."""
    total_now = total_full = 0.0
    pcts, status = [], ""
    for d in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        cap = _num(d + "/capacity")
        if cap is None:
            continue
        pcts.append(cap)
        status = status or (open(d + "/status").read().strip() if os.path.exists(d + "/status") else "")
        for now, full in (("energy_now", "energy_full"), ("charge_now", "charge_full")):
            n, f = _num(f"{d}/{now}"), _num(f"{d}/{full}")
            if n is not None and f:
                total_now += n
                total_full += f
                break
    if not pcts:
        return None
    pct = sum(pcts) / len(pcts)
    if (pct > 100 or pct < 0) and total_full:
        pct = 100.0 * total_now / total_full
    return int(max(0, min(100, round(pct)))), status


# ---- stay awake (blocks idle + sleep through systemd-inhibit; nothing persistent is installed)
CAFFEINE_PID = os.path.join(RUNTIME, "hypr-rice-caffeine.pid")


def caffeine_available():
    return have("systemd-inhibit") and have("sleep")


def caffeine_on():
    """True if the stay-awake lock is currently held."""
    try:
        pid = int(open(CAFFEINE_PID).read().strip())
        os.kill(pid, 0)
        return "hypr-rice-caffeine" in open(f"/proc/{pid}/cmdline").read()
    except (OSError, ValueError):
        return False


def set_caffeine(on):
    if not on:
        try:
            pid = int(open(CAFFEINE_PID).read().strip())
            os.killpg(pid, signal.SIGTERM)
        except (OSError, ValueError):
            pass
        try:
            os.unlink(CAFFEINE_PID)
        except OSError:
            pass
        return True
    if caffeine_on():
        return True
    try:
        p = sp.Popen(["systemd-inhibit", "--what=idle:sleep", "--who=hypr-rice", "--why=hypr-rice-caffeine",
                      "--mode=block", "sleep", "infinity"], stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL,
                     start_new_session=True)
        time.sleep(0.25)
        if p.poll() is not None:
            notify("Stay awake", "Could not take the idle lock.")
            return False
        open(CAFFEINE_PID, "w").write(str(p.pid))
        return True
    except OSError:
        return False


# ---- screen recording. Uses your own screen-record-toggle.sh if you have one, otherwise wf-recorder directly.
REC = os.path.join(RICE, "scripts", "screen-record-toggle.sh")
REC_SCRIPT = os.path.isfile(REC)
REC_DIR = os.path.expanduser("~/Videos/Recordings")
REC_PID = os.path.join(RUNTIME, "hypr-rice-rec.pid")


def rec_available():
    return have("wf-recorder")


def _rec_state():
    """(pid, started_at, outfile) of a live native recording, else None."""
    try:
        pid, started, out = open(REC_PID).read().split(" ", 2)
        os.kill(int(pid), 0)
        if "wf-recorder" in open(f"/proc/{pid}/cmdline").read():
            return int(pid), float(started), out.strip()
    except (OSError, ValueError):
        pass
    return None


def rec_status():
    """-> (recording?, seconds so far)"""
    if REC_SCRIPT:
        try:
            return json.loads(sh([REC, "status"])).get("class") == "recording", 0
        except ValueError:
            return False, 0
    st = _rec_state()
    return (True, int(time.time() - st[1])) if st else (False, 0)


REC_MODS = os.path.join(RUNTIME, "hypr-rice-rec.mods")


def _pa(*a):
    return sh(["pactl", *a], 4.0).strip()


def _rec_audio_device(mode):
    """PulseAudio/PipeWire source for wf-recorder. mode: mic | sys | both. -> name or None."""
    if not have("pactl"):
        return None
    mic = _pa("get-default-source")
    sink = _pa("get-default-sink")
    if mode == "mic":
        return mic or None
    if mode == "sys":
        return (sink + ".monitor") if sink else None
    if not mic or not sink:                                   # both: mix mic + system sound into a virtual sink
        return (sink + ".monitor") if sink else (mic or None)
    mods = []
    for args in (["load-module", "module-null-sink", "sink_name=hypr_rec_mix",
                  "sink_properties=device.description=RecordingMix"],
                 ["load-module", "module-loopback", f"source={mic}", "sink=hypr_rec_mix", "latency_msec=40"],
                 ["load-module", "module-loopback", f"source={sink}.monitor", "sink=hypr_rec_mix", "latency_msec=40"]):
        mid = _pa(*args)
        if not mid.isdigit():
            for m in mods:
                _pa("unload-module", m)
            return (sink + ".monitor")
        mods.append(mid)
    open(REC_MODS, "w").write(" ".join(mods))
    return "hypr_rec_mix.monitor"


def _rec_audio_cleanup():
    try:
        mods = open(REC_MODS).read().split()
        os.unlink(REC_MODS)
    except OSError:
        return
    for m in reversed(mods):
        _pa("unload-module", m)


def rec_start(region=False, audio=""):
    """Start recording. region: drag a box (needs slurp). audio: "" | "mic" | "sys" | "both". -> True if recording."""
    if audio is True:
        audio = "mic"
    if REC_SCRIPT:                                            # your screen-record-toggle.sh does the recording
        spawn([REC, "start", audio or "none"] + (["region"] if region else []))
        return True
    if _rec_state():
        return True
    cmd = ["wf-recorder"]
    if audio:
        dev = _rec_audio_device(audio)
        if not dev:
            notify("Screen record", "No audio device found, recording without sound.")
        else:
            cmd.append("--audio=" + dev)
    if region:
        geo = sh(["slurp"], 90.0).strip()
        if not geo:
            return False
        cmd += ["-g", geo]
    try:
        os.makedirs(REC_DIR, exist_ok=True)
        out = os.path.join(REC_DIR, "rec-" + time.strftime("%Y%m%d-%H%M%S") + ".mp4")
        p = sp.Popen(cmd + ["-f", out], stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL, start_new_session=True)
        time.sleep(0.5)
        if p.poll() is not None:
            _rec_audio_cleanup()
            notify("Screen record", "wf-recorder could not start.")
            return False
        open(REC_PID, "w").write(f"{p.pid} {time.time()} {out}")
        notify("Recording started", "Open the panel and tap Screen record to stop.")
        return True
    except OSError:
        return False


def rec_stop():
    if REC_SCRIPT:
        spawn([REC, "stop"])
        return
    st = _rec_state()
    if not st:
        return
    try:
        os.kill(st[0], signal.SIGINT)                # wf-recorder finishes the file on SIGINT
        for _ in range(30):
            time.sleep(0.1)
            try:
                os.kill(st[0], 0)
            except OSError:
                break
    except OSError:
        pass
    try:
        os.unlink(REC_PID)
    except OSError:
        pass
    _rec_audio_cleanup()
    notify("Recording saved", st[2])


def rec_on():
    return rec_status()[0]


# ---------------------------------------------------------------- media
def media():
    """Pick the active MPRIS player. -> dict(player status title artist art pos length) or None."""
    fmt = "{{playerName}}\t{{status}}\t{{title}}\t{{artist}}\t{{mpris:artUrl}}\t{{position}}\t{{mpris:length}}"
    best = None
    for line in sh(["playerctl", "-a", "metadata", "--format", fmt]).splitlines():
        p = line.split("\t")
        if len(p) < 7:
            continue
        item = dict(player=p[0], status=p[1], title=p[2], artist=p[3], art=p[4], pos=_us(p[5]), length=_us(p[6]))
        if item["status"] == "Playing":
            return item
        if best is None and item["status"] == "Paused":
            best = item
    return best


def _us(s):
    try:
        return int(s) / 1_000_000
    except ValueError:
        return 0.0


def player_cmd(player, *args):
    sh(["playerctl", "-p", player, *args])


def art_file(url):
    """Local path for an album-art URL (downloads and caches http(s)). '' if none."""
    if not url:
        return ""
    if url.startswith("file://"):
        p = urllib.request.url2pathname(url[7:])
        return p if os.path.isfile(p) else ""
    if url.startswith(("http://", "https://")):
        os.makedirs(CACHE, exist_ok=True)
        p = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest())
        if not os.path.isfile(p):
            try:
                with urllib.request.urlopen(url, timeout=4) as r, open(p, "wb") as f:
                    f.write(r.read(4_000_000))
            except Exception:
                return ""
        return p
    return ""


def fmt_time(sec):
    sec = int(max(0, sec))
    return f"{sec // 60}:{sec % 60:02d}"


# ---------------------------------------------------------------- colours
COLORS_CSS = os.path.join(RICE, "waybar", "colors.css")


def sync_wallpaper_colors():
    """If the wallpaper on screen is not the one the accents were taken from (you changed it by hand),
    re-sample it. Returns True when the colours changed. Cheap no-op otherwise."""
    wp = ""
    for line in sh(["hyprctl", "hyprpaper", "listactive"], 2.5).splitlines():
        m = re.search(r"(/\S.*?\.(?:png|jpe?g|webp))\s*$", line.strip(), re.I)
        if m and os.path.isfile(m.group(1)):
            wp = m.group(1)
            break
    if not wp:
        return False
    try:
        known = json.load(open(os.path.join(RICE, "generated", "colors.json"))).get("wallpaper")
    except (OSError, ValueError):
        known = None
    if known == wp:
        return False
    script = os.path.join(RICE, "scripts", "wallcolors.py")
    if not os.path.isfile(script):
        return False
    r = run(["python3", script, wp, "--no-reload"], 20.0)
    return bool(r and r.returncode == 0)


def css_colors():
    base = (
        "@define-color base #1e1e2e; @define-color surface0 #313244; @define-color surface1 #45475a;\n"
        "@define-color text #cdd6f4; @define-color subtext #a6adc8; @define-color red #f38ba8;\n"
        "@define-color green #a6e3a1; @define-color accent #cba6f7; @define-color accent2 #89b4fa;\n"
    )
    try:
        extra = open(COLORS_CSS, encoding="utf-8").read()
        extra = "\n".join(l for l in extra.splitlines() if l.strip().startswith("@define-color"))
    except OSError:
        extra = ""
    return base + extra + "\n"

```

## File: `aod.py`
```
#!/usr/bin/env python3
"""hypr-rice always-on display (iOS-style dimmed clock, glass cards in the panel's style).
Usage: aod.py preview | on | off | toggle | status | start | stop | install [idle_seconds] | uninstall
  on/toggle : stays on until you press a key or click empty space; the media card is clickable.
  start/stop: used by hypridle (idle display, dismissed by any input)."""
import sys, os, json, math, time, signal, shutil, subprocess, glob

H = os.path.expanduser("~")
ME = f"{H}/.config/hypr-rice/aod.py"
PID = "/tmp/hypr-aod.pid"
STICKY = "/tmp/hypr-aod-sticky"
WX = f"{H}/.cache/hypr-rice-aod-weather.txt"
HI = f"{H}/.config/hypr/hypridle.conf"
B, E = "# aod-begin", "# aod-end"
GL = dict(prev="\U000f04ae", next="\U000f04ad", play="\U000f040a", pause="\U000f03e4")


def sh(c, t=3):
    try:
        return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception:
        return ""


def colors():
    try:
        j = json.load(open(f"{H}/.cache/wal/colors.json"))
        return j["colors"]["color4"], j["special"]["foreground"], j["special"]["background"]
    except Exception:
        return "#cba6f7", "#cdd6f4", "#1e1e2e"


def battery():
    d = (glob.glob("/sys/class/power_supply/BAT*") or [None])[0]
    if not d:
        return ""
    try:
        pct = open(d + "/capacity").read().strip()
        ch = open(d + "/status").read().strip() == "Charging"
        return f"\uf240  {pct}%" + ("  \uf0e7" if ch else "")
    except Exception:
        return ""


def weather():
    try:
        age = time.time() - os.path.getmtime(WX) if os.path.exists(WX) else 9e9
        tf = WX + ".try"
        tried = time.time() - os.path.getmtime(tf) if os.path.exists(tf) else 9e9
        if age > 900 and tried > 60:
            os.makedirs(os.path.dirname(WX), exist_ok=True)
            open(tf, "w").close()
            subprocess.Popen(f"curl -s -m 5 'wttr.in/?format=%c+%t' -o {WX}.new && [ -s {WX}.new ] && mv {WX}.new {WX}",
                             shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return open(WX).read().strip() if os.path.exists(WX) else ""
    except Exception:
        return ""


def media():
    o = sh("playerctl metadata --format '{{title}}|||{{artist}}|||{{status}}'")
    p = o.split("|||")
    if len(p) != 3 or not p[0] or p[2] == "Stopped":
        return None
    return p[0], p[1], p[2]


def rr(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def run(mode="idle"):
    preview, sticky = mode == "preview", mode == "sticky"
    interactive = preview or sticky
    import gi
    import cairo
    gi.require_version("Gtk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, GdkPixbuf, GtkLayerShell as L
    open(PID, "w").write(str(os.getpid()))
    acc, fg, base = colors()
    rgb = lambda h, a=1.0: tuple(int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file(open(f"{H}/.cache/wal/wal").read().strip())
    except Exception:
        pb = None
    cache, hits = {}, {}

    win = Gtk.Window()
    L.init_for_window(win)
    L.set_layer(win, L.Layer.OVERLAY)
    L.set_namespace(win, "aod")
    for e in (L.Edge.TOP, L.Edge.BOTTOM, L.Edge.LEFT, L.Edge.RIGHT):
        L.set_anchor(win, e, True)
    L.set_exclusive_zone(win, -1)
    L.set_keyboard_mode(win, L.KeyboardMode.EXCLUSIVE if sticky else (L.KeyboardMode.ON_DEMAND if preview else L.KeyboardMode.NONE))

    def lay(cr, s, size, bold=False, width=None):
        l = PangoCairo.create_layout(cr)
        fd = Pango.FontDescription("JetBrainsMono Nerd Font")
        fd.set_weight(Pango.Weight.BOLD if bold else Pango.Weight.NORMAL)
        fd.set_absolute_size(size * Pango.SCALE)
        l.set_font_description(fd)
        if width:
            l.set_width(int(width * Pango.SCALE))
            l.set_ellipsize(Pango.EllipsizeMode.END)
        l.set_text(s, -1)
        return l

    def put(cr, l, x, y, col, left=False):
        w, h = l.get_pixel_size()
        cr.set_source_rgba(*col)
        cr.move_to(x if left else x - w / 2, y - h / 2)
        PangoCairo.show_layout(cr, l)

    def glass(cr, x, y, w, h, r):
        rr(cr, x, y, w, h, r)
        cr.set_source_rgba(*rgb(base, 0.58))
        cr.fill_preserve()
        g = cairo.LinearGradient(x, y, x + w, y + h)
        g.add_color_stop_rgba(0, *rgb(acc, 0.24))
        g.add_color_stop_rgba(1, *rgb(acc, 0.06))
        cr.set_source(g)
        cr.fill_preserve()
        cr.set_source_rgba(*rgb(fg, 0.20))
        cr.set_line_width(1)
        cr.stroke()

    def draw(wd, cr):
        W, Hh = wd.get_allocated_width(), wd.get_allocated_height()
        hits.clear()
        cr.set_source_rgba(0.03, 0.03, 0.05, 1)
        cr.paint()
        if pb:
            if cache.get("k") != (W, Hh):
                s = max(W / pb.get_width(), Hh / pb.get_height())
                sw, sh_ = int(pb.get_width() * s) + 1, int(pb.get_height() * s) + 1
                cache["k"] = (W, Hh)
                cache["p"] = (pb.scale_simple(sw, sh_, GdkPixbuf.InterpType.BILINEAR), (W - sw) // 2, (Hh - sh_) // 2)
            p, ox, oy = cache["p"]
            Gdk.cairo_set_source_pixbuf(cr, p, ox, oy)
            cr.paint()
        cr.set_source_rgba(0.03, 0.03, 0.05, 0.84)
        cr.paint()
        put(cr, lay(cr, time.strftime("%A %d %B"), Hh * 0.034), W / 2, Hh * 0.25, rgb(fg, 0.75))
        put(cr, lay(cr, time.strftime("%H:%M"), Hh * 0.26, True), W / 2, Hh * 0.40, rgb(fg, 0.94))
        m = media()
        items = [battery(), weather()] + ([] if interactive else [f"\uf001  {m[0][:34]}" if m else ""])
        items = [x for x in items if x]
        size = Hh * 0.026
        ls = [lay(cr, x, size) for x in items]
        pw = [max(l.get_pixel_size()[0] + 56, 190) for l in ls]
        ph = Hh * 0.075
        gap = 16
        x = (W - (sum(pw) + gap * (len(pw) - 1))) / 2
        y = Hh * 0.58 - ph / 2
        for l, w in zip(ls, pw):
            glass(cr, x, y, w, ph, ph / 2)
            put(cr, l, x + w / 2, y + ph / 2, rgb(acc, 0.97))
            x += w + gap
        if interactive and m:
            cw, ch = max(W * 0.34, 560), Hh * 0.13
            cx, cy = (W - cw) / 2, Hh * 0.72
            glass(cr, cx, cy, cw, ch, 26)
            d, g2, pad = ch * 0.56, ch * 0.10, ch * 0.24
            bx = {"next": cx + cw - pad - d}
            bx["play"] = bx["next"] - g2 - d
            bx["prev"] = bx["play"] - g2 - d
            by = cy + (ch - d) / 2
            tx = cx + pad + 4
            tw = bx["prev"] - g2 - tx
            put(cr, lay(cr, m[0], ch * 0.24, True, tw), tx, cy + ch * 0.36, rgb(fg, 0.96), True)
            put(cr, lay(cr, m[1] or "Unknown artist", ch * 0.19, False, tw), tx, cy + ch * 0.68, rgb(fg, 0.62), True)
            for k, glyph in (("prev", GL["prev"]), ("play", GL["pause"] if m[2] == "Playing" else GL["play"]), ("next", GL["next"])):
                cr.arc(bx[k] + d / 2, by + d / 2, d / 2, 0, 2 * math.pi)
                if k == "play":
                    cr.set_source_rgba(*rgb(acc, 0.95))
                    cr.fill()
                    col = rgb(base, 1.0)
                else:
                    cr.set_source_rgba(*rgb(fg, 0.10))
                    cr.fill()
                    col = rgb(fg, 0.92)
                put(cr, lay(cr, glyph, d * 0.46), bx[k] + d / 2, by + d / 2, col)
                hits[k] = (bx[k], by, d, d)
        if interactive:
            put(cr, lay(cr, "Click anywhere else or press a key to close", Hh * 0.017), W / 2, Hh * 0.93, rgb(fg, 0.35))

    def click(wd, ev):
        cmd = {"prev": "previous", "play": "play-pause", "next": "next"}
        for k, (hx, hy, hw, hh) in hits.items():
            if hx <= ev.x <= hx + hw and hy <= ev.y <= hy + hh:
                subprocess.Popen(["playerctl", cmd[k]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                GLib.timeout_add(350, lambda: (da.queue_draw(), False)[1])
                return True
        Gtk.main_quit()
        return True

    da = Gtk.DrawingArea()
    da.connect("draw", draw)
    win.add(da)
    GLib.timeout_add_seconds(2 if interactive else 5, lambda: (da.queue_draw(), True)[1])
    if interactive:
        win.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        win.connect("key-press-event", lambda *_: Gtk.main_quit())
        win.connect("button-press-event", click)
    if preview:
        GLib.timeout_add_seconds(30, lambda: (Gtk.main_quit(), False)[1])
    win.show_all()
    Gtk.main()
    for f in (STICKY, PID):
        try:
            os.remove(f)
        except Exception:
            pass


def alive():
    try:
        os.kill(int(open(PID).read()), 0)
        return True
    except Exception:
        return False


def sticky_on():
    return alive() and os.path.exists(STICKY)


def spawn(mode):
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "run", mode], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start():
    if not alive():
        spawn("idle")


def kill():
    try:
        os.kill(int(open(PID).read()), signal.SIGTERM)
    except Exception:
        pass
    for f in (PID, STICKY):
        try:
            os.remove(f)
        except Exception:
            pass


def stop():
    if not sticky_on():
        kill()


def on():
    if alive() and not sticky_on():
        kill()
        time.sleep(0.2)
    if not alive():
        open(STICKY, "w").close()
        spawn("sticky")


def strip(t):
    if B in t and E in t:
        a, b = t.index(B), t.index(E) + len(E)
        t = t[:a].rstrip("\n") + "\n" + t[b:].lstrip("\n")
    return t


def install(secs):
    os.makedirs(os.path.dirname(ME), exist_ok=True)
    if os.path.abspath(__file__) != ME:
        shutil.copy(__file__, ME)
    os.chmod(ME, 0o755)
    t = open(HI).read() if os.path.exists(HI) else ""
    if t and not os.path.exists(HI + ".pre-aod"):
        shutil.copy(HI, HI + ".pre-aod")
    blk = (f"\n{B}\nlistener {{\n    timeout = {secs}\n    on-timeout = python3 {ME} start\n"
           f"    on-resume = python3 {ME} stop\n}}\n{E}\n")
    open(HI, "w").write(strip(t) + blk)
    subprocess.run(["pkill", "-x", "hypridle"])
    subprocess.Popen(["hypridle"], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Installed: the always-on display starts after {secs}s idle and goes away on any input.")


if __name__ == "__main__":
    a = sys.argv[1:] or ["preview"]
    if a[0] == "run":
        run(a[1] if len(a) > 1 else "idle")
    elif a[0] == "preview":
        run("preview")
    elif a[0] == "on":
        on()
    elif a[0] == "off":
        kill()
    elif a[0] == "toggle":
        kill() if sticky_on() else on()
    elif a[0] == "status":
        print("On" if sticky_on() else "Off")
    elif a[0] == "start":
        start()
    elif a[0] == "stop":
        stop()
    elif a[0] == "install":
        install(int(a[1]) if len(a) > 1 else 120)
    elif a[0] == "uninstall":
        if os.path.exists(HI):
            open(HI, "w").write(strip(open(HI).read()))
        subprocess.run(["pkill", "-x", "hypridle"])
        subprocess.Popen(["hypridle"], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        kill()
        print("Removed.")

```
