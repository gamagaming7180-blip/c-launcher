#!/usr/bin/env python3
"""C Launcher Settings: one settings app in the same look as the control panel. Colours follow the wallpaper live.
  settings.py [page]     open (pages: wifi bluetooth apps notifications sound display personalize storage battery
                         security location wellbeing about)      settings.py --track   screen-time tracker (autostart)
Needs python-gobject gtk3. Reuses panelcore.py for every system call; missing tools just hide their rows."""
import datetime, glob, json, os, shutil, subprocess as sp, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panelcore as pc
RICE, GEN = pc.RICE, os.path.join(pc.RICE, "generated")
WB = os.path.join(os.path.expanduser("~/.local/share"), "c-launcher-wellbeing")

if "--track" in sys.argv:   # focus-time per app, one json per day; polls the active window every 5 s
    os.makedirs(WB, exist_ok=True)
    while True:
        try:
            w = json.loads(pc.sh(["hyprctl", "activewindow", "-j"], 2) or "{}").get("class") or ""
            p = os.path.join(WB, time.strftime("%Y-%m-%d") + ".json")
            d = json.load(open(p)) if os.path.exists(p) else {}
            if w:
                d[w] = d.get(w, 0) + 5
                json.dump(d, open(p, "w"))
        except Exception:
            pass
        time.sleep(5)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk

G = dict(wifi="\U000f0928", bt="\U000f00af", vol="\U000f057e", bri="\U000f00e0", bat="\U000f0079", lock="\U000f033e",
         night="\U000f0594", dnd="\U000f009b", prof="\U000f04c5", coffee="\U000f0176", plane="\U000f001d", rec="\U000f044a",
         speaker="\U000f04c3", aod="\U000f0150", scan="\U000f0450", off="\U000f0425", reboot="\U000f0709")
PAGES = [("wifi", "Wi-Fi", "wifi"), ("bluetooth", "Bluetooth & devices", "bt"), ("apps", "Apps", "scan"),
         ("notifications", "Notifications", "dnd"), ("sound", "Sound", "vol"), ("display", "Display & modes", "bri"),
         ("personalize", "Personalise", "night"), ("storage", "Storage", "rec"), ("battery", "Battery", "bat"),
         ("security", "Security & privacy", "lock"), ("location", "Location", "plane"),
         ("wellbeing", "Digital wellbeing", "coffee"), ("about", "About & updates", "prof")]

CSS = """
window.hs { background-color: alpha(@base, 0.92); }
.hs, .hs * { font-family: "JetBrainsMono Nerd Font", "Noto Sans", sans-serif; font-size: 13px; color: @text; }
.hs .side { background-color: alpha(@base, 0.55); border-right: 1px solid alpha(@text, 0.10); padding: 14px 10px; }
.hs .nav { background-image: none; background-color: transparent; border: 1px solid transparent; border-radius: 16px;
           padding: 9px 12px; box-shadow: none; }
.hs .nav:hover { background-color: alpha(@text, 0.09); }
.hs .nav.sel { background-image: linear-gradient(to right, alpha(@accent, 0.38), alpha(@accent2, 0.20)); border-color: alpha(@accent, 0.60); }
.hs .nico { color: @accent2; font-size: 16px; min-width: 26px; }
.hs .h1 { font-size: 22px; font-weight: 800; } .hs .sub, .hs .rsub { color: @subtext; font-size: 11px; }
.hs .card { background-color: alpha(@text, 0.07); border: 1px solid alpha(@text, 0.14); border-radius: 20px; padding: 6px 8px; }
.hs .row { padding: 9px 10px; border-radius: 14px; } .hs .rname { font-weight: 700; }
.hs button.chip { background-image: none; background-color: alpha(@text, 0.10); border: 1px solid alpha(@text, 0.12);
                  border-radius: 13px; padding: 6px 14px; font-weight: 700; box-shadow: none; }
.hs button.chip:hover { background-color: alpha(@text, 0.18); }
.hs button.chip.primary { background-color: alpha(@accent, 0.85); color: @base; } .hs button.chip.primary * { color: @base; }
.hs switch { background-color: alpha(@text, 0.20); background-image: none; border: none; border-radius: 14px; min-width: 46px; }
.hs switch:checked { background-color: @accent; } .hs switch slider { background-color: @text; background-image: none; border: none; border-radius: 11px; }
.hs switch:checked slider { background-color: @base; }
.hs scale trough, .hs levelbar trough { min-height: 8px; border-radius: 4px; background-color: alpha(@text, 0.18); border: none; background-image: none; }
.hs scale highlight, .hs levelbar block.filled { background-color: @accent; border-radius: 4px; border: none; background-image: none; }
.hs scale slider { min-width: 16px; min-height: 16px; margin: -5px; border-radius: 8px; border: none; background-color: @text; background-image: none; }
.hs entry { background-color: alpha(@text, 0.10); border: 1px solid alpha(@text, 0.14); border-radius: 12px; padding: 6px 10px; box-shadow: none; background-image: none; }
.hs .big { font-size: 40px; font-weight: 800; } .hs .wall { border-radius: 14px; border: 2px solid transparent; padding: 0; }
.hs .wall.cur { border-color: @accent; } .hs scrolledwindow, .hs viewport { background-color: transparent; }
"""
win = None


def bg(fn, then):
    def run():
        try:
            r = fn()
        except Exception:
            r = None
        GLib.idle_add(then, r)
    threading.Thread(target=run, daemon=True).start()


def L(t="", cls=None, x=0.0):
    l = Gtk.Label(label=t, xalign=x)
    l.set_line_wrap(True)
    if cls:
        l.get_style_context().add_class(cls)
    return l


def V(sp_=8, cls=None):
    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=sp_)
    if cls:
        b.get_style_context().add_class(cls)
    return b


def card(rows):
    c = V(2, "card")
    for r in rows:
        c.pack_start(r, False, False, 0)
    return c


def row(name, sub="", widget=None, icon=None):
    h = Gtk.Box(spacing=10)
    h.get_style_context().add_class("row")
    if icon:
        h.pack_start(L(G.get(icon, icon), "nico"), False, False, 0)
    t = V(1)
    t.pack_start(L(name, "rname"), False, False, 0)
    if sub:
        t.pack_start(L(sub, "rsub"), False, False, 0)
    h.pack_start(t, True, True, 0)
    if widget:
        h.pack_end(widget, False, False, 0)
    return h


def chip(text, fn, primary=False):
    b = Gtk.Button(label=text)
    b.get_style_context().add_class("chip")
    if primary:
        b.get_style_context().add_class("primary")
    b.connect("clicked", lambda *_: fn())
    return b


def sw(on, fn):
    s = Gtk.Switch(active=bool(on), valign=Gtk.Align.CENTER)
    s.connect("notify::active", lambda w, _: fn(w.get_active()))
    return s


def slider(val, fn, hi=100, w=220):
    s = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, hi, 1)
    s.set_value(val or 0); s.set_draw_value(False); s.set_size_request(w, -1)
    s.connect("value-changed", lambda x: threading.Thread(target=fn, args=(x.get_value(),), daemon=True).start())
    return s


def sh(c, t=3.0):
    return pc.sh(c, t)


def human(n):
    for u in "B KB MB GB TB".split():
        if n < 1024 or u == "TB":
            return ("%.0f %s" if u in "B KB" else "%.1f %s") % (n, u)
        n /= 1024


def folder_size(p):
    t = 0
    for r, _, fs in os.walk(p, onerror=lambda e: None):
        for f in fs:
            try:
                t += os.lstat(os.path.join(r, f)).st_size
            except OSError:
                pass
    return t


# ------------------------------------------------------------------ pages: each returns (widget, optional loader)
def page_wifi():
    box = V(10); w = pc.wifi()
    if w is None:
        return L("NetworkManager (nmcli) not found."), None
    box.pack_start(card([row("Wi-Fi", w[1] and "Connected to " + w[1] or "Not connected",
                             sw(w[0], lambda on: pc.set_wifi(on)), "wifi"),
                         row("IP address", pc.wifi_ip() or "-")]), False, False, 0)
    lst = V(2); box.pack_start(L("Nearby networks", "sub"), False, False, 0); box.pack_start(card([lst]), False, False, 0)

    def fill(nets):
        for c in lst.get_children():
            lst.remove(c)
        for n in nets or []:
            tag = "Connected" if n["active"] else ("Open" if not n["security"] else "Secured")
            lst.pack_start(row(n["ssid"], "%s%%  %s  %s" % (n["signal"], n.get("band", ""), tag),
                               None if n["active"] else chip("Connect", lambda s=n["ssid"]: bg(lambda: pc.wifi_connect(s), lambda r: 0))), False, False, 0)
        lst.show_all()
    return box, (pc.wifi_list, fill)


def page_bluetooth():
    box = V(10); p = pc.bluetooth()
    if p is None:
        return L("No Bluetooth adapter found."), None
    names = pc.bt_connected()
    box.pack_start(card([row("Bluetooth", "On" if p else "Off", sw(p, pc.set_bluetooth), "bt")]), False, False, 0)
    box.pack_start(L("Connected devices", "sub"), False, False, 0)
    rows = [row(n, "Connected", None, "speaker") for n in names] or [row("Nothing connected", "Pair new devices from the clock panel")]
    box.pack_start(card(rows), False, False, 0)
    usb = [l.split(" ", 6)[-1] for l in sh(["lsusb"]).splitlines() if "hub" not in l.lower()][:8]
    box.pack_start(L("USB devices", "sub"), False, False, 0)
    box.pack_start(card([row(u) for u in usb] or [row("None")]), False, False, 0)
    return box, None


def page_apps():
    box = V(10); apps = []
    for d in ("/usr/share/applications", os.path.expanduser("~/.local/share/applications")):
        for f in glob.glob(d + "/*.desktop"):
            try:
                t = open(f, errors="ignore").read()
                if "NoDisplay=true" in t:
                    continue
                n = [l[5:] for l in t.splitlines() if l.startswith("Name=")]
                if n:
                    apps.append((n[0], os.path.basename(f)))
            except OSError:
                pass
    apps.sort(key=lambda a: a[0].lower())
    e = Gtk.Entry(placeholder_text="Search %d apps" % len(apps)); box.pack_start(e, False, False, 0)
    lst = V(2); box.pack_start(card([lst]), False, False, 0)

    def fill(*_):
        q = e.get_text().lower()
        for c in lst.get_children():
            lst.remove(c)
        for n, f in [a for a in apps if q in a[0].lower()][:25]:
            lst.pack_start(row(n, f, chip("Open", lambda f=f: pc.spawn(["gtk-launch", f]))), False, False, 0)
        lst.show_all()
    e.connect("changed", fill); fill()
    return box, None


def page_notifications():
    d = pc.dnd()
    if d is None:
        return L("mako is not running."), None
    box = V(10)
    box.pack_start(card([row("Do not disturb", "Silences pop-ups, still collects them", sw(d, lambda on: pc.toggle_dnd() if on != pc.dnd() else 0), "dnd"),
                         row("Notification history", "", chip("Show", lambda: pc.spawn(["makoctl", "restore"]))),
                         row("Dismiss all", "", chip("Clear", lambda: pc.spawn(["makoctl", "dismiss", "--all"])))]), False, False, 0)
    box.pack_start(L("Edit look and timing in ~/.config/hypr-rice/mako/config", "sub"), False, False, 0)
    return box, None


def page_sound():
    box = V(10); v = pc.volume(); m = pc.mic_muted()
    box.pack_start(card([row("Output volume", "", slider(v and v[0], pc.set_volume, 150), "vol"),
                         row("Mute", "", sw(v and v[1], lambda on: pc.toggle_mute() if on != (pc.volume() or (0, on))[1] else 0)),
                         row("Microphone muted", "", sw(m, lambda on: pc.toggle_mic() if on != pc.mic_muted() else 0), "speaker")]), False, False, 0)
    for kind, title in (("sink", "Output devices"), ("source", "Input devices")):
        box.pack_start(L(title, "sub"), False, False, 0)
        rows = [row(d["name"], "Default" if d["default"] else "",
                    None if d["default"] else chip("Use", lambda d=d, k=kind: pc.set_default_audio(k, d["id"]))) for d in pc.audio_devices(kind)]
        box.pack_start(card(rows or [row("None found")]), False, False, 0)
    return box, None


def page_display():
    box = V(10); n = pc.nightlight(); prof = pc.profile()
    rows = [row("Brightness", "", slider(pc.brightness(), pc.set_brightness), "bri")]
    if n:
        rows += [row("Night light", "Warmth %sK" % n["temp"], sw(n["on"], lambda on: pc.toggle_nightlight() if on != pc.nightlight()["on"] else 0), "night"),
                 row("Warmth", "", slider(n["temp"], lambda k: pc.set_warmth(k), 6500))]
    box.pack_start(card(rows), False, False, 0)
    box.pack_start(L("Modes", "sub"), False, False, 0)
    modes = [row("Power profile", prof or "unavailable", chip("Cycle", lambda: (pc.cycle_profile(), None)), "prof")]
    if pc.caffeine_available():
        modes.append(row("Stay awake", "Blocks idle and sleep", sw(pc.caffeine_on(), pc.set_caffeine), "coffee"))
    modes += [row("Airplane mode", "", sw(pc.airplane(), pc.set_airplane), "plane"),
              row("Always-on display", "Dimmed clock screen", chip("Toggle", lambda: pc.spawn(["python3", os.path.join(RICE, "aod.py")])), "aod")]
    box.pack_start(card(modes), False, False, 0)
    return box, None


def page_personalize():
    box = V(10)
    try:
        c = json.load(open(os.path.join(GEN, "colors.json")))
    except Exception:
        c = {"accent": "cba6f7", "accent2": "89b4fa"}
    box.pack_start(card([row("Accent colours", "Taken from the current wallpaper, so they change when it does"),
                         row("Wallpaper", os.path.basename(c.get("wallpaper", "")), chip("Random", lambda: pc.spawn([os.path.join(RICE, "scripts", "wallpaper.sh"), "random"])))]), False, False, 0)
    fb = Gtk.FlowBox(max_children_per_line=4, selection_mode=Gtk.SelectionMode.NONE, row_spacing=8, column_spacing=8)
    from gi.repository import GdkPixbuf
    imgs = sorted(set(glob.glob(os.path.join(RICE, "wallpapers", "*.*")) + glob.glob(os.path.expanduser("~/Pictures/Wallpapers/*.*"))))

    def add(i, p):
        b = Gtk.Button(); b.get_style_context().add_class("wall")
        if p == c.get("wallpaper"):
            b.get_style_context().add_class("cur")
        b.add(Gtk.Image.new_from_pixbuf(i)); b.connect("clicked", lambda *_: pc.spawn([os.path.join(RICE, "scripts", "wallpaper.sh"), "set", p]))
        fb.add(b); b.show_all()

    def load():
        for p in imgs[:40]:
            try:
                GLib.idle_add(add, GdkPixbuf.Pixbuf.new_from_file_at_scale(p, 150, 90, False), p)
            except Exception:
                pass
    threading.Thread(target=load, daemon=True).start()
    box.pack_start(fb, False, False, 0)
    return box, None


def page_storage():
    box = V(10); u = shutil.disk_usage("/")
    lb = Gtk.LevelBar(min_value=0, max_value=1, value=u.used / u.total)
    box.pack_start(card([row("Internal storage", "%s used of %s  -  %s free" % (human(u.used), human(u.total), human(u.free))), lb]), False, False, 0)
    lst = V(2); box.pack_start(L("Your folders", "sub"), False, False, 0); box.pack_start(card([lst]), False, False, 0)
    dirs = ["Documents", "Downloads", "Pictures", "Videos", "Music", ".cache", ".config"]

    def fill(res):
        for c in lst.get_children():
            lst.remove(c)
        for n, s in sorted(res or [], key=lambda x: -x[1]):
            lst.pack_start(row(n, human(s)), False, False, 0)
        lst.show_all()
    return box, (lambda: [(d, folder_size(os.path.expanduser("~/" + d))) for d in dirs if os.path.isdir(os.path.expanduser("~/" + d))], fill)


def page_battery():
    b = pc.battery()
    if not b:
        return L("No battery found (desktop)."), None
    box = V(10); box.pack_start(L("%d%%" % b[0], "big"), False, False, 0)
    bar = Gtk.LevelBar(min_value=0, max_value=100, value=b[0]); rows = [row("Status", b[1] or "-"), bar]
    for d in glob.glob("/sys/class/power_supply/BAT*")[:1]:
        for a, z in (("energy_full", "energy_full_design"), ("charge_full", "charge_full_design")):
            f, n = pc._num(d + "/" + a), pc._num(d + "/" + z)
            if f and n:
                rows.append(row("Battery health", "%d%% of original capacity" % min(100, round(100 * f / n))))
                break
        cyc = pc._num(d + "/cycle_count")
        if cyc is not None:
            rows.append(row("Charge cycles", "%d" % cyc))
    rows.append(row("Power profile", pc.profile() or "-", chip("Cycle", pc.cycle_profile), "prof"))
    box.pack_start(card(rows), False, False, 0)
    return box, None


def page_security():
    box = V(10)
    fp = "fprintd" in sh(["pacman", "-Q", "fprintd"]) and "No devices" not in sh(["fprintd-list", os.environ.get("USER", "")], 4)
    idle = [l.split("=")[1].strip() for l in open(os.path.join(RICE, "hypridle.conf")).read().splitlines() if "timeout" in l and "=" in l] if os.path.exists(os.path.join(RICE, "hypridle.conf")) else []
    fw = sh(["systemctl", "is-active", "ufw"]).strip() or sh(["systemctl", "is-active", "nftables"]).strip() or "not found"
    box.pack_start(card([row("Lock screen now", "", chip("Lock", lambda: pc.spawn(["loginctl", "lock-session"])), "lock"),
                         row("Auto-lock", "After %s s idle (edit hypridle.conf)" % (idle[1] if len(idle) > 1 else "?")),
                         row("Fingerprint unlock", "Sensor ready" if fp else "No fingerprint sensor detected"),
                         row("Firewall", fw)]), False, False, 0)
    box.pack_start(L("Privacy", "sub"), False, False, 0)
    box.pack_start(card([row("Microphone", "", sw(not pc.mic_muted(), lambda on: pc.toggle_mic() if on == bool(pc.mic_muted()) else 0)),
                         row("Screen recording", "Super + Alt + R", None, "rec")]), False, False, 0)
    return box, None


def page_location():
    on = sh(["systemctl", "is-active", "geoclue"]).strip() == "active"
    box = V(10)
    box.pack_start(card([row("Location services", "GeoClue " + ("running" if on else "stopped"),
                             sw(on, lambda v: pc.spawn(["pkexec", "systemctl", "start" if v else "stop", "geoclue"])), "plane"),
                         row("Time zone", sh(["timedatectl", "show", "-p", "Timezone", "--value"]).strip() or "-")]), False, False, 0)
    box.pack_start(L("Apps only get your location while this is on. Needs the geoclue package.", "sub"), False, False, 0)
    return box, None


def page_wellbeing():
    box = V(10); p = os.path.join(WB, time.strftime("%Y-%m-%d") + ".json")
    try:
        d = json.load(open(p))
    except Exception:
        d = {}
    tot = sum(d.values())
    up = float(open("/proc/uptime").read().split()[0])
    box.pack_start(L("%dh %02dm" % (tot // 3600, tot % 3600 // 60), "big"), False, False, 0)
    box.pack_start(L("screen time today, %dh %02dm since boot" % (up // 3600, up % 3600 // 60), "sub"), False, False, 0)
    rows = []
    for n, s in sorted(d.items(), key=lambda x: -x[1])[:8]:
        bar = Gtk.LevelBar(min_value=0, max_value=max(d.values()), value=s); bar.set_size_request(160, -1)
        rows.append(row(n, "%dm" % (s // 60), bar))
    box.pack_start(card(rows or [row("No data yet", "Start the tracker: exec-once = python3 ~/.config/hypr-rice/scripts/settings.py --track")]), False, False, 0)
    box.pack_start(card([row("Night light", "Wind down in the evening", chip("Open", lambda: win.go("display"))),
                         row("Do not disturb", "", chip("Open", lambda: win.go("notifications")))]), False, False, 0)
    return box, None


def page_about():
    box = V(10)
    ver = sh(["git", "-C", RICE, "log", "-1", "--format=%h  %s  (%cr)"]).strip() or "not a git checkout"
    n = sh(["git", "-C", RICE, "rev-list", "--count", "HEAD"]).strip()
    box.pack_start(card([row("C Launcher", "Version " + (n and "build %s" % n or "custom"), None, "prof"),
                         row("Latest change", ver),
                         row("Updates", "Delivered by you: pull or copy new files into the rice folder, then restart the panel"),
                         row("Open rice folder", RICE, chip("Open", lambda: pc.spawn(["xdg-open", RICE]))),
                         row("Restart panel", "Use when the clock panel is missing", chip("Restart", lambda: pc.spawn([os.path.join(RICE, "scripts", "panel-toggle.sh"), "--restart"]))),
                         row("Restart waybar", "Use when the pill bar is missing", chip("Restart", lambda: pc.spawn([os.path.join(RICE, "scripts", "restart-rice-waybar.sh")])))]), False, False, 0)
    box.pack_start(L("Kernel " + sh(["uname", "-r"]).strip() + "  -  " + (sh(["hyprctl", "version", "-j"]) and json.loads(sh(["hyprctl", "version", "-j"])).get("tag", "Hyprland") or "Hyprland"), "sub"), False, False, 0)
    return box, None


KW = dict(wifi="network internet ip router hotspot", bluetooth="usb devices headphones pair earbuds", apps="programs launch applications",
          notifications="dnd do not disturb silence mako", sound="volume mute microphone speaker output input audio",
          display="brightness night light warmth power profile airplane stay awake always-on modes", personalize="wallpaper accent colours theme",
          storage="disk space folders downloads", battery="charge health cycles power", security="lock fingerprint firewall privacy password",
          location="geoclue gps time zone", wellbeing="screen time usage focus", about="updates version restart panel waybar git")


class Win(Gtk.Window):
    def __init__(self, first):
        super().__init__(title="Settings"); global win; win = self
        self.set_default_size(980, 660); self.get_style_context().add_class("hs")
        self.set_visual(self.get_screen().get_rgba_visual()); self.set_app_paintable(True)
        self.prov = Gtk.CssProvider(); Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.prov, 800)
        self.sig = None; self.restyle()
        GLib.timeout_add_seconds(2, self.restyle)   # follow the wallpaper
        root = Gtk.Box(); self.add(root)
        side = V(2, "side"); side.set_size_request(250, -1); root.pack_start(side, False, False, 0)
        side.pack_start(L("Settings", "h1"), False, False, 8)
        self.q = Gtk.SearchEntry(placeholder_text="Search settings"); side.pack_start(self.q, False, False, 6)
        self.q.connect("search-changed", self.filter); self.q.connect("activate", self.first)
        self.navs = {}; self.stack = Gtk.Stack(); self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        for key, name, ic in PAGES:
            b = Gtk.Button(); b.get_style_context().add_class("nav")
            h = Gtk.Box(spacing=8); h.pack_start(L(G[ic], "nico"), False, False, 0); h.pack_start(L(name), False, False, 0); b.add(h)
            b.connect("clicked", lambda _, k=key: self.go(k)); side.pack_start(b, False, False, 0); self.navs[key] = b
        sc = Gtk.ScrolledWindow(); sc.add(self.stack); root.pack_start(sc, True, True, 0)
        self.go(first); self.show_all()

    def hits(self):
        q = self.q.get_text().strip().lower()
        return [k for k, n, _ in PAGES if not q or q in (n + " " + KW.get(k, "")).lower()]

    def filter(self, *_):
        h = self.hits()
        for k, b in self.navs.items():
            b.set_visible(k in h)

    def first(self, *_):
        h = self.hits()
        if h:
            self.go(h[0])

    def restyle(self):
        css = pc.css_colors()
        if css != self.sig:
            self.sig = css; self.prov.load_from_data((css + CSS).encode())
        return True

    def go(self, key):
        for k, b in self.navs.items():
            ctx = b.get_style_context(); ctx.add_class("sel") if k == key else ctx.remove_class("sel")
        old = self.stack.get_child_by_name(key)
        if old:
            self.stack.remove(old)
        title = dict((k, n) for k, n, _ in PAGES)[key]
        body = V(12); body.set_border_width(26); body.pack_start(L(title, "h1"), False, False, 0)
        w, loader = globals()["page_" + key]()
        body.pack_start(w, False, False, 0); body.show_all()
        self.stack.add_named(body, key); self.stack.set_visible_child_name(key)
        if loader:
            bg(loader[0], loader[1])


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("-")]
    Win(a[0] if a and a[0] in dict((k, 1) for k, _, _ in PAGES) else "wifi").connect("destroy", Gtk.main_quit)
    Gtk.main()
