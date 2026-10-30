#!/usr/bin/env python3
"""wallcolors: pick accent colours from a wallpaper and apply them everywhere.

usage: wallcolors.py IMAGE [--persist] [--no-reload]
  --persist    also write IMAGE into hyprpaper.conf and hyprlock.conf (survives reboot)
  --no-reload  write files only, do not poke waybar / mako / hyprland

Writes   generated/colors.json, generated/colors.lua, waybar/colors.css
Swaps the previous accent for the new one (same hex / rgba value) in:
         mako/config, rofi/catppuccin.rasi, hyprlock.conf
Needs Pillow (python-pillow) or ImageMagick. If neither works it changes nothing.
"""
import colorsys
import json
import math
import os
import re
import shutil
import subprocess as sp
import sys

RICE = os.path.expanduser("~/.config/hypr-rice")
GEN = os.path.join(RICE, "generated")
MOCHA = ("cba6f7", "89b4fa")             # stock rice accents (mauve, blue)


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


def pick(px):
    """Return (accent, accent2) hex strings tuned for a dark UI, or None."""
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
    if total < 5:                                      # basically grey: keep current colours
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

    def hexc(h, l):
        r, g, b = colorsys.hls_to_rgb(h, l, 0.72)
        return "%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))

    return hexc(h1, 0.78), hexc(h2, 0.72)


def rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))


def swap_in_file(path, old, new):
    """Replace the previous accent (hex or rgba) with the new one, in place."""
    if not os.path.isfile(path) or old == new:
        return
    t = open(path, encoding="utf-8").read()
    o, n = rgb(old), rgb(new)
    t2 = re.sub("#" + old, "#" + new, t, flags=re.I)
    t2 = re.sub(r"rgba?\(\s*%d\s*,\s*%d\s*,\s*%d\s*," % o, "rgba(%d, %d, %d," % n, t2)
    if t2 != t:
        open(path, "w", encoding="utf-8").write(t2)


def persist(img):
    """Remember the wallpaper for the next login and the lock screen."""
    for name, exts in (("hyprpaper.conf", None), ("hyprlock.conf", (".png", ".jpg", ".jpeg"))):
        p = os.path.join(RICE, name)
        if not os.path.isfile(p) or (exts and not img.lower().endswith(exts)):
            continue
        lines = open(p, encoding="utf-8").read().split("\n")
        in_bg = name == "hyprpaper.conf"
        done = False
        for i, l in enumerate(lines):
            if name == "hyprlock.conf" and re.match(r"\s*background\s*\{", l):
                in_bg = True
            elif in_bg and not done and re.match(r"\s*path\s*=", l):
                lines[i] = re.sub(r"=.*", "= " + img, l)
                done = True
            elif name == "hyprlock.conf" and in_bg and l.strip() == "}":
                in_bg = False
        if done:
            open(p, "w", encoding="utf-8").write("\n".join(lines))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__)
        return 1
    img = os.path.abspath(os.path.expanduser(args[0]))
    if not os.path.isfile(img):
        print("no such file:", img)
        return 1
    os.makedirs(GEN, exist_ok=True)
    if "--persist" in flags:
        persist(img)
    cols = pick(pixels(img))
    if not cols:
        print("could not read colours (needs python-pillow or imagemagick, or the image is grey); colours left as they were")
        return 0
    a1, a2 = cols
    jp = os.path.join(GEN, "colors.json")
    try:
        old = json.load(open(jp))
        o1, o2 = old["accent"], old["accent2"]
    except Exception:
        o1, o2 = MOCHA
    json.dump({"accent": a1, "accent2": a2, "wallpaper": img}, open(jp, "w"))
    open(os.path.join(GEN, "colors.lua"), "w").write('return { accent = "%s", accent2 = "%s" }\n' % (a1, a2))
    wb = os.path.join(RICE, "waybar")
    if os.path.isdir(wb):
        open(os.path.join(wb, "colors.css"), "w").write(
            "/* written by wallcolors.py: follows the wallpaper */\n"
            "@define-color accent  #%s;\n@define-color accent2 #%s;\n" % (a1, a2))
    for rel in ("mako/config", "rofi/catppuccin.rasi", "hyprlock.conf"):
        swap_in_file(os.path.join(RICE, rel), o1, a1)
        swap_in_file(os.path.join(RICE, rel), o2, a2)
    print("accent #%s  accent2 #%s" % (a1, a2))
    if "--no-reload" not in flags:
        for cmd in (["pkill", "-SIGUSR2", "waybar"], ["makoctl", "reload"], ["hyprctl", "reload"]):
            if shutil.which(cmd[0]):
                sp.run(cmd, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
