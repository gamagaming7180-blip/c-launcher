#!/usr/bin/env python3
"""media-card: a small glass "now playing" card that drops out of the media ticker in the bar, styled like the
quick-settings panel.

  * Shows cover art (music, YouTube, anything that reports art over MPRIS), title, artist, an equalizer that follows
    the real audio (needs cava, optional), a seekable progress bar and prev / play-pause / next.
  * A droplet leaves the ticker, falls under it and opens into the card. Pops out by itself when a new track starts.
  * It always closes by itself after IDLE_SECS seconds without activity on it (your mouse on it counts as activity).
  * media-card.py            toggle the card (this is what clicking the ticker runs)
    media-card.py --hidden   start the background watcher without showing anything
"""
import colorsys
import ctypes
import json
import fcntl
import hashlib
import math
import os
import shutil
import signal
import subprocess as sp
import sys
import threading
import time
import urllib.parse
import urllib.request

try:   # gtk-layer-shell must load before libwayland-client
    ctypes.CDLL("libgtk-layer-shell.so.0", mode=ctypes.RTLD_GLOBAL)
except OSError:
    pass
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from mediaspec import Spectrum
except Exception:
    Spectrum = None
try:
    import panelcore as pc            # reuses the settings panel's colour scheme when it is installed
except Exception:
    pc = None

try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GLib, Gtk, Gdk, GdkPixbuf, Pango  # noqa: E402
    from gi.repository import GtkLayerShell  # noqa: E402
except (ImportError, ValueError):
    print("media-card needs: sudo pacman -S python-gobject gtk3 gtk-layer-shell playerctl", file=sys.stderr)
    sys.exit(1)

XPOS_FILE = os.path.expanduser("~/.cache/hypr-rice/media-ticker-x")
RUNTIME = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
LOCK = os.path.join(RUNTIME, "hypr-rice-media-card.lock")
ART_DIR = os.path.expanduser("~/.cache/hypr-rice/media-art")

# ---- tweak here -------------------------------------------------------------------------------------------
CARD_W = 392             # card width
CARD_TOP = 48            # px from the top of the screen to the top of the card (just under your 40px bar)
PILL_W, PILL_H, PILL_Y = 152, 31, 9   # the media ticker in the bar: the droplet starts exactly on it
DEFAULT_TICKER_X = 330   # px from the left of the screen to the middle of the ticker (used when it cannot be measured)
IDLE_SECS = 3.0          # the card closes after this long without activity on it
USE_CAVA = True          # equalizer follows the real audio when cava is installed; False = decorative bars only
ART = 112                # cover size in px
ART_PAD = 8              # room around the cover for its soft glow
GLASS = 0.88             # how solid the glass is: 0 = clear, 1 = opaque (raise to ~0.30 on bright wallpapers)
RADIUS = 28              # card corner radius
G = dict(prev="\U000f04ae", next="\U000f04ad", play="\U000f040a", pause="\U000f03e4", close="\U000f0156")

FALLBACK_COLORS = """
@define-color base #1e1e2e; @define-color text #cdd6f4; @define-color subtext #a6adc8;
@define-color red #f38ba8; @define-color accent #cba6f7; @define-color accent2 #89b4fa;
"""

CSS = """
.mc, .mc * { font-family: "JetBrainsMono Nerd Font", "Noto Sans", sans-serif; font-size: 12px; }
window.mc { background-color: transparent; }
.mc label { text-shadow: 0 1px 3px rgba(0,0,0,0.35); }
.mc .cardflat { background-color: transparent; border: 1px solid transparent; border-radius: %RADIUS%px;
                padding: 16px 16px 16px 8px; }
.mc .card { background-color: alpha(@base, %GLASS%);
            background-image: linear-gradient(to bottom right, alpha(@accent, 0.22), alpha(@accent2, 0.06), alpha(@accent, 0.14));
            border: 1px solid alpha(@text, 0.12); 
            border-radius: %RADIUS%px; padding: 16px 16px 16px 8px;
            box-shadow: inset 0 0 0 0 transparent; }
.mc button { background-image: none; background-color: transparent; box-shadow: none; text-shadow: none;
             border: 1px solid transparent; border-radius: 14px; padding: 0; margin: 0; min-height: 0; min-width: 0;
             color: @text; outline-style: none; }
.mc .chip { background-color: alpha(@text, 0.10); border-radius: 12px; padding: 3px 10px 3px 9px;
            box-shadow: inset 0 0 0 0 transparent; }
.mc .title { font-weight: 800; font-size: 14px; }
.mc .artist { color: @subtext; font-size: 11px; font-weight: 600; }
.mc .player { color: @text; font-size: 10px; font-weight: 700; }
.mc .time { color: @subtext; font-size: 10px; font-weight: 700; }
.mc .ctl { border-radius: 19px; min-width: 40px; min-height: 40px; font-size: 18px; }
.mc .ctl:hover { background-color: alpha(@text, 0.14); }
.mc .ctl.play { min-width: 48px; min-height: 48px; border-radius: 24px; font-size: 21px; color: @base;
                background-image: linear-gradient(135deg, @accent, @accent2);
                box-shadow: inset 0 0 0 0 transparent, 0 4px 16px alpha(@accent, 0.45); }
.mc .ctl.play:hover { box-shadow: inset 0 0 0 0 transparent, 0 4px 22px alpha(@accent, 0.7); }
.mc .ctl.play label { text-shadow: none; }
.mc .x { color: @subtext; border-radius: 11px; min-width: 22px; min-height: 22px; font-size: 11px;
         background-color: alpha(@text, 0.08); }
.mc .x:hover { background-color: alpha(@text, 0.2); color: @text; }
.mc scale trough { min-height: 6px; border-radius: 3px; background-color: alpha(@text, 0.16); border: none;
                   background-image: none; box-shadow: inset 0 1px 1px rgba(0,0,0,0.2); }
.mc scale highlight { background-color: transparent; border-radius: 3px; border: none;
                      background-image: linear-gradient(90deg, @accent, @accent2); }
.mc scale slider { min-width: 12px; min-height: 12px; margin: -3px; border-radius: 6px; border: none;
                   background-color: #ffffff; background-image: none; box-shadow: 0 1px 4px rgba(0,0,0,0.45); }
""".replace("%GLASS%", str(GLASS)).replace("%RADIUS%", str(RADIUS))


# ------------------------------------------------------------------ playerctl
def run(args, timeout=1.2):
    try:
        p = sp.run(args, text=True, stdout=sp.PIPE, stderr=sp.DEVNULL, timeout=timeout, check=False)
    except (OSError, sp.TimeoutExpired):
        return ""
    return p.stdout.strip() if p.returncode == 0 else ""


def to_secs(v):
    try:
        return max(0.0, float(v) / 1e6)
    except (TypeError, ValueError):
        return 0.0


def query_media():
    """The player that is playing (else the first paused one) -> dict, or None."""
    if not shutil.which("playerctl"):
        return None
    full = ("playerName", "playerInstance", "status", "title", "artist", "album", "mpris:artUrl", "mpris:length",
            "position")
    out = run(["playerctl", "-a", "metadata", "--format", "\t".join("{{%s}}" % f for f in full)])
    if not out:                                   # very old playerctl: retry with the basic fields only
        basic = full[:6]
        out = run(["playerctl", "-a", "metadata", "--format", "\t".join("{{%s}}" % f for f in basic)])
    playing, paused = [], []
    for line in out.splitlines():
        f = [x.strip() for x in (line.split("\t") + [""] * 9)[:9]]
        name, inst, status, title, artist, album, art, length, pos = f
        if status not in ("Playing", "Paused") or not (title or artist or album):
            continue
        item = dict(player=name or "media", inst=inst or name, status=status, title=title or "Unknown track",
                    artist=artist or album, art=art, length=to_secs(length), pos=to_secs(pos))
        (playing if status == "Playing" else paused).append(item)
    return playing[0] if playing else (paused[0] if paused else None)


class Monitor:
    """Polls playerctl in a thread so the UI never waits on it."""

    def __init__(self):
        self.lock = threading.Lock()
        self.media, self.stamp, self.seq, self.last_key = None, 0.0, 0, None
        self.wake = threading.Event()

    def start(self):
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            m = query_media()
            with self.lock:
                self.media, self.stamp = m, time.monotonic()
                key = (m["player"], m["title"], m["artist"]) if m else None
                if key and key != self.last_key:
                    self.seq += 1
                self.last_key = key
            self.wake.wait(0.6)
            self.wake.clear()

    def snap(self):
        with self.lock:
            return (dict(self.media) if self.media else None), self.stamp, self.seq


def player_cmd(media, *args):
    if media:
        threading.Thread(target=lambda: run(["playerctl", "-p", media["inst"], *args], 2.0), daemon=True).start()


# ------------------------------------------------------------------ where is the ticker?
def screen_info():
    """(screen logical width, cursor x on that screen, cursor y, monitor x, monitor y) from Hyprland, or None."""
    try:
        cur = json.loads(run(["hyprctl", "cursorpos", "-j"]) or "null")
        mons = json.loads(run(["hyprctl", "monitors", "-j"]) or "null")
        cx, cy = cur["x"], cur["y"]
        for m in mons:
            sc = m.get("scale") or 1.0
            w, h = m["width"] / sc, m["height"] / sc
            if m["x"] <= cx < m["x"] + w and m["y"] <= cy < m["y"] + h:
                return int(w), cx - m["x"], cy - m["y"], m["x"], m["y"]
        m = next((m for m in mons if m.get("focused")), mons[0])
        return int(m["width"] / (m.get("scale") or 1.0)), None, None, m["x"], m["y"]
    except Exception:
        return None


ORIGIN = [(0, 0)]      # top-left of the monitor the card is on (global coordinates)


def cursor_global():
    try:
        c = json.loads(run(["hyprctl", "cursorpos", "-j"], 0.6) or "null")
        return c["x"], c["y"]
    except Exception:
        return None


def ticker_x(from_click):
    """Middle of the ticker. A click on it is measured from the cursor; otherwise the last click or the default."""
    info = screen_info()
    sw = info[0] if info else 1600
    ORIGIN[0] = (info[3], info[4]) if info else (0, 0)
    x = None
    if from_click and info and info[1] is not None and 0 <= info[2] <= 60:     # cursor is on the bar
        x = info[1]
        try:
            os.makedirs(os.path.dirname(XPOS_FILE), exist_ok=True)
            with open(XPOS_FILE, "w") as fh:
                fh.write(str(int(x)))
        except OSError:
            pass
    if x is None:
        try:
            x = int(open(XPOS_FILE).read().strip())
        except (OSError, ValueError):
            x = DEFAULT_TICKER_X
    return sw, x


# ------------------------------------------------------------------ cover art
def fetch_art(url):
    """Local path for a cover URL (file://, http(s)://) or None. Downloads are cached."""
    if not url:
        return None
    try:
        if url.startswith("file://"):
            path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
            return path if os.path.isfile(path) else None
        if not url.startswith(("http://", "https://")):
            return None
        os.makedirs(ART_DIR, exist_ok=True)
        path = os.path.join(ART_DIR, hashlib.sha1(url.encode()).hexdigest())
        if not os.path.isfile(path):
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (media-card)"})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = r.read(8_000_000)
            with open(path + ".part", "wb") as fh:
                fh.write(data)
            os.replace(path + ".part", path)
        files = sorted((os.path.join(ART_DIR, n) for n in os.listdir(ART_DIR)), key=os.path.getmtime)
        for old in files[:-80]:                                  # keep the cache small
            try:
                os.unlink(old)
            except OSError:
                pass
        return path
    except Exception as exc:
        print("media-card: art fetch failed:", repr(exc), file=sys.stderr)
        return None


def load_pixbuf(path):
    try:
        return GdkPixbuf.Pixbuf.new_from_file(path)
    except Exception:
        return None


def tint_from_pixbuf(pb):
    """A pleasant accent colour (hex) taken from the cover, or None."""
    try:
        small = pb.scale_simple(12, 12, GdkPixbuf.InterpType.BILINEAR)
        n, rs, data = small.get_n_channels(), small.get_rowstride(), small.get_pixels()
        best, best_score = None, -1.0
        for y in range(12):
            for x in range(12):
                i = y * rs + x * n
                r, g, b = data[i] / 255.0, data[i + 1] / 255.0, data[i + 2] / 255.0
                h, l, s = colorsys.rgb_to_hls(r, g, b)
                score = s * (1 - abs(l - 0.55) * 1.2)           # prefer vivid, mid-light pixels
                if score > best_score:
                    best, best_score = (h, l, s), score
        h, l, s = best
        r, g, b = colorsys.hls_to_rgb(h, max(0.58, min(0.74, l)), max(0.45, s))
        return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
    except Exception:
        return None


# ------------------------------------------------------------------ small helpers
ACT = [time.monotonic()]


def poke():
    ACT[0] = time.monotonic()


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


def btn(text, cls, fn):
    b = Gtk.Button()
    old = b.get_child()
    if old is not None:
        b.remove(old)
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.set_focus_on_click(False)
    for c in cls.split():
        b.get_style_context().add_class(c)
    b.add(lab(text, xalign=0.5))
    b.connect("clicked", lambda *_: (poke(), fn()))
    return b


def set_btn_text(b, text):
    ch = b.get_child()
    if isinstance(ch, Gtk.Label):
        ch.set_text(text)


def fmt_time(sec):
    sec = int(max(0, sec))
    return f"{sec // 60}:{sec % 60:02d}"


def colors_css():
    if pc is not None:
        try:
            return pc.css_colors()
        except Exception:
            pass
    return FALLBACK_COLORS


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
            print("media-card: skipped a CSS rule:", exc.message, file=sys.stderr)
    p = Gtk.CssProvider()
    p.load_from_data("\n".join(good).encode())
    return p


def rrect(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


# ------------------------------------------------------------------ droplet: ticker -> card
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
    """Fills the window. While animating it draws a droplet that starts on the ticker, falls, widens and settles into
    the card, then fades the contents in. At rest it draws nothing special."""
    __gtype_name__ = "RiceMediaStage"

    def __init__(self, card, pill_cx):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.card, self.pill_cx = card, pill_cx
        self.pair_fn = None                      # () -> ((r,g,b), (r,g,b)): the two glass tint colours
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
            a1, a2 = self.pair_fn() if self.pair_fn else ((0.8, 0.65, 0.97), (0.54, 0.7, 0.98))
            res = draw_droplet(cr, self.t, self.pill_cx, PILL_W, PILL_H, PILL_Y, (cx, cy, cw, ch), base, a1, a2, GLASS,
                               RADIUS, 15.0)
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
            GLib.timeout_add(1600, lambda: (self._rescue(), False)[1])

    def _rescue(self):
        if self.animating and self._tick is not None:
            self.remove_tick_callback(self._tick)
            self._tick = None
            self.t = 1.0
            self._settle()


# ------------------------------------------------------------------ the card window
class MiniWindow(Gtk.Window):
    def __init__(self, ctl, screen_w, tx):
        super().__init__()
        self.ctl = ctl
        self.alive, self.leaving = True, False
        self.born, self.cursor_last, self.card_rect = time.monotonic(), None, (0, 0, 0, 0)
        self.card_left_abs = 0
        self.media = None
        self.pb = None
        self.art_url = None
        self.tint = None
        self.tint_provider = None
        self.length, self.pos0, self.stamp, self.playing = 0.0, 0.0, time.monotonic(), False
        self.dragging_until = 0.0
        self.get_style_context().add_class("mc")
        self.set_title("rice-media-card")
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "rice-media-card")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        card_left = int(max(12, min(tx - CARD_W / 2.0, screen_w - CARD_W - 12)))     # card sits under the ticker
        win_left = max(0, card_left - 40)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, win_left)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)   # never steals typing focus
        self.set_size_request(CARD_W + 80, -1)

        self.card = box(True, 0, "cardflat")
        self.card.set_halign(Gtk.Align.START)
        self.card.set_size_request(CARD_W, -1)
        self.card.set_margin_start(card_left - win_left)
        self.card.set_margin_top(CARD_TOP)
        self.card.set_margin_bottom(16)
        self.card_left_abs = card_left
        self.stage = Stage(self.card, tx - win_left)
        self.stage.pair_fn = self.grad_pair
        self.stage.pack_start(self.card, True, True, 0)
        self.add(self.stage)

        row = box(False, 6)
        self.card.pack_start(row, True, True, 0)
        self.art = Gtk.DrawingArea()
        self.art.set_size_request(ART + 2 * ART_PAD, ART + 2 * ART_PAD)
        self.art.set_valign(Gtk.Align.CENTER)
        self.art.connect("draw", self.draw_art)
        row.pack_start(self.art, False, False, 0)

        col = box(True, 0)
        row.pack_start(col, True, True, 0)
        top = box(False, 8)
        self.eq = Gtk.DrawingArea()
        self.eq.set_size_request(42, 14)
        self.eq.set_valign(Gtk.Align.CENTER)
        self.eq.connect("draw", self.draw_eq)
        self.l_player = lab("", "player", ellipsize=14)
        chip = box(False, 7, "chip")
        chip.set_halign(Gtk.Align.START)
        chip.pack_start(self.eq, False, False, 0)
        chip.pack_start(self.l_player, False, False, 0)
        top.pack_start(chip, False, False, 0)
        top.pack_end(btn(G["close"], "x", lambda: ctl.close()), False, False, 0)
        col.pack_start(top, False, False, 0)
        self.l_title = lab("", "title", ellipsize=24)
        self.l_artist = lab("", "artist", ellipsize=30)
        col.pack_start(self.l_title, False, False, 2)
        col.pack_start(self.l_artist, False, False, 0)

        prog = box(False, 6)
        self.l_pos, self.l_len = lab("0:00", "time"), lab("0:00", "time", xalign=1.0)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1000, 1)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        self.scale.connect("change-value", self.on_seek)
        prog.pack_start(self.l_pos, False, False, 0)
        prog.pack_start(self.scale, True, True, 0)
        prog.pack_start(self.l_len, False, False, 0)
        col.pack_start(prog, False, False, 10)

        ctls = box(False, 6)
        ctls.set_halign(Gtk.Align.CENTER)
        self.b_prev = btn(G["prev"], "ctl", lambda: self.cmd("previous"))
        self.b_play = btn(G["play"], "ctl play", lambda: self.cmd("play-pause"))
        self.b_next = btn(G["next"], "ctl", lambda: self.cmd("next"))
        for b in (self.b_prev, self.b_play, self.b_next):
            ctls.pack_start(b, False, False, 0)
        col.pack_start(ctls, False, False, 0)

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("motion-notify-event", lambda *_: (poke(), False)[1])
        self.connect("destroy", self.on_destroy)
        self.card.connect("size-allocate", lambda *_: GLib.idle_add(self.set_input_region))
        self.stage.show_all()
        poke()
        GLib.timeout_add(250, self.tick)
        GLib.timeout_add(70, self.anim)
        GLib.timeout_add(300, self.idle_check)
        GLib.timeout_add(400, self.cursor_poll)

    # ---- window plumbing
    def on_destroy(self, *_):
        self.alive = False
        if self.ctl.win is None and self.ctl.spec:
            self.ctl.spec.stop()                         # nobody is watching: stop analysing audio
        if self.tint_provider is not None:
            Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(), self.tint_provider)
            self.tint_provider = None

    def set_input_region(self):
        if not self.alive:
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
        GLib.timeout_add(700, lambda: (self.destroy() if self.alive else None, False)[1])   # never linger

    # ---- content
    def cmd(self, c):
        player_cmd(self.media, c)
        self.ctl.mon.wake.set()
        if c == "play-pause":
            self.playing = not self.playing
            set_btn_text(self.b_play, G["pause"] if self.playing else G["play"])
            self.pos0, self.stamp = self.current_pos(), time.monotonic()

    def on_seek(self, _s, _st, v):
        poke()
        if self.media and self.length > 0:
            secs = max(0.0, min(self.length, v / 1000.0 * self.length))
            self.dragging_until = time.monotonic() + 1.2
            self.pos0, self.stamp = secs, time.monotonic()
            self.l_pos.set_text(fmt_time(secs))
            player_cmd(self.media, "position", f"{secs:.1f}")
        return False

    def current_pos(self):
        p = self.pos0 + (time.monotonic() - self.stamp if self.playing else 0.0)
        return min(p, self.length) if self.length > 0 else p

    def update(self, media, stamp):
        if not self.alive or self.leaving:
            return
        self.media = media
        if media is None:
            self.l_title.set_text("Nothing playing")
            self.l_artist.set_text("Start some music or a video")
            self.l_player.set_text("")
            self.playing, self.length, self.pos0 = False, 0.0, 0.0
            set_btn_text(self.b_play, G["play"])
            self.set_art(None)
            return
        self.l_title.set_text(media["title"])
        self.l_artist.set_text(media["artist"] or media["player"])
        self.l_player.set_text(media["player"].capitalize())
        self.playing = media["status"] == "Playing"
        set_btn_text(self.b_play, G["pause"] if self.playing else G["play"])
        self.length = media["length"]
        if time.monotonic() > self.dragging_until:
            self.pos0, self.stamp = media["pos"], stamp
        self.l_len.set_text(fmt_time(self.length) if self.length else "--:--")
        self.set_art(media["art"])

    def set_art(self, url):
        if url == self.art_url:
            return
        self.art_url = url
        if not url:
            self.pb = None
            self.set_tint(None)
            self.art.queue_draw()
            return

        def work():
            path = fetch_art(url)
            return load_pixbuf(path) if path else None

        def done(pb):
            if self.alive and url == self.art_url:
                self.pb = pb
                self.set_tint(tint_from_pixbuf(pb) if pb else None)
                self.art.queue_draw()
        threading.Thread(target=lambda: GLib.idle_add(lambda r=work(): (done(r), False)[1]), daemon=True).start()

    @staticmethod
    def tint_pair(hexcolor):
        """Two neighbouring colours (0..255 ints) built from the cover colour: for the gradients."""
        h = hexcolor.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
        r2, g2, b2 = colorsys.hls_to_rgb((hh + 0.07) % 1.0, min(0.80, ll + 0.10), ss)
        return (int(r * 255), int(g * 255), int(b * 255)), (int(r2 * 255), int(g2 * 255), int(b2 * 255))

    def set_tint(self, hexcolor):
        if hexcolor == self.tint:
            return
        self.tint = hexcolor
        screen = Gdk.Screen.get_default()
        if self.tint_provider is not None:
            Gtk.StyleContext.remove_provider_for_screen(screen, self.tint_provider)
            self.tint_provider = None
        if hexcolor:
            (r1, g1, b1), (r2, g2, b2) = self.tint_pair(hexcolor)
            c1, c2 = f"rgb({r1},{g1},{b1})", f"rgb({r2},{g2},{b2})"
            css = (f".mc scale highlight {{ background-image: linear-gradient(90deg, {c1}, {c2}); }} "
                   f".mc .ctl.play {{ background-image: linear-gradient(135deg, {c1}, {c2}); "
                   f"box-shadow: inset 0 0 0 0 transparent, 0 4px 16px rgba({r1},{g1},{b1},0.5); }} "
                   f".mc .card {{ background-image: linear-gradient(to bottom right, rgba({r1},{g1},{b1},0.22), "
                   f"rgba({r2},{g2},{b2},0.06), rgba({r1},{g1},{b1},0.14)); }}")
            self.tint_provider = make_provider(css)
            Gtk.StyleContext.add_provider_for_screen(screen, self.tint_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 300)
        self.eq.queue_draw()
        self.art.queue_draw()
        self.stage.queue_draw()

    def grad_pair(self):
        """The two glass tint colours (0..1 floats) for the opening droplet: cover colours, else wallpaper accents."""
        if self.tint:
            a, b = self.tint_pair(self.tint)
            return tuple(v / 255.0 for v in a), tuple(v / 255.0 for v in b)
        out = []
        for name, fb in (("accent", (0.8, 0.65, 0.97)), ("accent2", (0.54, 0.7, 0.98))):
            try:
                ok, c = self.get_style_context().lookup_color(name)
                out.append((c.red, c.green, c.blue) if ok else fb)
            except Exception:
                out.append(fb)
        return out[0], out[1]

    def accent_rgb(self):
        if self.tint:
            h = self.tint.lstrip("#")
            return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        try:
            ok, c = self.get_style_context().lookup_color("accent")
            if ok:
                return c.red, c.green, c.blue
        except Exception:
            pass
        return 0.8, 0.65, 0.97

    # ---- drawing
    def draw_art(self, w, cr):
        import cairo
        s, p, rad = ART, ART_PAD, 22
        ar, ag, ab = self.accent_rgb()
        for i in range(p, 0, -1):                              # soft glow in the cover's colour
            rrect(cr, p - i, p - i + 3, s + 2 * i, s + 2 * i, rad + i)
            cr.set_source_rgba(ar, ag, ab, 0.05)
            cr.fill()
        cr.save()
        cr.translate(p, p)
        rrect(cr, 0, 0, s, s, rad)
        cr.clip_preserve()
        if self.pb is not None:
            pw, ph = self.pb.get_width(), self.pb.get_height()
            k = max(s / pw, s / ph)
            cr.save()
            cr.translate((s - pw * k) / 2.0, (s - ph * k) / 2.0)
            cr.scale(k, k)
            Gdk.cairo_set_source_pixbuf(cr, self.pb, 0, 0)
            cr.paint()
            cr.restore()
        else:
            grad = cairo.LinearGradient(0, 0, s, s)
            grad.add_color_stop_rgba(0, ar, ag, ab, 0.60)
            grad.add_color_stop_rgba(1, ar * 0.5, ag * 0.5, ab * 0.7, 0.35)
            cr.set_source(grad)
            cr.fill_preserve()
            cr.set_source_rgba(1, 1, 1, 0.85)
            cr.select_font_face("sans-serif")
            cr.set_font_size(48)
            ext = cr.text_extents("\u266a")
            cr.move_to((s - ext.width) / 2.0 - ext.x_bearing, (s + ext.height) / 2.0)
            cr.show_text("\u266a")
        sheen = cairo.LinearGradient(0, 0, 0, s * 0.5)         # glassy sheen across the top of the cover
        sheen.add_color_stop_rgba(0, 1, 1, 1, 0.16)
        sheen.add_color_stop_rgba(1, 1, 1, 1, 0.0)
        rrect(cr, 0, 0, s, s, rad)
        cr.set_source(sheen)
        cr.fill()
        cr.reset_clip()
        rrect(cr, 0.5, 0.5, s - 1, s - 1, rad)
        rim = cairo.LinearGradient(0, 0, 0, s)
        rim.add_color_stop_rgba(0, 1, 1, 1, 0.12)
        rim.add_color_stop_rgba(1, 1, 1, 1, 0.12)
        cr.set_source(rim)
        cr.set_line_width(1)
        cr.stroke()
        cr.restore()
        return False

    def draw_eq(self, w, cr):
        t = time.monotonic()
        r, g, b = self.accent_rgb()
        cr.set_source_rgba(min(1.0, r + 0.12), min(1.0, g + 0.12), min(1.0, b + 0.12), 0.95)
        n, bw, gap, H = 8, 3, 2.2, 14
        levels = self.ctl.spec.get() if (self.ctl.spec and self.playing) else None
        for i in range(n):
            if levels:
                lvl = levels[i]
            elif self.playing:
                a = (math.sin(t * 5.3 - i * 0.88) + 1) / 2
                bb = (math.sin(t * 3.1 + i * 0.63 + 0.8) + 1) / 2
                c = (math.sin(t * 7.1 - i * 1.17 + 1.4) + 1) / 2
                lvl = max(0.0, min(1.0, a * 0.54 + bb * 0.31 + c * 0.15))
            else:
                lvl = 0.12 + 0.05 * (i % 3)
            h = max(2.0, lvl * H)
            rrect(cr, i * (bw + gap), H - h, bw, h, 1.8)
            cr.fill()
        return False

    def anim(self):
        if not self.alive:
            return False
        if self.playing:
            if self.ctl.spec:
                self.ctl.spec.start()
            self.eq.queue_draw()
        return True

    def tick(self):
        if not self.alive:
            return False
        try:
            if not self.leaving:
                pos = self.current_pos()
                if time.monotonic() > self.dragging_until and self.length > 0:
                    self.scale.set_value(pos / self.length * 1000.0)
                self.l_pos.set_text(fmt_time(pos))
        except Exception as exc:                       # an error here must never stop the timer
            print("media-card tick error:", repr(exc), file=sys.stderr)
        return True

    def idle_check(self):
        """Close after IDLE_SECS with no click / slider move / pointer movement over the card. Also a hard cap."""
        if not self.alive:
            return False
        try:
            if not self.leaving and (time.monotonic() - ACT[0] > IDLE_SECS or time.monotonic() - self.born > 40):
                self.ctl.close()
        except Exception as exc:
            print("media-card idle error:", repr(exc), file=sys.stderr)
        return True

    def cursor_poll(self):
        """Ask Hyprland where the cursor is (reliable even when GTK misses enter/leave events); movement over the
        card counts as activity."""
        if not self.alive or self.leaving:
            return self.alive

        def work():
            return cursor_global()

        def done(c):
            if c is None or not self.alive:
                return
            lx, ly = c[0] - ORIGIN[0][0], c[1] - ORIGIN[0][1]
            h = self.card.get_allocated_height()
            inside = self.card_left_abs <= lx <= self.card_left_abs + CARD_W and CARD_TOP <= ly <= CARD_TOP + h
            if inside and (lx, ly) != self.cursor_last:
                poke()
            self.cursor_last = (lx, ly)
        threading.Thread(target=lambda: GLib.idle_add(lambda r=work(): (done(r), False)[1]), daemon=True).start()
        return True


# ------------------------------------------------------------------ controller
class Controller:
    def __init__(self):
        self.win = None
        self.mon = Monitor()
        self.prov = None
        self.last_seq = None
        self.spec = Spectrum() if (Spectrum and USE_CAVA and Spectrum.available()) else None
        self.reload_css()

    def reload_css(self):
        screen = Gdk.Screen.get_default()
        if self.prov:
            Gtk.StyleContext.remove_provider_for_screen(screen, self.prov)
        self.prov = make_provider(colors_css() + CSS)
        Gtk.StyleContext.add_provider_for_screen(screen, self.prov, Gtk.STYLE_PROVIDER_PRIORITY_USER + 100)

    def start(self):
        self.mon.start()
        GLib.timeout_add(300, self.pump)

    def toggle(self):
        if self.win is not None:
            self.close()
        else:
            self.open(from_click=True)
        return True

    def open(self, from_click=False):
        if self.win is not None:
            return
        self.reload_css()
        poke()
        sw, tx = ticker_x(from_click)
        self.win = MiniWindow(self, sw, tx)
        media, stamp, _ = self.mon.snap()
        self.win.update(media, stamp)
        self.win.show()
        self.win.animate_in()

    def close(self):
        w, self.win = self.win, None
        if w is not None:
            w.animate_out()
        return True

    def pump(self):
        media, stamp, seq = self.mon.snap()
        if self.last_seq is None:
            if stamp:
                self.last_seq = seq                    # first reading: do not pop up for music already playing
            return True
        if seq != self.last_seq:
            self.last_seq = seq
            if media and media["status"] == "Playing" and self.win is None:
                self.open()
            elif self.win is not None:
                poke()
        if self.win is not None:
            self.win.update(media, stamp)
        return True


# ------------------------------------------------------------------ process plumbing
def claim_lock(toggle_running):
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        if toggle_running:
            try:
                os.kill(int(os.read(fd, 32).decode().strip() or 0), signal.SIGUSR1)
            except (OSError, ValueError):
                pass
        sys.exit(0)
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
    flag = {"hit": False}
    signal.signal(signum, lambda *_: flag.__setitem__("hit", True))
    GLib.timeout_add(150, lambda: (flag["hit"] and (flag.__setitem__("hit", False), handler()), True)[1])


def start_watchdog():
    """If the GTK main loop stops answering for 8 s, dump stacks to the log and exit (the compositor then removes the
    card). The Waybar ticker restarts the watcher within about 15 seconds."""
    import faulthandler
    faulthandler.enable(all_threads=True)
    beat = [time.monotonic()]
    GLib.timeout_add(1000, lambda: (beat.__setitem__(0, time.monotonic()), True)[1])

    def run_():
        while True:
            time.sleep(2)
            if time.monotonic() - beat[0] > 8:
                print("media-card: main loop stalled, exiting", file=sys.stderr, flush=True)
                faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
                os._exit(1)
    threading.Thread(target=run_, daemon=True).start()


def main():
    hidden = "--hidden" in sys.argv
    _lock = claim_lock(toggle_running=not hidden)  # noqa: F841 (held for the process lifetime)
    ctl = Controller()
    ctl.start()
    start_watchdog()
    # never open or close a layer-shell window from inside the signal callback itself (it can deadlock in show())
    add_unix_signal(signal.SIGUSR1, lambda: (GLib.idle_add(lambda: (ctl.toggle(), False)[1]), True)[1])
    add_unix_signal(signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    add_unix_signal(signal.SIGINT, lambda: (Gtk.main_quit(), False)[1])
    if not hidden:
        GLib.idle_add(lambda: (ctl.open(from_click=True), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()
