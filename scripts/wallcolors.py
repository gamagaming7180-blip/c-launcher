#!/usr/bin/env python3
"""wallcolors (Vesper theme engine): one wallpaper in, one coherent desktop out.

usage:
  wallcolors.py IMAGE [--persist] [--no-reload]    sample IMAGE, rebuild the whole palette, render every config
  wallcolors.py --reapply [--no-reload]            re-render everything with the current palette and wallpaper
  wallcolors.py IMAGE --accent RRGGBB [--accent2 RRGGBB]   force the accent colours instead of sampling

  --persist    kept for compatibility with wallpaper.sh (the wallpaper is always remembered now)
  --no-reload  write files only; do not poke waybar / mako / kitty / hyprland

How it works: the dominant hues of the wallpaper become `accent` / `accent2`; every dark surface
(bar glass, launcher, notifications, terminal, lock screen) is a very dark tint of the same hue, so the
whole desktop looks like it was cut from one piece of glass. Templates live in ~/.config/hypr-rice/templates;
placeholders:  {{accent}} rrggbb   {{#accent}} #rrggbb   {{accent:cc}} rrggbbcc   {{#accent:cc}} #rrggbbcc
               {{rgba(accent, 0.5)}} rgba(r, g, b, 0.5)   {{wallpaper}} {{lockbg}} {{home}}
Needs Pillow (python-pillow) or ImageMagick to sample images.
"""
import colorsys
import json
import math
import os
import re
import shutil
import subprocess as sp
import sys

RICE = os.environ.get("HYPR_RICE_DIR") or os.path.expanduser("~/.config/hypr-rice")
GEN = os.path.join(RICE, "generated")
TPL = os.path.join(RICE, "templates")
HOME = os.path.expanduser("~")

# template -> destinations (relative to RICE). rofi's list theme is also written under its old name
# because older scripts still pass -theme rofi/catppuccin.rasi.
OUTPUTS = [
    ("colors.css.tpl",          ["waybar/colors.css"]),
    ("mako.tpl",                ["mako/config"]),
    ("kitty-colors.conf.tpl",   ["kitty/colors.conf"]),
    ("hyprlock.conf.tpl",       ["hyprlock.conf"]),
    ("hyprpaper.conf.tpl",      ["hyprpaper.conf"]),
    ("rofi-list.rasi.tpl",      ["rofi/vesper.rasi", "rofi/catppuccin.rasi"]),
    ("rofi-grid.rasi.tpl",      ["rofi/vesper-grid.rasi"]),
]

DEFAULT_H1, DEFAULT_H2 = 0.745, 0.935            # violet + rose when nothing can be sampled


# ------------------------------------------------------------------ sampling
def pixels(path):
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        im.thumbnail((96, 96))
        raw = im.tobytes()
        return [tuple(raw[i:i + 3]) for i in range(0, len(raw) - 2, 3)]
    except Exception:
        pass
    exe = shutil.which("magick") or shutil.which("convert")
    if exe:
        try:
            cmd = [exe, path + "[0]", "-resize", "96x96", "-depth", "8", "txt:-"]
            out = sp.run(cmd, capture_output=True, text=True, timeout=20).stdout
            return [tuple(map(int, m)) for m in re.findall(r"\((\d+),(\d+),(\d+)", out)]
        except Exception:
            pass
    return []


def pick_hues(px):
    """Dominant and secondary hue (0..1) of the vivid pixels, or None for a grey image."""
    sin, cos, wt = [0.0] * 24, [0.0] * 24, [0.0] * 24
    total = 0.0
    for r, g, b in px:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.22 or v < 0.28:                      # skip greys and near-black
            continue
        w = (s ** 1.5) * (0.4 + v)
        i = int(h * 24) % 24
        wt[i] += w
        sin[i] += w * math.sin(h * 2 * math.pi)
        cos[i] += w * math.cos(h * 2 * math.pi)
        total += w
    if total < 5:
        return None

    def hue_of(i):
        return (math.atan2(sin[i], cos[i]) / (2 * math.pi)) % 1.0

    order = sorted(range(24), key=lambda i: -wt[i])
    h1, h2 = hue_of(order[0]), None
    for i in order[1:]:
        d = abs(hue_of(i) - h1)
        d = min(d, 1 - d)
        if d >= 0.11 and wt[i] > 0.25 * wt[order[0]]:
            h2 = hue_of(i)
            break
    if h2 is None:
        h2 = (h1 + 0.09) % 1.0                         # analogous fallback
    return h1, h2


# ------------------------------------------------------------------ palette
def hx(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return "%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def build_palette(h1, h2):
    return {
        # surfaces: dark tints of the wallpaper hue
        "island":   hx(h1, 0.030, 0.25),
        "mantle":   hx(h1, 0.040, 0.28),
        "base":     hx(h1, 0.060, 0.30),
        "glass":    hx(h1, 0.075, 0.34),
        "surface":  hx(h1, 0.115, 0.26),
        "surface2": hx(h1, 0.170, 0.24),
        "overlay":  hx(h1, 0.300, 0.16),
        # text
        "text":     hx(h1, 0.930, 0.40),
        "subtext":  hx(h1, 0.700, 0.18),
        # accents (same lightness as the old rice so the panel / OSD look the same)
        "accent":   hx(h1, 0.780, 0.72),
        "accent2":  hx(h2, 0.720, 0.72),
        "accent3":  hx(h1, 0.880, 0.80),
        # semantic colours stay fixed so "red" always means red
        "red":      "ff7d96",
        "green":    "8fe3a8",
        "yellow":   "f5d58a",
        "black":    "000000",
    }


def rgb(hexs):
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def hue_of_hex(hexs):
    r, g, b = (c / 255 for c in rgb(hexs))
    return colorsys.rgb_to_hls(r, g, b)[0]


# ------------------------------------------------------------------ templates
_PH = re.compile(r"\{\{\s*(#?)(\w+)(?::([0-9a-fA-F]{2}))?\s*\}\}")
_RGBA = re.compile(r"\{\{\s*rgba\(\s*(\w+)\s*,\s*([0-9.]+)\s*\)\s*\}\}")


def render(text, pal, extra):
    def rgba(m):
        c = pal.get(m.group(1))
        return "rgba(%d, %d, %d, %s)" % (*rgb(c), m.group(2)) if c else m.group(0)

    def ph(m):
        hashmark, name, alpha = m.groups()
        if name in extra:
            return extra[name]
        c = pal.get(name)
        if c is None:
            return m.group(0)
        return hashmark + c + (alpha or "")

    return _PH.sub(ph, _RGBA.sub(rgba, text))


def write_atomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def lock_background(img):
    """hyprlock cannot read webp/avif; fall back to a live screenshot for those."""
    return img if img.lower().endswith((".png", ".jpg", ".jpeg")) else "screenshot"


def apply_all(pal, img):
    os.makedirs(GEN, exist_ok=True)
    extra = {"wallpaper": img, "lockbg": lock_background(img), "home": HOME}
    for tpl, dests in OUTPUTS:
        p = os.path.join(TPL, tpl)
        if not os.path.isfile(p):
            print("template missing, skipped:", tpl)
            continue
        out = render(open(p, encoding="utf-8").read(), pal, extra)
        for d in dests:
            write_atomic(os.path.join(RICE, d), out)
    # generated/ is read by the Lua config, the panel, the OSD and the media card
    write_atomic(os.path.join(GEN, "colors.json"), json.dumps(dict(pal, wallpaper=img)))
    write_atomic(os.path.join(GEN, "palette.json"), json.dumps(pal, indent=1))
    lua = "return {\n" + "".join('  %s = "%s",\n' % (k, v) for k, v in sorted(pal.items())) + "}\n"
    write_atomic(os.path.join(GEN, "colors.lua"), lua)
    write_atomic(os.path.join(GEN, "current-wallpaper"), img + "\n")


def reload_everything():
    for cmd in (["pkill", "-SIGUSR2", "-x", "waybar"],
                ["makoctl", "reload"],
                ["pkill", "-SIGUSR1", "-x", "kitty"],          # kitty re-reads its config on SIGUSR1
                ["hyprctl", "reload"]):
        if shutil.which(cmd[0]):
            sp.run(cmd, stdout=sp.DEVNULL, stderr=sp.DEVNULL)


# ------------------------------------------------------------------ main
def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def find_default_wallpaper():
    for d in (os.path.join(HOME, "Pictures", "Wallpapers"), os.path.join(RICE, "wallpapers")):
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    return os.path.join(d, f)
    return ""


def opt(flags, name):
    return flags[flags.index(name) + 1] if name in flags and flags.index(name) + 1 < len(flags) else None


def main():
    argv = sys.argv[1:]
    flags = [a for a in argv]
    positional = []
    skip = False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        if a in ("--accent", "--accent2"):
            skip = True
            continue
        if not a.startswith("--"):
            positional.append(a)
    if not positional and "--reapply" not in flags:
        print(__doc__)
        return 1

    prev = load_json(os.path.join(GEN, "palette.json")) or load_json(os.path.join(GEN, "colors.json")) or {}
    img = ""
    if positional:
        img = os.path.abspath(os.path.expanduser(positional[0]))
        if not os.path.isfile(img):
            print("no such file:", img)
            return 1
    else:
        img = (open(os.path.join(GEN, "current-wallpaper")).read().strip()
               if os.path.isfile(os.path.join(GEN, "current-wallpaper")) else prev.get("wallpaper", ""))
        if not img or not os.path.isfile(img):
            img = find_default_wallpaper()

    a1, a2 = opt(flags, "--accent"), opt(flags, "--accent2")
    if a1:
        a1 = a1.lstrip("#").lower()
        h1 = hue_of_hex(a1)
        h2 = hue_of_hex(a2.lstrip("#")) if a2 else (h1 + 0.09) % 1.0
        pal = build_palette(h1, h2)
        pal["accent"] = a1
        if a2:
            pal["accent2"] = a2.lstrip("#").lower()
    elif positional:
        hues = pick_hues(pixels(img))
        if hues:
            pal = build_palette(*hues)
        elif "accent" in prev and "glass" in prev:
            pal = {k: v for k, v in prev.items() if k != "wallpaper"}
            print("image is (nearly) grey or unreadable; keeping the current colours")
        else:
            pal = build_palette(DEFAULT_H1, DEFAULT_H2)
    else:                                              # --reapply
        if "accent" in prev and "glass" in prev:
            pal = {k: v for k, v in prev.items() if k != "wallpaper"}
        else:
            hues = pick_hues(pixels(img)) if img else None
            pal = build_palette(*(hues or (DEFAULT_H1, DEFAULT_H2)))

    apply_all(pal, img)
    print("accent #%s  accent2 #%s" % (pal["accent"], pal["accent2"]))
    if "--no-reload" not in flags:
        reload_everything()
    return 0


if __name__ == "__main__":
    sys.exit(main())
