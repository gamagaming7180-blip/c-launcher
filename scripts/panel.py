#!/usr/bin/env python3
"""C Launcher panel v5 -- quick settings that drop from the top (click the clock / SUPER + A).

Same contract as before, so nothing else has to change:
  * panel-toggle.sh sends SIGUSR1 to toggle; the pid lives in $XDG_RUNTIME_DIR/hypr-rice-panel.lock
  * `panel.py --hidden` starts it hidden in the background
  * colours come from ~/.config/hypr-rice/generated/colors.json (the wallpaper colours),
    re-read every time the panel opens
Slow work (nmcli, bluetoothctl, wpctl ...) runs in worker threads; the UI only paints results.
"""
import colorsys
import glob
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from string import Template

RICE = os.path.expanduser("~/.config/hypr-rice")
COLORS_JSON = os.path.join(RICE, "generated", "colors.json")
LOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr-rice-panel.lock")
BAR_H = 52            # height of the top bar; the panel slides out from just under it
CARD_W = 420
NAMESPACE = "hypr-rice-panel"

# gtk-layer-shell has to be loaded before libwayland-client.
_LS = "/usr/lib/libgtk-layer-shell.so"
if (os.path.exists(_LS) and "gtk-layer-shell" not in os.environ.get("LD_PRELOAD", "")
        and not os.environ.get("HR_PANEL_REEXEC")):
    os.environ["LD_PRELOAD"] = _LS + (":" + os.environ["LD_PRELOAD"] if os.environ.get("LD_PRELOAD") else "")
    os.environ["HR_PANEL_REEXEC"] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv)

ENV = {k: v for k, v in os.environ.items() if k != "LD_PRELOAD"}
ENV["LC_ALL"] = "C"

IC = dict(
    wifi4="\U000f0928", wifi3="\U000f0925", wifi2="\U000f0922", wifi1="\U000f091f", wifi_off="\U000f092d",
    bt="\U000f00af", bt_off="\U000f00b2", hotspot="\U000f0003", dnd="\U000f009b", night="\U000f0594",
    game="\U000f02ca", mic="\U000f036c", mic_off="\U000f036d", air="\U000f001d", prof="\U000f04c5",
    power="\U000f0425", lock="\U000f033e", cog="\U000f0493", vol="\U000f057e", mute="\U000f075f",
    bri="\U000f00e0", back="\U000f004d", close="\U000f0156", refresh="\U000f0450", chev="\U000f0142",
    bat="\U000f0079", batc="\U000f0084", eye="\U000f06d0", eyeoff="\U000f06d1", check="\U000f012c",
)


# ============================================================ helpers (no GUI)
def run(cmd, timeout=6.0):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:  # missing binary, timeout ...
        return 1, "", str(e)


def out(cmd, timeout=6.0):
    return run(cmd, timeout)[1].strip()


def have(x):
    return shutil.which(x) is not None


def spawn(cmd):
    try:
        subprocess.Popen(cmd, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except Exception as e:
        print("panel: spawn failed:", cmd, e, file=sys.stderr)


def notify(title, body=""):
    if have("notify-send"):
        spawn(["notify-send", "-a", "Panel", title, body])


# ---------------------------------------------------------------- colours
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _light(c):
    return colorsys.rgb_to_hls(c[0] / 255, c[1] / 255, c[2] / 255)[1]


def _hx(c):
    return "#%02x%02x%02x" % tuple(c)


def _rgba(c, a):
    return "rgba(%d,%d,%d,%.2f)" % (c[0], c[1], c[2], a)


def load_palette(path=COLORS_JSON):
    """Wallpaper colours -> the handful of colours the panel needs. Tolerates any json shape."""
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        data = {}
    flat = {}

    def walk(o, prefix=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, str(k).lower())
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, str):
                    flat.setdefault("color%d" % i, v) if re.fullmatch(r"#?[0-9a-fA-F]{6}", v) else None
                else:
                    walk(v, prefix)
        elif isinstance(o, str) and re.fullmatch(r"#?[0-9a-fA-F]{6}", o):
            flat.setdefault(prefix, "#" + o.lstrip("#"))

    walk(data)

    def pick(*names, default):
        for n in names:
            if n in flat:
                try:
                    return _hex_to_rgb(flat[n])
                except Exception:
                    pass
        return default

    bg = pick("background", "bg", "base", "surface", "color0", default=(30, 33, 48))
    fg = pick("foreground", "fg", "text", "on_surface", "color15", "color7", default=(232, 234, 246))
    ac = pick("primary", "accent", "color4", "color5", "color6", "color2", "color1", "color3",
              default=(180, 167, 245))
    if _light(bg) > 0.28:
        bg = _mix(bg, (0, 0, 0), 0.72)
    if _light(fg) < 0.7:
        fg = _mix(fg, (255, 255, 255), 0.7)
    if _light(ac) < 0.55:
        ac = _mix(ac, (255, 255, 255), 0.45)
    top = _mix(_mix(bg, ac, 0.16), (255, 255, 255), 0.04)
    bottom = _mix(bg, (0, 0, 0), 0.22)
    return dict(
        g1=_rgba(top, 0.93), g2=_rgba(bottom, 0.95), border=_rgba(ac, 0.75),
        fg=_hx(fg), dim=_rgba(fg, 0.62), faint=_rgba(fg, 0.10), faint2=_rgba(fg, 0.16),
        accent=_hx(ac), accent_b=_hx(_mix(ac, (110, 160, 255), 0.35)), accent_soft=_rgba(ac, 0.22),
        on_accent=_hx(_mix(bg, (0, 0, 0), 0.4)), tile=_rgba(_mix(bg, (255, 255, 255), 0.10), 0.62),
        err="#ff8da1", ok="#9be3b0",
    )


# ---------------------------------------------------------------- Wi-Fi (nmcli)
def wifi_enabled():
    return out(["nmcli", "radio", "wifi"]) == "enabled"


def wifi_dev():
    for line in out(["nmcli", "-t", "--escape", "no", "-f", "DEVICE,TYPE", "device"]).splitlines():
        p = line.split(":")
        if len(p) >= 2 and p[1] == "wifi":
            return p[0]
    return None


def parse_wifi_list(text):
    best = {}
    for line in text.splitlines():
        p = line.split(":", 4)
        if len(p) < 5 or not p[4]:
            continue
        inuse, sig, freq, sec, ssid = p
        try:
            sig = int(sig)
        except ValueError:
            sig = 0
        m = re.match(r"\d+", freq)
        mhz = int(m.group()) if m else 0
        band = "6 GHz" if mhz >= 5925 else "5 GHz" if mhz >= 4900 else "2.4 GHz" if mhz else ""
        sec = "" if sec in ("", "--") else sec
        n = dict(ssid=ssid, signal=sig, band=band, sec=sec, active=(inuse.strip() == "*"))
        old = best.get(ssid)
        if old is None or n["active"] or (not old["active"] and sig > old["signal"]):
            best[ssid] = n
    return sorted(best.values(), key=lambda n: (not n["active"], -n["signal"]))


def wifi_list():
    return parse_wifi_list(out(["nmcli", "-t", "--escape", "no", "-f", "IN-USE,SIGNAL,FREQ,SECURITY,SSID",
                                "device", "wifi", "list"], 8.0))


def wifi_saved():
    names = []
    for line in out(["nmcli", "-t", "--escape", "no", "-f", "NAME,TYPE", "connection", "show"]).splitlines():
        name, _, typ = line.rpartition(":")
        if typ == "802-11-wireless" and name != "Hotspot":
            names.append(name)
    return names


def wifi_ip(dev):
    if not dev:
        return ""
    t = out(["nmcli", "-g", "IP4.ADDRESS", "device", "show", dev])
    return t.splitlines()[0].split("/")[0] if t else ""


def wifi_rescan():
    run(["nmcli", "device", "wifi", "rescan"], 6.0)


def wifi_disconnect():
    d = wifi_dev()
    if d:
        run(["nmcli", "device", "disconnect", d], 10.0)


def wifi_forget(ssid):
    run(["nmcli", "connection", "delete", "id", ssid], 8.0)


def wifi_connect(ssid, pw=None, saved=False):
    """-> (ok, message)."""
    if saved:
        rc, o, e = run(["nmcli", "connection", "up", "id", ssid], 35.0)
    elif pw:
        rc, o, e = run(["nmcli", "device", "wifi", "connect", ssid, "password", pw], 35.0)
    else:
        rc, o, e = run(["nmcli", "device", "wifi", "connect", ssid], 35.0)
    if rc == 0:
        return True, ""
    if not saved:
        run(["nmcli", "connection", "delete", "id", ssid], 6.0)   # don't keep a profile with a bad password
    text = (e or o).strip()
    low = text.lower()
    if "secrets were required" in low or "password" in low or "802-1x" in low or "auth" in low:
        return False, "Wrong password"
    if "no network with ssid" in low or "not found" in low:
        return False, "Network out of range"
    if "timeout" in low or "timed out" in low:
        return False, "Timed out, try again"
    return False, (text.splitlines()[-1] if text else "Could not connect")[:48]


def internet_state():
    return out(["nmcli", "networking", "connectivity", "check"], 8.0)


def hotspot_active():
    for line in out(["nmcli", "-t", "--escape", "no", "-f", "NAME,TYPE", "connection", "show", "--active"]).splitlines():
        if line.rpartition(":")[0] == "Hotspot":
            return True
    return False


def set_hotspot(on):
    if on:
        d = wifi_dev()
        cmd = ["nmcli", "device", "wifi", "hotspot", "con-name", "Hotspot"]
        if d:
            cmd[4:4] = ["ifname", d]
        rc, o, e = run(cmd, 20.0)
        if rc != 0:
            notify("Hotspot failed", (e or o).strip()[-120:])
    else:
        run(["nmcli", "connection", "down", "id", "Hotspot"], 10.0)


# ---------------------------------------------------------------- Bluetooth
def bt_powered():
    return "Powered: yes" in out(["bluetoothctl", "show"])


def bt_set(on):
    run(["bluetoothctl", "power", "on" if on else "off"], 8.0)


def bt_devices():
    names = {}
    for line in out(["bluetoothctl", "devices"]).splitlines():
        p = line.split(" ", 2)
        if len(p) == 3 and p[0] == "Device":
            names[p[1]] = p[2]
    paired = set()
    for line in out(["bluetoothctl", "devices", "Paired"]).splitlines():
        p = line.split(" ", 2)
        if len(p) >= 2 and p[0] == "Device":
            paired.add(p[1])
    res = []
    for mac, name in list(names.items())[:14]:
        info = out(["bluetoothctl", "info", mac], 3.0)
        res.append(dict(mac=mac, name=name, connected="Connected: yes" in info,
                        paired=("Paired: yes" in info) or mac in paired))
    res.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    return res


def bt_toggle_device(mac, connected):
    rc, o, e = run(["bluetoothctl", "disconnect" if connected else "connect", mac], 20.0)
    return rc == 0 and "Failed" not in o


# ---------------------------------------------------------------- audio / brightness / battery / misc
def vol_get(src=False):
    s = out(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@" if src else "@DEFAULT_AUDIO_SINK@"])
    m = re.search(r"([\d.]+)", s)
    return (float(m.group(1)) if m else 0.0), ("MUTED" in s)


def vol_set(frac):
    run(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "%.2f" % max(0.0, min(1.0, frac))])


def mute_toggle(src=False):
    run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@" if src else "@DEFAULT_AUDIO_SINK@", "toggle"])


def bri_get():
    parts = out(["brightnessctl", "-m"]).split(",")
    try:
        return int(parts[3].rstrip("%"))
    except Exception:
        return None


def bri_set(pct):
    run(["brightnessctl", "set", "%d%%" % max(1, min(100, int(pct)))])


def battery():
    for d in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        try:
            cap = int(open(d + "/capacity").read().strip())
            st = open(d + "/status").read().strip()
            return cap, st
        except Exception:
            continue
    return None


def dnd_active():
    return "do-not-disturb" in out(["makoctl", "mode"]).split()


def dnd_toggle():
    run(["makoctl", "mode", "-t", "do-not-disturb"])


def night_tool():
    return "hyprsunset" if have("hyprsunset") else "wlsunset" if have("wlsunset") else None


def night_active():
    t = night_tool()
    return bool(t) and run(["pgrep", "-x", t])[0] == 0


def night_toggle():
    t = night_tool()
    if not t:
        return
    if night_active():
        run(["pkill", "-x", t])
    else:
        spawn(["hyprsunset", "-t", "4200"] if t == "hyprsunset" else ["wlsunset", "-t", "4200", "-T", "6500"])


PROFILES = ["power-saver", "balanced", "performance"]


def profile_get():
    return out(["powerprofilesctl", "get"]) or ""


def profile_cycle():
    cur = profile_get()
    try:
        nxt = PROFILES[(PROFILES.index(cur) + 1) % len(PROFILES)]
    except ValueError:
        nxt = "balanced"
    if run(["powerprofilesctl", "set", nxt])[0] != 0 and nxt == "performance":
        run(["powerprofilesctl", "set", "power-saver"])


def game_active():
    t = out(["hyprctl", "getoption", "animations:enabled", "-j"])
    try:
        return json.loads(t).get("int", 1) == 0
    except Exception:
        return False


def game_toggle():
    try:                                   # your rice's own game-mode logic, if it is still there
        sys.path.insert(0, os.path.join(RICE, "scripts"))
        import panelcore as pc
        pc.toggle_gamemode()
        return
    except Exception:
        pass
    if game_active():
        run(["hyprctl", "reload"])
    else:
        run(["hyprctl", "--batch", "keyword animations:enabled 0;keyword decoration:blur:enabled 0;"
                                    "keyword decoration:shadow:enabled 0"])


def airplane_active():
    return not wifi_enabled() and not bt_powered()


def airplane_toggle():
    on = not airplane_active()
    run(["nmcli", "radio", "all", "off" if on else "on"], 8.0)
    if have("bluetoothctl"):
        bt_set(not on)


def sig_icon(sig):
    return IC["wifi4"] if sig >= 75 else IC["wifi3"] if sig >= 50 else IC["wifi2"] if sig >= 25 else IC["wifi1"]


# ============================================================ GUI
CSS = Template("""
* { font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", monospace; font-size: 12px; color: $fg; }
window, .backdrop { background: transparent; }
.card { background-image: linear-gradient(to bottom right, $g1, $g2); border: 1px solid $border;
        border-radius: 22px; padding: 16px; box-shadow: 0 16px 44px rgba(0,0,0,0.5); }
button { background: none; background-image: none; border: none; box-shadow: none; text-shadow: none;
         padding: 0; min-height: 0; min-width: 0; border-radius: 14px; }
button:hover { background-color: $faint; }
label { background: none; }
.clock { font-size: 30px; font-weight: bold; }
.date, .dim, .sub { color: $dim; font-size: 11px; }
.section { color: $dim; font-size: 10px; font-weight: bold; margin-top: 8px; margin-bottom: 2px; }
.title { font-size: 16px; font-weight: bold; }
.big { font-size: 15px; font-weight: bold; }
.glyph { font-size: 18px; }
.err { color: $err; }
.ok { color: $ok; }
.chip { background-color: $faint; border-radius: 14px; padding: 9px 14px; border: 1px solid $faint; }
.chip:hover { background-color: $faint2; }
.chip.primary { background-image: linear-gradient(to right, $accent_b, $accent); color: $on_accent;
                border-color: transparent; }
.chip.primary label { color: $on_accent; font-weight: bold; }
.chip.danger { background-color: rgba(255,120,140,0.20); border-color: rgba(255,120,140,0.5); }
.iconbtn { background-color: $faint; border-radius: 14px; padding: 8px 10px; }
.iconbtn:hover { background-color: $faint2; }
.iconbtn label { font-size: 15px; }
.tile { background-color: $tile; border-radius: 16px; border: 1px solid $faint; }
.tile button { border-radius: 16px; padding: 10px 10px; }
.tile .tilego { padding: 10px 4px; border-radius: 0 16px 16px 0; }
.tile.on { background-image: linear-gradient(to bottom right, $accent_b, $accent); border-color: transparent; }
.tile.on label { color: $on_accent; }
.tile.on .sub { color: $on_accent; }
.tile.on button:hover { background-color: rgba(255,255,255,0.18); }
.tile .tilename { font-weight: bold; font-size: 12px; }
.netcard { background-color: $accent_soft; border: 1px solid $border; border-radius: 16px; padding: 12px; }
.joinbox { background-color: $faint; border: 1px solid $border; border-radius: 16px; padding: 12px; }
.row { border-radius: 14px; }
.row button { padding: 9px 8px; }
.row .xbtn { padding: 9px 10px; }
.row.active { background-color: $accent_soft; }
entry { background-color: rgba(255,255,255,0.09); background-image: none; border: 1px solid $accent_b;
        border-radius: 12px; padding: 9px 12px; min-height: 22px; color: $fg; caret-color: $accent;
        box-shadow: none; }
entry:focus { border-color: $accent; background-color: rgba(255,255,255,0.14); }
scale trough { min-height: 8px; border-radius: 8px; background-color: $faint2; border: none; }
scale highlight { background-image: linear-gradient(to right, $accent_b, $accent); border-radius: 8px; border: none; }
scale slider { min-width: 18px; min-height: 18px; border-radius: 99px; background-color: $fg; background-image: none;
               border: none; margin: -6px; box-shadow: 0 2px 6px rgba(0,0,0,0.4); }
switch { background-color: $faint2; background-image: none; border-radius: 99px; border: none;
         min-width: 50px; min-height: 26px; box-shadow: none; }
switch:checked { background-image: linear-gradient(to right, $accent_b, $accent); }
switch slider { background-color: $on_accent; background-image: none; border-radius: 99px; border: none;
                min-width: 22px; min-height: 22px; margin: 2px; box-shadow: none; }
scrolledwindow { background: none; }
scrollbar { background: none; border: none; }
scrollbar slider { min-width: 4px; border-radius: 4px; background-color: $faint2; border: none; }
""")


def build_gui():
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    try:
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import GtkLayerShell
    except Exception:
        GtkLayerShell = None
    from gi.repository import Gtk, Gdk, GLib, Pango, Gio

    def bg(fn, cb=None):
        def work():
            try:
                r = fn()
            except Exception as e:
                print("panel: worker error:", repr(e), file=sys.stderr)
                r = None
            if cb:
                GLib.idle_add(lambda: (cb(r), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def lab(text="", cls=None, xalign=0.0, ellipsize=False, chars=0):
        l = Gtk.Label(label=text)
        l.set_xalign(xalign)
        if cls:
            for c in cls.split():
                l.get_style_context().add_class(c)
        if ellipsize:
            l.set_ellipsize(Pango.EllipsizeMode.END)
            if chars:
                l.set_max_width_chars(chars)
        return l

    def button(child, cb, cls=""):
        b = Gtk.Button()
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_can_focus(False)
        b.add(child)
        for c in cls.split():
            b.get_style_context().add_class(c)
        b.connect("clicked", lambda *_: cb())
        return b

    def chip(text, cb, cls=""):
        return button(lab(text, xalign=0.5), cb, "chip " + cls)

    def iconbtn(glyph, cb):
        return button(lab(glyph, xalign=0.5), cb, "iconbtn")

    def clear(box):
        for c in box.get_children():
            c.destroy()

    class Panel:
        def __init__(self):
            self.visible = False
            self.page = "main"
            self.dragging = False
            self.busy = False
            self.msg = None            # (text, cls, until)
            self.join_ssid = None
            self.join_sec = ""
            self.wifi_data = None
            self.bt_data = None
            self.state = {}
            self.tick_n = 0
            self.css = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.css,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)   # beat ~/.config/gtk-3.0/gtk.css
            self.apply_css()
            self.build_window()
            self.watch_colors()

        # ------------------------------------------------------------ window
        def apply_css(self):
            try:
                self.css.load_from_data(CSS.safe_substitute(load_palette()).encode())
            except Exception as e:
                print("panel: css problem:", e, file=sys.stderr)

        def build_window(self):
            w = self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            w.set_title("hypr-rice-panel")
            w.set_decorated(False)
            w.set_app_paintable(True)
            scr = Gdk.Screen.get_default()
            vis = scr.get_rgba_visual()
            if vis:
                w.set_visual(vis)
            if GtkLayerShell:
                GtkLayerShell.init_for_window(w)
                GtkLayerShell.set_layer(w, GtkLayerShell.Layer.TOP)
                GtkLayerShell.set_namespace(w, NAMESPACE)
                for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                             GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
                    GtkLayerShell.set_anchor(w, edge, True)
                GtkLayerShell.set_margin(w, GtkLayerShell.Edge.TOP, BAR_H)
                GtkLayerShell.set_exclusive_zone(w, -1)
                try:
                    GtkLayerShell.set_keyboard_mode(w, GtkLayerShell.KeyboardMode.ON_DEMAND)
                except Exception:
                    GtkLayerShell.set_keyboard_interactivity(w, True)
            else:
                w.set_default_size(560, 760)
            w.connect("key-press-event", self.on_key)

            root = Gtk.EventBox()
            root.set_visible_window(False)
            root.connect("button-press-event", lambda *_: (self.hide(), True)[1])
            self.fixed = Gtk.Fixed()
            self.cur_y = -2000.0
            self.anim_id = None
            shield = self.shield = Gtk.EventBox()
            shield.set_visible_window(False)
            shield.connect("button-press-event", lambda *_: True)
            for m, v in (("top", 8), ("start", 20), ("end", 20), ("bottom", 24)):
                getattr(shield, "set_margin_" + m)(v)
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            card.get_style_context().add_class("card")
            card.set_size_request(CARD_W, -1)
            self.stack = Gtk.Stack()
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            self.stack.set_transition_duration(200)
            self.stack.set_vhomogeneous(False)
            self.stack.add_named(self.build_main(), "main")
            self.stack.add_named(self.build_wifi(), "wifi")
            self.stack.add_named(self.build_bt(), "bt")
            card.pack_start(self.stack, False, False, 0)
            self.card = card
            shield.add(card)
            self.fixed.put(shield, 0, int(self.cur_y))
            self.fixed.connect("size-allocate", lambda *_: self.place())
            shield.connect("size-allocate", lambda *_: GLib.idle_add(lambda: (self.place(), False)[1]))
            root.add(self.fixed)
            w.add(root)

        # the card slides down out of the pill bar and back up into it
        def place(self):
            W = self.fixed.get_allocated_width()
            w = self.shield.get_preferred_width()[1]
            self.fixed.move(self.shield, max(0, (W - w) // 2), int(self.cur_y))

        def closed_y(self):
            return -(self.shield.get_preferred_height()[1] + 12)

        def animate(self, show):
            if self.anim_id:
                GLib.source_remove(self.anim_id)
                self.anim_id = None
            closed = float(self.closed_y())
            start, end = self.cur_y, (0.0 if show else closed)
            t0, dur = time.monotonic(), (0.30 if show else 0.20)

            def step():
                t = min(1.0, (time.monotonic() - t0) / dur)
                e = 1 - (1 - t) ** 3 if show else t * t        # ease-out going down, ease-in going up
                self.cur_y = start + (end - start) * e
                p = 1 - self.cur_y / closed if closed else 1.0
                self.card.set_opacity(max(0.0, min(1.0, p * 1.8)))
                self.place()
                if t >= 1.0:
                    self.anim_id = None
                    if not show and not self.visible:
                        self.win.hide()
                    return False
                return True
            self.anim_id = GLib.timeout_add(16, step)

        def watch_colors(self):
            """Recolour as soon as the wallpaper script rewrites colors.json, even while hidden."""
            try:
                self.mon = Gio.File.new_for_path(os.path.dirname(COLORS_JSON)).monitor_directory(
                    Gio.FileMonitorFlags.NONE, None)
                self.mon.connect("changed", lambda _m, f, _o, _e: (
                    f and f.get_basename() == "colors.json"
                    and GLib.timeout_add(200, lambda: (self.apply_css(), False)[1])))
            except Exception as e:
                print("panel: could not watch colors.json:", e, file=sys.stderr)

        def on_key(self, _w, ev):
            if ev.keyval == Gdk.KEY_Escape:
                if self.join_ssid:
                    self.join_close()
                elif self.page != "main":
                    self.goto("main")
                else:
                    self.hide()
                return True
            return False

        def show(self):
            if self.visible:
                return
            self.visible = True
            self.apply_css()
            self.goto("main", animate=False)
            if not self.win.get_mapped():
                self.cur_y = float(self.closed_y())
                self.card.set_opacity(0)
                self.place()
            self.win.show_all()
            self.join_box.hide()
            self.power_rev.set_reveal_child(False)
            self.animate(True)
            self.refresh_state()
            self.update_clock()
            self.tick_n = 0
            GLib.timeout_add(2000, self.tick)

        def hide(self):
            if not self.visible:
                return
            self.visible = False
            self.animate(False)

        def toggle(self):
            self.hide() if self.visible else self.show()

        def goto(self, name, animate=True):
            self.page = name
            if not animate:
                self.stack.set_transition_duration(0)
            self.stack.set_visible_child_name(name)
            if not animate:
                self.stack.set_transition_duration(200)
            if name == "wifi":
                self.join_close()
                self.wifi_refresh(rescan=True)
            elif name == "bt":
                self.bt_refresh(scan=True)

        def tick(self):
            if not self.visible:
                return False
            self.tick_n += 1
            self.update_clock()
            if self.page == "main":
                self.refresh_state()
            elif self.page == "wifi" and self.tick_n % 2 == 0 and not self.busy:
                self.wifi_refresh()
            elif self.page == "bt" and self.tick_n % 3 == 0:
                self.bt_refresh()
            return True

        # ------------------------------------------------------------ main page
        def build_main(self):
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            head = Gtk.Box(spacing=8)
            tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.clock = lab("", "clock")
            self.date = lab("", "date")
            tb.pack_start(self.clock, False, False, 0)
            tb.pack_start(self.date, False, False, 0)
            head.pack_start(tb, True, True, 0)
            self.bat_lbl = lab("", "dim", xalign=1.0)
            head.pack_start(self.bat_lbl, False, False, 4)
            head.pack_start(iconbtn(IC["cog"], lambda: (self.hide(), spawn(["python3", RICE + "/scripts/settings.py"]))),
                            False, False, 0)
            page.pack_start(head, False, False, 0)

            self.tiles = {}
            grid = Gtk.Grid()
            grid.set_column_spacing(8)
            grid.set_row_spacing(8)
            grid.set_column_homogeneous(True)
            specs = []
            if have("nmcli"):
                specs.append(("wifi", "Wi-Fi", lambda: self.act(self.toggle_wifi), "wifi"))
            if have("bluetoothctl"):
                specs.append(("bt", "Bluetooth", lambda: self.act(self.toggle_bt), "bt"))
            if have("nmcli"):
                specs.append(("hotspot", "Hotspot", lambda: self.act(lambda: set_hotspot(not hotspot_active())), None))
            if have("makoctl"):
                specs.append(("dnd", "Do not disturb", lambda: self.act(dnd_toggle), None))
            if night_tool():
                specs.append(("night", "Night light", lambda: self.act(night_toggle), None))
            specs.append(("game", "Game mode", lambda: self.act(game_toggle), None))
            if have("wpctl"):
                specs.append(("mic", "Microphone", lambda: self.act(lambda: mute_toggle(True)), None))
            if have("nmcli"):
                specs.append(("air", "Airplane", lambda: self.act(airplane_toggle), None))
            if have("powerprofilesctl"):
                specs.append(("prof", "Power", lambda: self.act(profile_cycle), None))
            for i, (key, title, cb, go) in enumerate(specs):
                grid.attach(self.make_tile(key, title, cb, go), i % 3, i // 3, 1, 1)
            page.pack_start(grid, False, False, 0)

            if have("wpctl"):
                self.vol_ic = lab(IC["vol"], "glyph", 0.5)
                self.vol_sc, self.vol_pc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1), lab("", "dim", 1.0)
                page.pack_start(self.slider_row(self.vol_ic, self.vol_sc, self.vol_pc,
                                                lambda: self.act(mute_toggle), self.on_vol), False, False, 0)
            if have("brightnessctl") and bri_get() is not None:
                self.bri_sc, self.bri_pc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1), lab("", "dim", 1.0)
                page.pack_start(self.slider_row(lab(IC["bri"], "glyph", 0.5), self.bri_sc, self.bri_pc,
                                                None, self.on_bri), False, False, 0)

            foot = Gtk.Box(spacing=8, homogeneous=True)
            foot.pack_start(chip("Settings", lambda: (self.hide(), spawn(["python3", RICE + "/scripts/settings.py"]))), True, True, 0)
            if have("hyprlock"):
                foot.pack_start(chip("Lock", lambda: (self.hide(), spawn(["hyprlock"]))), True, True, 0)
            foot.pack_start(chip("Power", lambda: self.power_rev.set_reveal_child(not self.power_rev.get_reveal_child())), True, True, 0)
            page.pack_start(foot, False, False, 0)

            self.power_rev = Gtk.Revealer()
            self.power_rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
            pb = Gtk.Box(spacing=8, homogeneous=True)
            self.power_btns = []
            for text, cmd in (("Sleep", ["systemctl", "suspend"]), ("Log out", ["hyprctl", "dispatch", "exit"]),
                              ("Restart", ["systemctl", "reboot"]), ("Shut down", ["systemctl", "poweroff"])):
                b = chip(text, lambda: None, "danger" if text != "Sleep" else "")
                self.power_btns.append((b, text, cmd))
                pb.pack_start(b, True, True, 0)
            for b, text, cmd in self.power_btns:
                self.wire_power(b, text, cmd)
            self.power_rev.add(pb)
            page.pack_start(self.power_rev, False, False, 0)
            return page

        def wire_power(self, b, text, cmd):
            label = b.get_child()
            armed = {"t": 0}

            def clicked(*_):
                if text == "Sleep" or time.time() - armed["t"] < 3:
                    self.hide()
                    spawn(cmd)
                    return
                armed["t"] = time.time()
                label.set_text("Sure?")
                GLib.timeout_add(3000, lambda: (label.set_text(text), False)[1])
            b.connect("clicked", clicked)

        def make_tile(self, key, title, cb, go):
            box = Gtk.Box()
            box.get_style_context().add_class("tile")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            ic = lab("", "glyph")
            nm = lab(title, "tilename", ellipsize=True, chars=11)
            sub = lab("", "sub", ellipsize=True, chars=11)
            inner.pack_start(ic, False, False, 0)
            inner.pack_start(nm, False, False, 0)
            inner.pack_start(sub, False, False, 0)
            main = button(inner, cb)
            box.pack_start(main, True, True, 0)
            if go:
                gb = button(lab(IC["chev"], xalign=0.5), lambda: self.goto(go), "tilego")
                box.pack_start(gb, False, False, 0)
            self.tiles[key] = (box, ic, sub)
            return box

        def set_tile(self, key, on, glyph, sub):
            t = self.tiles.get(key)
            if not t:
                return
            box, ic, sb = t
            ctx = box.get_style_context()
            ctx.add_class("on") if on else ctx.remove_class("on")
            ic.set_text(glyph)
            sb.set_text(sub)

        def slider_row(self, ic, sc, pc, mute_cb, on_change):
            row = Gtk.Box(spacing=10)
            row.pack_start(button(ic, mute_cb, "iconbtn") if mute_cb else ic, False, False, 4)
            sc.set_draw_value(False)
            sc.set_hexpand(True)
            sc.connect("button-press-event", lambda *_: (setattr(self, "dragging", True), False)[1])
            sc.connect("button-release-event", lambda *_: (setattr(self, "dragging", False), False)[1])
            sc.connect("value-changed", on_change)
            row.pack_start(sc, True, True, 0)
            pc.set_width_chars(4)
            row.pack_start(pc, False, False, 4)
            return row

        def on_vol(self, sc):
            v = sc.get_value()
            self.vol_pc.set_text("%d%%" % v)
            if self.dragging:
                self.debounce("vol", lambda: bg(lambda: vol_set(v / 100)))

        def on_bri(self, sc):
            v = sc.get_value()
            self.bri_pc.set_text("%d%%" % v)
            if self.dragging:
                self.debounce("bri", lambda: bg(lambda: bri_set(v)))

        def debounce(self, key, fn, ms=70):
            tm = getattr(self, "_tm", {})
            self._tm = tm
            if tm.get(key):
                GLib.source_remove(tm[key])
            tm[key] = GLib.timeout_add(ms, lambda: (tm.pop(key, None), fn(), False)[2])

        def act(self, fn):
            bg(fn, lambda _: self.refresh_state())

        def toggle_wifi(self):
            run(["nmcli", "radio", "wifi", "off" if wifi_enabled() else "on"], 8.0)

        def toggle_bt(self):
            bt_set(not bt_powered())

        def update_clock(self):
            self.clock.set_text(time.strftime("%H:%M"))
            self.date.set_text(time.strftime("%A, %d %B"))

        def refresh_state(self):
            def gather():
                s = {}
                if "wifi" in self.tiles:
                    on = wifi_enabled()
                    act = next((n for n in wifi_list() if n["active"]), None) if on else None
                    s["wifi"] = (on, act["ssid"] if act else None)
                if "bt" in self.tiles:
                    s["bt"] = bt_powered()
                if "hotspot" in self.tiles:
                    s["hotspot"] = hotspot_active()
                if "dnd" in self.tiles:
                    s["dnd"] = dnd_active()
                if "night" in self.tiles:
                    s["night"] = night_active()
                s["game"] = game_active()
                if "mic" in self.tiles:
                    s["mic"] = vol_get(True)[1]
                if "air" in self.tiles:
                    s["air"] = airplane_active()
                if "prof" in self.tiles:
                    s["prof"] = profile_get()
                if hasattr(self, "vol_sc"):
                    s["vol"] = vol_get()
                if hasattr(self, "bri_sc"):
                    s["bri"] = bri_get()
                s["bat"] = battery()
                return s
            bg(gather, self.paint_state)

        def paint_state(self, s):
            if not s or not self.visible:
                return
            if "wifi" in s:
                on, ssid = s["wifi"]
                self.set_tile("wifi", on, IC["wifi4"] if on else IC["wifi_off"], (ssid or "Not connected") if on else "Off")
            if "bt" in s:
                self.set_tile("bt", s["bt"], IC["bt"] if s["bt"] else IC["bt_off"], "On" if s["bt"] else "Off")
            if "hotspot" in s:
                self.set_tile("hotspot", s["hotspot"], IC["hotspot"], "On" if s["hotspot"] else "Off")
            if "dnd" in s:
                self.set_tile("dnd", s["dnd"], IC["dnd"], "On" if s["dnd"] else "Off")
            if "night" in s:
                self.set_tile("night", s["night"], IC["night"], "On" if s["night"] else "Off")
            self.set_tile("game", s.get("game", False), IC["game"], "On" if s.get("game") else "Off")
            if "mic" in s:
                self.set_tile("mic", not s["mic"], IC["mic_off"] if s["mic"] else IC["mic"], "Muted" if s["mic"] else "On")
            if "air" in s:
                self.set_tile("air", s["air"], IC["air"], "On" if s["air"] else "Off")
            if "prof" in s:
                self.set_tile("prof", s["prof"] == "performance", IC["prof"], (s["prof"] or "n/a").replace("-", " "))
            if "vol" in s and not self.dragging:
                v, muted = s["vol"]
                self.vol_ic.set_text(IC["mute"] if muted or v == 0 else IC["vol"])
                self.vol_sc.set_value(round(v * 100))
                self.vol_pc.set_text("%d%%" % round(v * 100))
            if s.get("bri") is not None and hasattr(self, "bri_sc") and not self.dragging:
                self.bri_sc.set_value(s["bri"])
                self.bri_pc.set_text("%d%%" % s["bri"])
            b = s.get("bat")
            self.bat_lbl.set_text("" if not b else "%s %d%%" % (IC["batc"] if b[1] == "Charging" else IC["bat"], b[0]))

        # ------------------------------------------------------------ shared page header
        def page_header(self, title, widget):
            h = Gtk.Box(spacing=10)
            h.pack_start(iconbtn(IC["back"], lambda: self.goto("main")), False, False, 0)
            tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            tb.pack_start(lab(title, "title"), False, False, 0)
            sub = lab("", "sub", ellipsize=True, chars=34)
            tb.pack_start(sub, False, False, 0)
            h.pack_start(tb, True, True, 0)
            if widget:
                widget.set_valign(Gtk.Align.CENTER)
                h.pack_end(widget, False, False, 0)
            return h, sub

        def set_msg(self, text, cls="", secs=5):
            self.msg = (text, cls, time.time() + secs) if text else None

        def paint_sub(self, sub, default):
            if self.msg and time.time() < self.msg[2]:
                sub.set_text(self.msg[0])
                ctx = sub.get_style_context()
                ctx.remove_class("err")
                ctx.remove_class("ok")
                if self.msg[1]:
                    ctx.add_class(self.msg[1])
            else:
                self.msg = None
                sub.set_text(default)
                sub.get_style_context().remove_class("err")
                sub.get_style_context().remove_class("ok")

        # ------------------------------------------------------------ Wi-Fi page
        def build_wifi(self):
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.w_sw = Gtk.Switch()
            self.w_sw_id = self.w_sw.connect("notify::active", self.wifi_switch)
            head, self.w_sub = self.page_header("Wi-Fi", self.w_sw)
            page.pack_start(head, False, False, 0)

            self.w_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            self.w_card.get_style_context().add_class("netcard")
            self.w_card_name = lab("", "big", ellipsize=True, chars=30)
            self.w_card_info = lab("", "sub")
            self.w_card.pack_start(self.w_card_name, False, False, 0)
            self.w_card.pack_start(self.w_card_info, False, False, 0)
            ab = Gtk.Box(spacing=8, homogeneous=True)
            ab.pack_start(chip("Disconnect", lambda: bg(wifi_disconnect, lambda _: self.wifi_refresh())), True, True, 0)
            ab.pack_start(chip("Forget", lambda: self.wifi_forget_active()), True, True, 0)
            self.w_card.pack_start(ab, False, False, 4)
            page.pack_start(self.w_card, False, False, 0)

            # --- the password box: always built, shown when you tap a locked network
            self.join_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            self.join_box.get_style_context().add_class("joinbox")
            self.join_lbl = lab("", "big", ellipsize=True, chars=32)
            self.join_box.pack_start(self.join_lbl, False, False, 0)
            erow = Gtk.Box(spacing=8)
            self.entry = Gtk.Entry()
            self.entry.set_visibility(False)
            self.entry.set_placeholder_text("Password")
            self.entry.set_hexpand(True)
            self.entry.set_can_focus(True)
            self.entry.connect("activate", lambda *_: self.wifi_join())
            erow.pack_start(self.entry, True, True, 0)
            self.eye = iconbtn(IC["eye"], self.toggle_eye)
            erow.pack_start(self.eye, False, False, 0)
            self.join_box.pack_start(erow, False, False, 0)
            brow = Gtk.Box(spacing=8, homogeneous=True)
            brow.pack_start(chip("Cancel", self.join_close), True, True, 0)
            self.join_btn = chip("Join", self.wifi_join, "primary")
            brow.pack_start(self.join_btn, True, True, 0)
            self.join_box.pack_start(brow, False, False, 0)
            self.join_box.set_no_show_all(True)
            page.pack_start(self.join_box, False, False, 0)

            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.set_propagate_natural_height(True)
            sw.set_min_content_height(160)
            sw.set_max_content_height(330)
            self.w_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            sw.add(self.w_list)
            page.pack_start(sw, True, True, 0)

            links = Gtk.Box(spacing=8, homogeneous=True)
            links.pack_start(chip("Rescan", lambda: self.wifi_refresh(rescan=True)), True, True, 0)
            if have("nm-connection-editor"):
                links.pack_start(chip("Network editor", lambda: (self.hide(), spawn(["nm-connection-editor"]))), True, True, 0)
            page.pack_start(links, False, False, 0)
            return page

        def toggle_eye(self):
            vis = not self.entry.get_visibility()
            self.entry.set_visibility(vis)
            self.eye.get_child().set_text(IC["eyeoff"] if vis else IC["eye"])

        def wifi_switch(self, sw, _p):
            on = sw.get_active()
            bg(lambda: run(["nmcli", "radio", "wifi", "on" if on else "off"], 8.0),
               lambda _: GLib.timeout_add(1200, lambda: (self.wifi_refresh(rescan=on), False)[1]))

        def wifi_refresh(self, rescan=False):
            def work():
                if rescan:
                    wifi_rescan()
                on = wifi_enabled()
                dev = wifi_dev()
                nets = wifi_list() if on else []
                return dict(on=on, nets=nets, saved=wifi_saved(), ip=wifi_ip(dev) if on else "")
            bg(work, self.wifi_paint)

        def wifi_paint(self, r):
            if not r or self.page != "wifi" or not self.visible:
                return
            self.wifi_data = r
            self.w_sw.handler_block(self.w_sw_id)
            self.w_sw.set_active(r["on"])
            self.w_sw.handler_unblock(self.w_sw_id)
            act = next((n for n in r["nets"] if n["active"]), None)
            if self.busy:
                pass
            else:
                self.paint_sub(self.w_sub, (act["ssid"] if act else "Not connected") if r["on"] else "Off")
            if act:
                self.w_card_name.set_text(act["ssid"])
                self.w_card_info.set_text("  ·  ".join(x for x in (act["band"], "%d%% signal" % act["signal"],
                                                                   act["sec"].split()[0] if act["sec"] else "Open", r["ip"]) if x))
                self.w_card.show_all()
            else:
                self.w_card.hide()
            clear(self.w_list)
            if not r["on"]:
                self.w_list.pack_start(lab("Wi-Fi is off", "dim", 0.5), False, False, 24)
            else:
                saved = [n for n in r["nets"] if not n["active"] and n["ssid"] in r["saved"]]
                avail = [n for n in r["nets"] if not n["active"] and n["ssid"] not in r["saved"]]
                if saved:
                    self.w_list.pack_start(lab("SAVED", "section"), False, False, 0)
                    for n in saved:
                        self.w_list.pack_start(self.net_row(n, True), False, False, 0)
                self.w_list.pack_start(lab("AVAILABLE", "section"), False, False, 0)
                for n in avail:
                    self.w_list.pack_start(self.net_row(n, False), False, False, 0)
                if not avail:
                    self.w_list.pack_start(lab("No other networks found", "dim", 0.5), False, False, 12)
            self.w_list.show_all()

        def net_row(self, n, saved):
            row = Gtk.Box(spacing=0)
            row.get_style_context().add_class("row")
            inner = Gtk.Box(spacing=12)
            inner.pack_start(lab(sig_icon(n["signal"]), "glyph"), False, False, 6)
            tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            tb.pack_start(lab(n["ssid"], "big", ellipsize=True, chars=24), False, False, 0)
            tb.pack_start(lab("%s  ·  %d%%" % (n["band"], n["signal"]), "sub"), False, False, 0)
            inner.pack_start(tb, True, True, 0)
            if n["sec"]:
                inner.pack_end(lab(IC["lock"], "dim"), False, False, 6)
            row.pack_start(button(inner, lambda nn=n, sv=saved: self.wifi_tap(nn, sv)), True, True, 0)
            if saved:
                x = button(lab(IC["close"], xalign=0.5), lambda s=n["ssid"]: (bg(lambda: wifi_forget(s), lambda _: self.wifi_refresh())), "xbtn")
                row.pack_start(x, False, False, 0)
            return row

        def wifi_tap(self, n, saved):
            if saved or not n["sec"]:
                self.wifi_connect(n["ssid"], None, saved)
            else:
                self.join_ssid, self.join_sec = n["ssid"], n["sec"]
                self.join_lbl.set_text("Join " + n["ssid"])
                self.entry.set_text("")
                self.entry.set_visibility(False)
                self.eye.get_child().set_text(IC["eye"])
                self.join_box.set_no_show_all(False)
                self.join_box.show_all()
                self.join_box.set_no_show_all(True)
                self.set_msg("")
                self.entry.grab_focus()

        def join_close(self):
            self.join_ssid = None
            self.join_box.hide()

        def wifi_join(self):
            ssid, pw = self.join_ssid, self.entry.get_text()
            if not ssid:
                return
            need = 5 if "WEP" in self.join_sec and "WPA" not in self.join_sec else 8
            if len(pw) < need:
                self.set_msg("Password needs at least %d characters" % need, "err")
                self.paint_sub(self.w_sub, "")
                return
            self.join_close()
            self.wifi_connect(ssid, pw, False)

        def wifi_connect(self, ssid, pw, saved):
            if self.busy:
                return
            self.busy = True
            self.set_msg("Connecting to %s…" % ssid, "", 40)
            self.paint_sub(self.w_sub, "")

            def done(r):
                self.busy = False
                ok, why = r if r else (False, "Could not connect")
                if ok:
                    self.set_msg("Connected to " + ssid, "ok", 4)
                    bg(internet_state, self.check_portal)
                else:
                    self.set_msg(why, "err", 7)
                    if why == "Wrong password" and not saved:
                        # let them try again straight away
                        self.join_ssid = ssid
                        self.join_lbl.set_text("Join " + ssid)
                        self.join_box.set_no_show_all(False)
                        self.join_box.show_all()
                        self.join_box.set_no_show_all(True)
                        self.entry.grab_focus()
                self.paint_sub(self.w_sub, "")
                self.wifi_refresh()
                self.refresh_state()
            bg(lambda: wifi_connect(ssid, pw, saved), done)

        def check_portal(self, st):
            if st == "portal":
                self.set_msg("This network needs a login, opening it…", "", 6)
                notify("Wi-Fi", "This network needs a login. Opening the sign-in page.")
                spawn(["xdg-open", "http://neverssl.com"])

        def wifi_forget_active(self):
            act = next((n for n in (self.wifi_data or {}).get("nets", []) if n["active"]), None)
            if act:
                bg(lambda: wifi_forget(act["ssid"]), lambda _: self.wifi_refresh())

        # ------------------------------------------------------------ Bluetooth page
        def build_bt(self):
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.b_sw = Gtk.Switch()
            self.b_sw_id = self.b_sw.connect("notify::active", self.bt_switch)
            head, self.b_sub = self.page_header("Bluetooth", self.b_sw)
            page.pack_start(head, False, False, 0)
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.set_propagate_natural_height(True)
            sw.set_min_content_height(160)
            sw.set_max_content_height(330)
            self.b_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            sw.add(self.b_list)
            page.pack_start(sw, True, True, 0)
            links = Gtk.Box(spacing=8, homogeneous=True)
            links.pack_start(chip("Scan", lambda: self.bt_refresh(scan=True)), True, True, 0)
            if have("blueman-manager"):
                links.pack_start(chip("Bluetooth manager", lambda: (self.hide(), spawn(["blueman-manager"]))), True, True, 0)
            page.pack_start(links, False, False, 0)
            return page

        def bt_switch(self, sw, _p):
            on = sw.get_active()
            bg(lambda: bt_set(on), lambda _: GLib.timeout_add(900, lambda: (self.bt_refresh(), False)[1]))

        def bt_refresh(self, scan=False):
            def work():
                if scan and bt_powered():
                    run(["bluetoothctl", "--timeout", "5", "scan", "on"], 8.0)
                p = bt_powered()
                return dict(on=p, devs=bt_devices() if p else [])
            bg(work, self.bt_paint)

        def bt_paint(self, r):
            if not r or self.page != "bt" or not self.visible:
                return
            self.b_sw.handler_block(self.b_sw_id)
            self.b_sw.set_active(r["on"])
            self.b_sw.handler_unblock(self.b_sw_id)
            conn = [d["name"] for d in r["devs"] if d["connected"]]
            self.paint_sub(self.b_sub, ("Connected: " + ", ".join(conn)) if conn else ("On" if r["on"] else "Off"))
            clear(self.b_list)
            if not r["on"]:
                self.b_list.pack_start(lab("Bluetooth is off", "dim", 0.5), False, False, 24)
            elif not r["devs"]:
                self.b_list.pack_start(lab("No devices yet. Put one in pairing mode and tap Scan.", "dim", 0.5, True, 40),
                                       False, False, 24)
            else:
                for d in r["devs"]:
                    row = Gtk.Box()
                    row.get_style_context().add_class("row")
                    if d["connected"]:
                        row.get_style_context().add_class("active")
                    inner = Gtk.Box(spacing=12)
                    inner.pack_start(lab(IC["bt"], "glyph"), False, False, 6)
                    tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    tb.pack_start(lab(d["name"], "big", ellipsize=True, chars=28), False, False, 0)
                    tb.pack_start(lab("Connected" if d["connected"] else ("Paired" if d["paired"] else "Tap to pair"), "sub"),
                                  False, False, 0)
                    inner.pack_start(tb, True, True, 0)
                    row.pack_start(button(inner, lambda dd=d: self.bt_tap(dd)), True, True, 0)
                    self.b_list.pack_start(row, False, False, 0)
            self.b_list.show_all()

        def bt_tap(self, d):
            self.set_msg(("Disconnecting " if d["connected"] else "Connecting to ") + d["name"] + "…", "", 20)
            self.paint_sub(self.b_sub, "")

            def work():
                if not d["paired"]:
                    run(["bluetoothctl", "pair", d["mac"]], 25.0)
                    run(["bluetoothctl", "trust", d["mac"]], 5.0)
                return bt_toggle_device(d["mac"], d["connected"])

            def done(ok):
                self.set_msg("" if ok else "Could not connect", "" if ok else "err", 5)
                self.paint_sub(self.b_sub, "")
                self.bt_refresh()
            bg(work, done)

    return Panel, GLib, Gtk


# ============================================================ main
def single_instance():
    try:
        pid = int(open(LOCK).read().strip())
        if pid != os.getpid():
            os.kill(pid, 0)
            if "panel.py" in open("/proc/%d/cmdline" % pid).read():
                os.kill(pid, signal.SIGUSR1)
                return False
    except Exception:
        pass
    try:
        with open(LOCK, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print("panel: could not write lock:", e, file=sys.stderr)
    return True


def main():
    if not single_instance():
        return
    Panel, GLib, Gtk = build_gui()
    p = Panel()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, lambda: (p.toggle(), True)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, lambda: (p.apply_css(), True)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: (Gtk.main_quit(), False)[1])
    if "--hidden" not in sys.argv:
        p.show()
    try:
        Gtk.main()
    finally:
        try:
            if open(LOCK).read().strip() == str(os.getpid()):
                os.remove(LOCK)
        except Exception:
            pass


if __name__ == "__main__":
    main()
