#!/usr/bin/env python3
"""Themes the app launcher (rofi AND wofi, whichever you have) to match the rice: dark matte card (about 88% opaque),
a 2px accent frame, rounded search pill, accent-gradient highlight, same font as the bar, wallpaper accent colours.
   launcher_theme.py            install      launcher_theme.py --refresh   re-read the wallpaper colours (rofi)
   launcher_theme.py --undo     restore      launcher_theme.py --opacity 0.88   --dir P (rice folder)"""
import glob, json, os, re, shutil, sys, time

home = os.path.expanduser("~")
rice = os.path.join(home, ".config", "hypr-rice")
args = sys.argv[1:]
opacity = float(args[args.index("--opacity") + 1]) if "--opacity" in args else 0.88
if "--dir" in args:
    rice = args[args.index("--dir") + 1]
COLORS_CSS = os.path.join(rice, "waybar", "colors.css")
WOFI = os.path.join(home, ".config", "wofi")
ROFI = os.path.join(home, ".config", "rofi")
FONT = "JetBrainsMono Nerd Font"
DEFAULT = dict(base="#1e1e2e", text="#cdd6f4", subtext="#a6adc8", accent="#cba6f7", accent2="#89b4fa")


def colors():
    c = dict(DEFAULT)
    try:
        for m in re.finditer(r"@define-color\s+(\w+)\s+(#[0-9a-fA-F]{6})", open(COLORS_CSS, encoding="utf-8").read()):
            if m.group(1) in c:
                c[m.group(1)] = m.group(2)
    except OSError:
        pass
    return c


def rgba(hexc, a):
    return "%s%02x" % (hexc, round(max(0.0, min(1.0, a)) * 255))


def wofi_css():
    d = DEFAULT
    return f'''/* hypr-rice launcher theme (wofi). Colours follow the wallpaper through waybar/colors.css. */
@define-color base {d["base"]}; @define-color text {d["text"]}; @define-color subtext {d["subtext"]};
@define-color accent {d["accent"]}; @define-color accent2 {d["accent2"]};
@import url("{COLORS_CSS}");

* {{ font-family: "{FONT}", "Noto Sans", sans-serif; font-size: 14px; font-weight: 600; }}
window {{ background-color: transparent; }}
#outer-box {{ margin: 0; padding: 14px; background-color: alpha(@base, {opacity}); border: 2px solid alpha(@accent, 0.55);
             border-radius: 26px; }}
#input {{ margin: 0 0 10px 0; padding: 10px 16px; min-height: 22px; border-radius: 18px; border: 1px solid alpha(@text, 0.14);
         background-image: none; background-color: alpha(@text, 0.07); color: @text; box-shadow: none; }}
#input:focus {{ border-color: alpha(@accent, 0.75); }}
#scroll, #inner-box {{ background-color: transparent; margin: 0; padding: 0; }}
#entry {{ padding: 8px 12px; margin: 2px 0; border-radius: 16px; border: 1px solid transparent; }}
#entry:selected {{ background-image: linear-gradient(to right, alpha(@accent, 0.38), alpha(@accent2, 0.20));
                  border: 1px solid alpha(@accent, 0.60); }}
#img {{ margin-right: 12px; }}
#text {{ color: @text; }}
#text:selected {{ color: @text; }}
'''


WOFI_CONF = '''show=drun
prompt=Search apps
width=560
height=430
location=center
allow_images=true
image_size=28
hide_scroll=true
no_actions=true
insensitive=true
gtk_dark=true
'''


def rofi_rasi():
    c = colors()
    bg, fg, ac, ac2, sub = c["base"], c["text"], c["accent"], c["accent2"], c["subtext"]
    return f'''/* hypr-rice launcher theme (rofi). Regenerate after a wallpaper change: python3 ~/.config/hypr-rice/scripts/launcher_theme.py --refresh */
* {{ font: "{FONT} 12"; background-color: transparent; text-color: {fg}; }}
configuration {{ modi: "drun"; show-icons: true; drun-display-format: "{{name}}"; }}
window {{ location: center; anchor: center; width: 560px; padding: 14px; background-color: {rgba(bg, opacity)};
         border: 2px; border-color: {rgba(ac, 0.55)}; border-radius: 26px; }}
mainbox {{ children: [ inputbar, listview ]; spacing: 10px; }}
inputbar {{ children: [ entry ]; padding: 10px 16px; border: 1px; border-color: {rgba(fg, 0.14)}; border-radius: 18px;
           background-color: {rgba(fg, 0.07)}; }}
entry {{ placeholder: "Search apps"; placeholder-color: {rgba(sub, 1.0)}; text-color: {fg}; }}
listview {{ lines: 7; columns: 1; scrollbar: false; spacing: 2px; fixed-height: false; }}
element {{ padding: 8px 12px; spacing: 12px; border: 1px; border-color: transparent; border-radius: 16px; }}
element selected.normal {{ background-color: {rgba(ac, 0.34)}; border-color: {rgba(ac, 0.60)}; }}
element-icon {{ size: 28px; }}
element-text {{ vertical-align: 0.5; text-color: inherit; }}
'''.replace("{fg}", fg)


def newest(prefix):
    b = sorted(glob.glob(os.path.join(home, prefix + "*")))
    return b[-1] if b else None


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def rofi_theme_line():
    p = os.path.join(ROFI, "config.rasi")
    s = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    if '@theme "rice"' not in s:
        s = re.sub(r'(?m)^\s*@theme\s+.*\n', "", s)
        write(p, '@theme "rice"\n' + s)


if "--refresh" in args:
    write(os.path.join(ROFI, "rice.rasi"), rofi_rasi())
    print("rofi theme refreshed from the current wallpaper colours")
    sys.exit(0)

if "--undo" in args:
    b = newest("hypr-rice-launcher-backup-")
    if not b:
        sys.exit("No backup found.")
    man = json.load(open(os.path.join(b, "manifest.json")))
    for rel, existed in man.items():
        dst = os.path.join(home, ".config", rel)
        if existed:
            shutil.copy2(os.path.join(b, rel), dst)
        elif os.path.exists(dst):
            os.remove(dst)
    print("Restored from", b)
    sys.exit(0)

bk = os.path.join(home, "hypr-rice-launcher-backup-" + time.strftime("%Y%m%d-%H%M%S"))
files = {"wofi/style.css": wofi_css(), "wofi/config": WOFI_CONF, "rofi/rice.rasi": rofi_rasi()}
man = {}
for rel in list(files) + ["rofi/config.rasi"]:
    src = os.path.join(home, ".config", rel)
    man[rel] = os.path.exists(src)
    if man[rel]:
        os.makedirs(os.path.dirname(os.path.join(bk, rel)), exist_ok=True)
        shutil.copy2(src, os.path.join(bk, rel))
os.makedirs(bk, exist_ok=True)
json.dump(man, open(os.path.join(bk, "manifest.json"), "w"))
for rel, text in files.items():
    write(os.path.join(home, ".config", rel), text)
rofi_theme_line()
dst = os.path.join(rice, "scripts", "launcher_theme.py")
if os.path.isdir(os.path.dirname(dst)) and os.path.abspath(__file__) != os.path.abspath(dst):
    shutil.copy2(__file__, dst)
print("Themed wofi and rofi. Backup in", bk)
print("Press SUPER + SPACE to try it. Undo: ./install.sh --undo")
