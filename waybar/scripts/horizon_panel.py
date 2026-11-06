#!/usr/bin/env python3
"""Horizon system panel: click the monitor icon in the bar to drop a live system panel.
Click the icon again (or press Esc) to close it.  Needs python-gobject (GTK3) and python-cairo;
gtk-layer-shell is optional but makes it appear right under the bar."""
import os, re, signal, sys, time
from pathlib import Path

PID = "/tmp/horizon_panel.pid"
ALIGN = "center"      # "center" (under the clock) or "right" (top-right corner)
TOP_MARGIN = 46       # gap from the top edge, in pixels
ROWS = 8              # how many processes to list
CLK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")


def rd(p, d=""):
    try:
        with open(p) as f:
            return f.read()
    except Exception:
        return d


def cpu_times():
    out = []
    for line in rd("/proc/stat").splitlines():
        if line.startswith("cpu"):
            v = [int(x) for x in line.split()[1:]]
            out.append((sum(v[:8]), v[3] + (v[4] if len(v) > 4 else 0)))
    return out


def meminfo():
    d = {}
    for line in rd("/proc/meminfo").splitlines():
        k, _, rest = line.partition(":")
        try:
            d[k] = int(rest.split()[0])
        except Exception:
            pass
    return d


def cpu_temp():
    best = None
    try:
        for h in Path("/sys/class/hwmon").glob("hwmon*"):
            if rd(h / "name").strip() in ("coretemp", "k10temp", "zenpower", "cpu_thermal"):
                vals = [int(rd(t).strip() or 0) for t in h.glob("temp*_input")]
                if vals:
                    best = max(vals) / 1000.0
                    break
        if best is None:
            best = int(rd("/sys/class/thermal/thermal_zone0/temp").strip()) / 1000.0
    except Exception:
        pass
    return best


def battery():
    try:
        bats = sorted(Path("/sys/class/power_supply").glob("BAT*"))
    except Exception:
        bats = []
    if not bats:
        return None
    b = bats[0]
    g = lambda n: rd(b / n).strip()
    try:
        cap = int(g("capacity"))
    except Exception:
        return None
    status = g("status") or "Unknown"
    num = lambda s: int(s) if s.lstrip("-").isdigit() else 0
    power = num(g("power_now"))
    if not power:
        power = num(g("current_now")) * num(g("voltage_now")) // 1000000
    e_now, e_full = num(g("energy_now")), num(g("energy_full"))
    if not e_full:
        v = num(g("voltage_now"))
        e_now, e_full = num(g("charge_now")) * v // 1000000, num(g("charge_full")) * v // 1000000
    hours = None
    if power > 0 and e_full:
        if status == "Discharging":
            hours = e_now / float(power)
        elif status == "Charging":
            hours = max(0, e_full - e_now) / float(power)
    health = round(100.0 * e_full / num(g("energy_full_design")), 0) if num(g("energy_full_design")) and e_full else None
    return {"cap": cap, "status": status, "watts": power / 1e6, "hours": hours, "health": health}


class Procs:
    def __init__(self):
        self.prev, self.t = {}, time.time()

    def sample(self):
        now = time.time()
        dt = max(now - self.t, 0.001)
        self.t = now
        cur, rows = {}, []
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                s = open("/proc/%s/stat" % d).read()
                r = s.rfind(")")
                name = s[s.find("(") + 1:r]
                f = s[r + 2:].split()
                ticks = int(f[11]) + int(f[12])
                rss = int(f[21]) * PAGE
            except Exception:
                continue
            cur[d] = ticks
            cpu = (ticks - self.prev[d]) / float(CLK) / dt * 100.0 if d in self.prev else 0.0
            rows.append((name, int(d), cpu, rss))
        self.prev = cur
        return rows


def gib(kb):
    return kb / 1048576.0


def human_time(h):
    if h is None:
        return ""
    m = int(h * 60)
    return "%dh %02dm" % (m // 60, m % 60)


def uptime():
    try:
        s = int(float(rd("/proc/uptime").split()[0]))
    except Exception:
        return ""
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    return ("%dd " % d if d else "") + "%dh %02dm" % (h, s // 60)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def mix_white(h, t=0.35):
    r, g, b = hexrgb(h)
    return "#%02x%02x%02x" % tuple(int((c + (1 - c) * t) * 255) for c in (r, g, b))


def accents():
    a1, a2 = "#c4a7f5", "#7fb0ff"
    t = rd(Path.home() / ".cache/wal/colors-waybar.css")
    m4 = re.search(r"@define-color\s+color4\s+(#[0-9a-fA-F]{6})", t)
    m5 = re.search(r"@define-color\s+color5\s+(#[0-9a-fA-F]{6})", t)
    if m4 and m5:
        a1, a2 = mix_white(m4.group(1)), mix_white(m5.group(1))
    return a1, a2


CSS = """
window.hzwin { background-color: transparent; }
.panel { background-color: rgba(18,15,28,0.90); border: 1px solid rgba(255,255,255,0.14);
  border-radius: 20px; padding: 16px 18px; color: #e6e2f5; font-size: 12px; }
.title { font-weight: 700; font-size: 14px; }
.dim { color: rgba(230,226,245,0.55); }
.big { font-size: 22px; font-weight: 700; color: @A1@; }
.big2 { font-size: 22px; font-weight: 700; color: @A2@; }
.h { font-size: 10px; letter-spacing: 2px; color: rgba(230,226,245,0.55); }
.sec { background-color: rgba(255,255,255,0.06); border-radius: 14px; padding: 10px 12px; }
progressbar trough { min-height: 6px; border-radius: 3px; background-color: rgba(255,255,255,0.12); }
progressbar progress { min-height: 6px; border-radius: 3px; background-image: linear-gradient(to right, @A1@, @A2@); }
button.sort { padding: 1px 10px; border-radius: 10px; background-image: none; background-color: rgba(255,255,255,0.08);
  color: rgba(230,226,245,0.7); border: none; box-shadow: none; font-size: 11px; min-height: 0; }
button.sort.on { background-color: @A1@; color: #16121f; }
.warn { color: #f5c37a; } .crit { color: #ff7b97; } .good { color: #8fe3a0; }
"""


def main():
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gtk, Gdk, GLib
    import cairo
    LS = None
    try:
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import GtkLayerShell as LS
    except Exception:
        LS = None

    a1, a2 = accents()
    c1, c2 = hexrgb(a1), hexrgb(a2)
    prov = Gtk.CssProvider()
    prov.load_from_data(CSS.replace("@A1@", a1).replace("@A2@", a2).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    state = {"sort": "cpu", "hist": [0.0] * 60, "cores": [], "prev": cpu_times(), "rows": [], "tick": 0}
    procs = Procs()
    procs.sample()

    win = Gtk.Window(title="horizon-panel")
    win.get_style_context().add_class("hzwin")
    win.set_decorated(False)
    win.set_resizable(False)
    win.set_app_paintable(True)
    vis = win.get_screen().get_rgba_visual()
    if vis:
        win.set_visual(vis)
    if LS:
        LS.init_for_window(win)
        LS.set_layer(win, LS.Layer.OVERLAY)
        LS.set_namespace(win, "horizon-panel")
        LS.set_anchor(win, LS.Edge.TOP, True)
        LS.set_margin(win, LS.Edge.TOP, TOP_MARGIN)
        if ALIGN == "right":
            LS.set_anchor(win, LS.Edge.RIGHT, True)
            LS.set_margin(win, LS.Edge.RIGHT, 14)
        try:
            LS.set_keyboard_mode(win, LS.KeyboardMode.ON_DEMAND)
        except Exception:
            pass
    else:
        win.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        win.set_keep_above(True)

    def lab(text="", cls=None, right=False):
        l = Gtk.Label(label=text)
        l.set_xalign(1.0 if right else 0.0)
        if cls:
            l.get_style_context().add_class(cls)
        return l

    def sec():
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        b.get_style_context().add_class("sec")
        return b

    def row(a, b):
        r = Gtk.Box(spacing=8)
        r.pack_start(a, True, True, 0)
        r.pack_end(b, False, False, 0)
        return r

    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    root.get_style_context().add_class("panel")
    root.set_size_request(400, -1)

    title_up = lab("", "dim", True)
    root.pack_start(row(lab("System", "title"), title_up), False, False, 0)

    # CPU
    cpu_box = sec()
    cpu_pct = lab("0%", "big")
    cpu_sub = lab("", "dim", True)
    cpu_box.pack_start(row(row(lab("CPU", "h"), cpu_pct), cpu_sub), False, False, 0)
    spark = Gtk.DrawingArea()
    spark.set_size_request(-1, 44)
    cores = Gtk.DrawingArea()
    cores.set_size_request(-1, 22)

    def draw_spark(w, cr):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        h = state["hist"]
        n = len(h)
        pts = [(i * (W - 1) / float(n - 1), H - 2 - min(v, 100) / 100.0 * (H - 4)) for i, v in enumerate(h)]
        cr.move_to(0, H)
        for x, y in pts:
            cr.line_to(x, y)
        cr.line_to(W, H)
        cr.close_path()
        g = cairo.LinearGradient(0, 0, 0, H)
        g.add_color_stop_rgba(0, c1[0], c1[1], c1[2], 0.45)
        g.add_color_stop_rgba(1, c1[0], c1[1], c1[2], 0.02)
        cr.set_source(g)
        cr.fill()
        cr.set_source_rgba(c1[0], c1[1], c1[2], 1)
        cr.set_line_width(1.6)
        cr.move_to(*pts[0])
        for x, y in pts[1:]:
            cr.line_to(x, y)
        cr.stroke()
        return False

    def draw_cores(w, cr):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        cs = state["cores"]
        if not cs:
            return False
        gap = 3
        bw = max(2.0, (W - gap * (len(cs) - 1)) / float(len(cs)))
        for i, v in enumerate(cs):
            x = i * (bw + gap)
            cr.set_source_rgba(1, 1, 1, 0.1)
            cr.rectangle(x, 0, bw, H)
            cr.fill()
            hh = max(1.0, v / 100.0 * H)
            cr.set_source_rgba(c2[0], c2[1], c2[2], 0.95)
            cr.rectangle(x, H - hh, bw, hh)
            cr.fill()
        return False

    spark.connect("draw", lambda w, cr: draw_spark(w, cr))
    cores.connect("draw", lambda w, cr: draw_cores(w, cr))
    cpu_box.pack_start(spark, False, False, 0)
    cpu_box.pack_start(cores, False, False, 0)
    cpu_box.pack_start(lab("PER CORE", "h"), False, False, 0)
    root.pack_start(cpu_box, False, False, 0)

    # memory + swap
    mem_box = sec()
    mem_t = lab("", "dim", True)
    mem_p = lab("0%", "big2")
    mem_box.pack_start(row(row(lab("MEMORY", "h"), mem_p), mem_t), False, False, 0)
    mem_bar = Gtk.ProgressBar()
    mem_box.pack_start(mem_bar, False, False, 0)
    mem_x = lab("", "dim")
    mem_box.pack_start(mem_x, False, False, 0)
    swap_t = lab("", "dim", True)
    mem_box.pack_start(row(lab("SWAP", "h"), swap_t), False, False, 0)
    swap_bar = Gtk.ProgressBar()
    mem_box.pack_start(swap_bar, False, False, 0)
    root.pack_start(mem_box, False, False, 0)

    # battery
    bat_box = sec()
    bat_p = lab("", "big")
    bat_t = lab("", "dim", True)
    bat_box.pack_start(row(row(lab("BATTERY", "h"), bat_p), bat_t), False, False, 0)
    bat_bar = Gtk.ProgressBar()
    bat_box.pack_start(bat_bar, False, False, 0)
    bat_x = lab("", "dim")
    bat_box.pack_start(bat_x, False, False, 0)
    root.pack_start(bat_box, False, False, 0)

    # processes
    pr_box = sec()
    btns = Gtk.Box(spacing=6)
    b_cpu, b_mem = Gtk.Button(label="CPU"), Gtk.Button(label="MEM")
    for b in (b_cpu, b_mem):
        b.get_style_context().add_class("sort")
        btns.pack_start(b, False, False, 0)
    pr_box.pack_start(row(lab("PROCESSES", "h"), btns), False, False, 0)
    grid = Gtk.Grid(column_spacing=12, row_spacing=3)
    for i, t in enumerate(("NAME", "PID", "CPU", "MEM")):
        grid.attach(lab(t, "h", i > 0), i, 0, 1, 1)
    cells = []
    for r in range(ROWS):
        rowc = []
        for c in range(4):
            l = lab("", None, c > 0)
            if c == 0:
                l.set_hexpand(True)
                l.set_ellipsize(3)
                l.set_max_width_chars(22)
            grid.attach(l, c, r + 1, 1, 1)
            rowc.append(l)
        cells.append(rowc)
    pr_box.pack_start(grid, False, False, 0)
    root.pack_start(pr_box, False, False, 0)
    win.add(root)

    def set_sort(k):
        state["sort"] = k
        for b, kk in ((b_cpu, "cpu"), (b_mem, "mem")):
            sc = b.get_style_context()
            sc.add_class("on") if kk == k else sc.remove_class("on")
        fill_procs()

    b_cpu.connect("clicked", lambda *_: set_sort("cpu"))
    b_mem.connect("clicked", lambda *_: set_sort("mem"))

    def level(widget, v):
        sc = widget.get_style_context()
        for c in ("warn", "crit"):
            sc.remove_class(c)
        if v >= 85:
            sc.add_class("crit")
        elif v >= 65:
            sc.add_class("warn")

    def fill_procs():
        key = (lambda r: r[2]) if state["sort"] == "cpu" else (lambda r: r[3])
        top = sorted(state["rows"], key=key, reverse=True)[:ROWS]
        for rowc, r in zip(cells, top + [None] * (ROWS - len(top))):
            if r is None:
                for l in rowc:
                    l.set_text("")
                continue
            rowc[0].set_text(r[0])
            rowc[1].set_text(str(r[1]))
            rowc[2].set_text("%.1f%%" % r[2])
            rowc[3].set_text("%d MiB" % (r[3] // 1048576) if r[3] < 1 << 30 else "%.1f GiB" % (r[3] / 1073741824.0))

    def update():
        cur = cpu_times()
        pv = state["prev"]
        vals = []
        for (t1, i1), (t0, i0) in zip(cur, pv):
            dt = t1 - t0
            vals.append(100.0 * (dt - (i1 - i0)) / dt if dt > 0 else 0.0)
        state["prev"] = cur
        if vals:
            total, per = vals[0], vals[1:]
            state["hist"] = state["hist"][1:] + [total]
            state["cores"] = per
            cpu_pct.set_text("%d%%" % round(total))
            level(cpu_pct, total)
            la = rd("/proc/loadavg").split()[:3]
            tmp = cpu_temp()
            cpu_sub.set_text("load %s  \u00b7  %d cores%s" % (" ".join(la), len(per),
                                                         ("  \u00b7  %d\u00b0C" % round(tmp)) if tmp else ""))
        m = meminfo()
        tot = m.get("MemTotal", 1)
        used = tot - m.get("MemAvailable", 0)
        pct = 100.0 * used / tot
        mem_p.set_text("%d%%" % round(pct))
        mem_t.set_text("%.2f / %.2f GiB" % (gib(used), gib(tot)))
        mem_bar.set_fraction(min(1.0, pct / 100.0))
        mem_x.set_text("cached %.2f  \u00b7  buffers %.2f  \u00b7  free %.2f GiB" % (
            gib(m.get("Cached", 0)), gib(m.get("Buffers", 0)), gib(m.get("MemFree", 0))))
        st = m.get("SwapTotal", 0)
        if st:
            su = st - m.get("SwapFree", 0)
            swap_t.set_text("%.2f / %.2f GiB  (%d%%)" % (gib(su), gib(st), round(100.0 * su / st)))
            swap_bar.set_fraction(su / float(st))
        else:
            swap_t.set_text("off")
            swap_bar.set_fraction(0)
        bt = battery()
        if bt:
            bat_box.show()
            bat_p.set_text("%d%%" % bt["cap"])
            bat_bar.set_fraction(bt["cap"] / 100.0)
            bat_t.set_text(bt["status"] + ((" \u00b7 " + human_time(bt["hours"]) + (" left" if bt["status"] == "Discharging" else " to full")) if bt["hours"] else ""))
            bat_x.set_text(("drawing %.1f W" % bt["watts"] if bt["watts"] else "no power draw reported")
                           + (("  \u00b7  health %d%%" % bt["health"]) if bt["health"] else ""))
        else:
            bat_box.hide()
        title_up.set_text("up " + uptime())
        state["tick"] += 1
        if state["tick"] % 2 == 1:
            state["rows"] = procs.sample()
            fill_procs()
        spark.queue_draw()
        cores.queue_draw()
        return True

    def quit_now(*_):
        Gtk.main_quit()
        return False

    def on_key(w, e):
        if e.keyval == Gdk.KEY_Escape:
            quit_now()
        return False

    focus = {"was": False}
    win.connect("key-press-event", on_key)
    win.connect("focus-in-event", lambda *a: focus.update(was=True) or False)
    win.connect("focus-out-event", lambda *a: GLib.timeout_add(120, quit_now) if focus["was"] else False)
    win.connect("destroy", quit_now)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_now)
    set_sort("cpu")
    time.sleep(0.25)
    update()
    GLib.timeout_add(1000, update)
    win.show_all()
    if not battery():
        bat_box.hide()
    Gtk.main()


def toggle_existing():
    try:
        pid = int(rd(PID).strip())
        os.kill(pid, 0)
        if "horizon_panel" in rd("/proc/%d/cmdline" % pid):
            os.kill(pid, signal.SIGTERM)
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    if toggle_existing():
        sys.exit(0)
    open(PID, "w").write(str(os.getpid()))
    try:
        main()
    finally:
        try:
            if rd(PID).strip() == str(os.getpid()):
                os.remove(PID)
        except Exception:
            pass
