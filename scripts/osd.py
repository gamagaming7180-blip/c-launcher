#!/usr/bin/env python3
"""osd: a small glass pop-up for volume and brightness, in the style of the settings panel.

When your volume or brightness changes (keyboard keys, the panel sliders, anything), a droplet leaves the clock
pill, drops under the bar and opens into a pop-up with an icon, a level bar and the percentage. The bar is drawn
in your current wallpaper's accent colours and follows the wallpaper when it changes. It closes by itself.

It watches the real values, so your existing volume / brightness key bindings keep working: nothing to rebind.
  osd.py --hidden   start the background watcher (the Waybar media ticker also starts it automatically)
  osd.py            same as --hidden
Needs python-gobject, gtk3, gtk-layer-shell and wpctl (PipeWire). Brightness uses /sys/class/backlight or brightnessctl.
"""
import ctypes
import fcntl
import glob
import json
import math
import os
import re
import shutil
import signal
import subprocess as sp
import sys
import threading
import time

try:   # gtk-layer-shell must load before libwayland-client
    ctypes.CDLL("libgtk-layer-shell.so.0", mode=ctypes.RTLD_GLOBAL)
except OSError:
    pass
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import panelcore as pc            # the settings panel's colour scheme (follows the wallpaper)
except Exception:
    pc = None

try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GLib, Gtk, Gdk  # noqa: E402
    from gi.repository import GtkLayerShell  # noqa: E402
except (ImportError, ValueError):
    print("osd needs: sudo pacman -S python-gobject gtk3 gtk-layer-shell", file=sys.stderr)
    sys.exit(1)

LOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr-rice-osd.lock")
RICE = os.path.expanduser("~/.config/hypr-rice")
COLORS_CSS = os.path.join(RICE, "waybar", "colors.css")

# ---- tweak here --------------------------------------------------------------------------------------------
OSD_W = 340               # pop-up width
CARD_TOP = 48             # px from the top of the screen to the pop-up (just under your 40px bar)
PILL_W, PILL_H, PILL_Y = 164, 31, 9     # the clock pill in the bar: the droplet starts on it
HOLD_SECS = 2.3           # how long it stays after the last change
GLASS = 0.88              # how solid the glass is: 0 = clear, 1 = opaque (raise to ~0.30 on bright wallpapers)
RADIUS = 28               # corner radius
GLYPH = dict(vol_off="\U000f0581", vol_mute="\U000f075f", vol_low="\U000f057f", vol_mid="\U000f0580",
             vol_high="\U000f057e", bri="\U000f00e0")

FALLBACK = ("@define-color base #1e1e2e; @define-color text #cdd6f4; @define-color subtext #a6adc8; "
            "@define-color red #f38ba8; @define-color accent #cba6f7; @define-color accent2 #89b4fa;")
CSS = """
.osd, .osd * { font-family: "JetBrainsMono Nerd Font", "Noto Sans", sans-serif; }
window.osd { background-color: transparent; }
.osd label { text-shadow: 0 1px 3px rgba(0,0,0,0.35); }
.osd .cardflat { background-color: transparent; border: 1px solid transparent; border-radius: %RADIUS%px;
                 padding: 12px 20px 12px 12px; }
.osd .card { background-color: alpha(@base, %GLASS%);
             background-image: linear-gradient(to bottom right, alpha(@accent, 0.22), alpha(@accent2, 0.06), alpha(@accent, 0.14));
             border: 1px solid alpha(@text, 0.12); 
             border-radius: %RADIUS%px; padding: 12px 20px 12px 12px;
             box-shadow: inset 0 0 0 0 transparent; }
.osd .ico { font-size: 19px; color: @text; min-width: 40px; min-height: 40px; border-radius: 20px;
            background-image: linear-gradient(135deg, alpha(@accent, 0.62), alpha(@accent2, 0.38));
            box-shadow: inset 0 0 0 0 transparent, 0 0 14px alpha(@accent, 0.35); }
.osd .pct { font-size: 13px; font-weight: 800; color: @text; min-width: 46px; }
""".replace("%GLASS%", str(GLASS)).replace("%RADIUS%", str(RADIUS))


# ------------------------------------------------------------------ reading volume and brightness
def run(args, timeout=1.0):
    try:
        p = sp.run(args, text=True, stdout=sp.PIPE, stderr=sp.DEVNULL, timeout=timeout, check=False)
    except (OSError, sp.TimeoutExpired):
        return ""
    return p.stdout.strip() if p.returncode == 0 else ""


def read_volume():
    """-> (percent, muted) or None"""
    m = re.search(r"Volume:\s*([\d.]+)(\s*\[MUTED\])?", run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]))
    return (round(float(m.group(1)) * 100), bool(m.group(2))) if m else None


def backlight_dirs():
    return [d for d in glob.glob("/sys/class/backlight/*") if os.path.exists(d + "/brightness")]


def read_brightness():
    """-> percent or None"""
    for d in backlight_dirs():
        try:
            cur = float(open(d + "/brightness").read())
            mx = float(open(d + "/max_brightness").read())
            if mx > 0:
                return round(cur / mx * 100)
        except (OSError, ValueError):
            continue
    if shutil.which("brightnessctl"):
        parts = run(["brightnessctl", "-m"]).split(",")
        try:
            return int(parts[3].rstrip("%"))
        except (IndexError, ValueError):
            pass
    return None


class Watcher:
    """Threads that notice volume / brightness changes and report them through `emit(kind, value, muted)`."""

    def __init__(self, emit):
        self.emit = emit

    def start(self):
        threading.Thread(target=self.volume_loop, daemon=True).start()
        threading.Thread(target=self.brightness_loop, daemon=True).start()

    def volume_loop(self):
        last = read_volume()
        wake = threading.Event()
        if shutil.which("pactl"):                                  # event driven, no polling
            def sub():
                while True:
                    try:
                        p = sp.Popen(["pactl", "subscribe"], stdout=sp.PIPE, stderr=sp.DEVNULL, text=True)
                        for line in p.stdout:
                            if " sink " in line or " server" in line:
                                wake.set()
                        p.wait()
                    except OSError:
                        pass
                    time.sleep(2)
            threading.Thread(target=sub, daemon=True).start()
            interval = 5.0                                          # safety net only
        else:
            interval = 0.3
        while True:
            wake.wait(interval)
            wake.clear()
            time.sleep(0.03)                                        # coalesce bursts of events
            wake.clear()
            cur = read_volume()
            if cur is not None and cur != last:
                if last is not None:                                # the first reading is only a baseline
                    self.emit("volume", cur[0], cur[1])
                last = cur

    def brightness_loop(self):
        last = read_brightness()
        poll = 0.12 if backlight_dirs() else 0.6                    # reading a sysfs file is practically free
        while True:
            time.sleep(poll)
            cur = read_brightness()
            if cur is not None and cur != last:
                if last is not None:
                    self.emit("brightness", cur, False)
                last = cur


# ------------------------------------------------------------------ drawing helpers
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


def make_provider(text):
    p = Gtk.CssProvider()
    try:
        p.load_from_data(text.encode())
        return p
    except GLib.Error:
        pass
    good = []
    for part in [r + "}" for r in text.split("}") if r.strip()]:
        t = Gtk.CssProvider()
        try:
            t.load_from_data(part.encode())
            good.append(part)
        except GLib.Error as exc:
            print("osd: skipped a CSS rule:", exc.message, file=sys.stderr)
    p = Gtk.CssProvider()
    p.load_from_data("\n".join(good).encode())
    return p


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
    """Fills the window. While animating, a droplet starts on the clock pill, drops and opens into the pop-up."""
    __gtype_name__ = "RiceOsdStage"

    def __init__(self, card, pill_cx):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.card, self.pill_cx = card, pill_cx
        self.t, self.animating, self._tick = 0.0, True, None

    def _rgb(self, name, fallback):
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
            cx, cy = self.card.translate_coordinates(self, 0, 0) or (40, CARD_TOP)
            cw, ch = self.card.get_allocated_width(), self.card.get_allocated_height()
            base = self._rgb("base", (0.12, 0.12, 0.18))
            a1 = self._rgb("accent", (0.8, 0.65, 0.97))
            a2 = self._rgb("accent2", (0.54, 0.7, 0.98))
            res = draw_droplet(cr, self.t, self.pill_cx, PILL_W, PILL_H, PILL_Y, (cx, cy, cw, ch), base, a1, a2, GLASS,
                               RADIUS, 14.0)
            if res is not None and res[5] > 0.0:                   # the pop-up is open enough: fade its contents in
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
            return Gtk.Box.do_draw(self, cr)
        return False

    def _settle(self):
        self.animating = False
        ctx = self.card.get_style_context()
        ctx.remove_class("cardflat")
        ctx.add_class("card")
        self.queue_draw()

    def run(self, mode, done=None):
        if self._tick is not None:
            self.remove_tick_callback(self._tick)
        ctx = self.card.get_style_context()
        ctx.remove_class("card")
        ctx.add_class("cardflat")
        self.animating = True
        if mode == "out":
            self.t = 1.0
        t0 = [None]
        dur = 0.26 if mode == "in" else 0.18

        def step(_w, clock):
            now = clock.get_frame_time() / 1e6
            if t0[0] is None:
                t0[0] = now
            f = _clamp((now - t0[0]) / dur)
            self.t = f if mode == "in" else 1.0 - f
            self.queue_draw()
            if f >= 1.0:
                self._tick = None
                if mode == "in":
                    self.t = 1.0
                    self._settle()
                if done:
                    done()
                return False
            return True
        self._tick = self.add_tick_callback(step)
        if mode == "in":
            GLib.timeout_add(1400, lambda: (self._rescue(), False)[1])

    def _rescue(self):
        if self.animating and self._tick is not None:
            self.remove_tick_callback(self._tick)
            self._tick = None
            self.t = 1.0
            self._settle()


# ------------------------------------------------------------------ the pop-up window
class OsdWindow(Gtk.Window):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.alive, self.leaving = True, False
        self.value = self.shown = 0.0
        self.muted, self.kind = False, "volume"
        self.deadline = time.monotonic() + HOLD_SECS
        self.anim_tick = None
        self.get_style_context().add_class("osd")
        self.set_title("rice-osd")
        self.set_app_paintable(True)
        self.set_accept_focus(False)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "rice-osd")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)        # centred under the clock
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        self.set_size_request(OSD_W + 80, -1)

        self.card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.card.get_style_context().add_class("cardflat")
        self.card.set_halign(Gtk.Align.CENTER)
        self.card.set_size_request(OSD_W, -1)
        self.card.set_margin_top(CARD_TOP)
        self.card.set_margin_bottom(14)
        self.l_ico = Gtk.Label(label="")
        self.l_ico.get_style_context().add_class("ico")
        self.bar = Gtk.DrawingArea()
        self.bar.set_size_request(150, 28)
        self.bar.set_hexpand(True)
        self.bar.set_valign(Gtk.Align.CENTER)
        self.bar.connect("draw", self.draw_bar)
        self.l_pct = Gtk.Label(label="")
        self.l_pct.set_xalign(1.0)
        self.l_pct.get_style_context().add_class("pct")
        self.card.pack_start(self.l_ico, False, False, 0)
        self.card.pack_start(self.bar, True, True, 0)
        self.card.pack_start(self.l_pct, False, False, 0)
        self.stage = Stage(self.card, (OSD_W + 80) / 2.0)
        self.stage.pack_start(self.card, True, True, 0)
        self.add(self.stage)
        self.connect("destroy", lambda *_: setattr(self, "alive", False))
        self.connect("realize", lambda *_: GLib.idle_add(self.click_through))
        self.stage.show_all()
        GLib.timeout_add(100, self.idle_check)

    def click_through(self):
        """The pop-up never takes clicks: an empty input region lets everything pass through to what is below."""
        try:
            import cairo
            gw = self.get_window()
            if gw is not None:
                gw.input_shape_combine_region(cairo.Region(), 0, 0)
        except Exception:
            pass
        return False

    # ---- state
    def set_level(self, kind, value, muted):
        self.kind, self.value, self.muted = kind, float(value), muted
        self.deadline = time.monotonic() + HOLD_SECS
        if kind == "volume":
            if muted or value <= 0:
                g = GLYPH["vol_mute"] if muted else GLYPH["vol_off"]
            else:
                g = GLYPH["vol_low"] if value < 34 else GLYPH["vol_mid"] if value < 67 else GLYPH["vol_high"]
        else:
            g = GLYPH["bri"]
        self.l_ico.set_text(g)
        self.l_pct.set_text("Muted" if muted else f"{int(round(value))}%")
        if self.anim_tick is None:
            self.anim_tick = self.add_tick_callback(self.ease)

    def ease(self, _w, _clock):
        if not self.alive:
            self.anim_tick = None
            return False
        target = 0.0 if self.muted else self.value
        self.shown += (target - self.shown) * 0.32
        if abs(target - self.shown) < 0.15:
            self.shown = target
            self.anim_tick = None
            self.bar.queue_draw()
            return False
        self.bar.queue_draw()
        return True

    def idle_check(self):
        if not self.alive:
            return False
        try:
            if not self.leaving and time.monotonic() > self.deadline:
                self.ctl.close()
        except Exception as exc:
            print("osd idle error:", repr(exc), file=sys.stderr)
        return True

    def animate_in(self):
        self.stage.run("in")

    def animate_out(self):
        if self.leaving or not self.alive:
            return
        self.leaving = True
        self.stage.run("out", lambda: GLib.idle_add(lambda: (self.destroy(), False)[1]))
        GLib.timeout_add(600, lambda: (self.destroy() if self.alive else None, False)[1])    # never linger

    # ---- drawing
    def rgb(self, name, fallback):
        try:
            ok, c = self.get_style_context().lookup_color(name)
            if ok:
                return c.red, c.green, c.blue
        except Exception:
            pass
        return fallback

    def draw_bar(self, w, cr):
        import cairo
        W, H = w.get_allocated_width(), w.get_allocated_height()
        bh = 10.0
        y = (H - bh) / 2.0
        ar, ag, ab = self.rgb("accent", (0.8, 0.65, 0.97))
        er, eg, eb = self.rgb("accent2", (0.54, 0.7, 0.98))
        if self.value > 100 and self.kind == "volume":                    # over 100 %: the end of the bar warms up
            er, eg, eb = self.rgb("red", (0.95, 0.55, 0.66))
        rrect(cr, 0, y, W, bh, bh / 2.0)                                   # glass track
        cr.set_source_rgba(1, 1, 1, 0.16)
        cr.fill_preserve()
        shade = cairo.LinearGradient(0, y, 0, y + bh)
        shade.add_color_stop_rgba(0, 0, 0, 0, 0.18)
        shade.add_color_stop_rgba(1, 0, 0, 0, 0.0)
        cr.set_source(shade)
        cr.fill()
        frac = _clamp(self.shown / 100.0)
        fw = W * frac
        if fw > 0.5:
            fw = max(fw, bh)
            dim = 0.35 if self.muted else 1.0
            for i in range(4, 0, -1):                                      # soft glow behind the fill
                rrect(cr, -i, y - i, fw + 2 * i, bh + 2 * i, (bh + 2 * i) / 2.0)
                cr.set_source_rgba(ar, ag, ab, 0.07 * dim)
                cr.fill()
            grad = cairo.LinearGradient(0, 0, W, 0)                        # accent -> accent2 along the bar
            grad.add_color_stop_rgba(0, ar, ag, ab, dim)
            grad.add_color_stop_rgba(1, er, eg, eb, dim)
            rrect(cr, 0, y, fw, bh, bh / 2.0)
            cr.set_source(grad)
            cr.fill_preserve()
            gloss = cairo.LinearGradient(0, y, 0, y + bh)                  # glossy top half of the fill
            gloss.add_color_stop_rgba(0, 1, 1, 1, 0.10 * dim)
            gloss.add_color_stop_rgba(0.55, 1, 1, 1, 0.0)
            cr.set_source(gloss)
            cr.fill()
            kx, ky, kr = fw - bh / 2.0, H / 2.0, 6.0                       # white knob at the tip
            cr.arc(kx, ky + 1.5, kr + 1.5, 0, 2 * math.pi)
            cr.set_source_rgba(0, 0, 0, 0.22 * dim)
            cr.fill()
            cr.arc(kx, ky, kr, 0, 2 * math.pi)
            cr.set_source_rgba(1, 1, 1, 0.96 * dim)
            cr.fill()
        return False


# ------------------------------------------------------------------ controller
class Controller:
    def __init__(self):
        self.win = None
        self.prov = None
        self.colors_mtime = None
        self.reload_css()

    @staticmethod
    def _mtime():
        try:
            return os.path.getmtime(COLORS_CSS)
        except OSError:
            return 0

    def reload_css(self):
        """(Re)load colours; called whenever the wallpaper colour file changed, so the accent follows the wallpaper."""
        screen = Gdk.Screen.get_default()
        if self.prov:
            Gtk.StyleContext.remove_provider_for_screen(screen, self.prov)
        colors = FALLBACK
        if pc is not None:
            try:
                colors = pc.css_colors()
            except Exception:
                pass
        self.prov = make_provider(colors + CSS)
        Gtk.StyleContext.add_provider_for_screen(screen, self.prov, Gtk.STYLE_PROVIDER_PRIORITY_USER + 100)
        self.colors_mtime = self._mtime()

    def panel_open(self):
        """The settings panel sits in the same spot, so stay out of its way while it is open."""
        try:
            layers = json.loads(run(["hyprctl", "layers", "-j"], 0.8) or "{}")
            return "rice-panel" in json.dumps(layers)
        except Exception:
            return False

    def show(self, kind, value, muted):
        if self.win is not None and not self.win.leaving:
            self.win.set_level(kind, value, muted)
            return False
        if self.panel_open():
            return False
        if self._mtime() != self.colors_mtime:
            self.reload_css()
        self.win = OsdWindow(self)
        self.win.set_level(kind, value, muted)
        self.win.shown = 0.0 if kind else value                           # the bar fills in as the pop-up opens
        self.win.show()
        self.win.animate_in()
        return False

    def close(self):
        w, self.win = self.win, None
        if w is not None:
            w.animate_out()
        return True


def claim_lock():
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit(0)                                   # already running
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    return fd


def add_unix_signal(signum, handler):
    import warnings
    for name in ("signal_add", "signal_add_full"):
        try:
            from gi.repository import GLibUnix
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                getattr(GLibUnix, name)(GLib.PRIORITY_HIGH, signum, handler)
            return
        except Exception:
            continue
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signum, handler)
        return
    except Exception:
        pass
    signal.signal(signum, lambda *_: Gtk.main_quit())


def start_watchdog():
    """If the main loop stalls for 8 s, log stacks and exit (the pop-up then disappears); the ticker restarts us."""
    import faulthandler
    faulthandler.enable(all_threads=True)
    beat = [time.monotonic()]
    GLib.timeout_add(1000, lambda: (beat.__setitem__(0, time.monotonic()), True)[1])

    def run_():
        while True:
            time.sleep(2)
            if time.monotonic() - beat[0] > 8:
                print("osd: main loop stalled, exiting", file=sys.stderr, flush=True)
                faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
                os._exit(1)
    threading.Thread(target=run_, daemon=True).start()


def main():
    _lock = claim_lock()  # noqa: F841 (held for the process lifetime)
    ctl = Controller()
    start_watchdog()
    # windows are opened from a normal idle callback, never from a worker thread or a signal callback
    Watcher(lambda kind, v, muted: GLib.idle_add(ctl.show, kind, v, muted)).start()
    add_unix_signal(signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    add_unix_signal(signal.SIGINT, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()
