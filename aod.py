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
