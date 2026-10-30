#!/usr/bin/env python3
"""Turn fingerprint unlock on or off in the rice's hyprlock.conf (password always keeps working).

usage: fingerprint-lock.py on|off [--rice ~/.config/hypr-rice]
"""
import json
import os
import re
import sys

BEGIN = "# HYPR_RICE_FINGERPRINT_BEGIN"
END = "# HYPR_RICE_FINGERPRINT_END"


def accent(rice):
    try:
        h = json.load(open(os.path.join(rice, "generated", "colors.json")))["accent"]
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return (203, 166, 247)


def block(rice):
    r, g, b = accent(rice)
    scripts = "$HOME/.config/hypr-rice/scripts"
    return f"""{BEGIN}
auth {{
    fingerprint {{
        enabled = true
        ready_message = Touch the sensor
        present_message = Reading your finger...
        retry_delay = 250
    }}
}}

label {{
    monitor =
    text = cmd[update:600000] {scripts}/lock-quip.sh
    color = rgba(166, 173, 200, 1.0)
    font_size = 15
    font_family = JetBrainsMono Nerd Font
    position = 0, 30
    halign = center
    valign = center
}}

label {{
    monitor =
    text = \U000f0237  touch the sensor to unlock
    color = rgba({r}, {g}, {b}, 0.9)
    font_size = 14
    font_family = JetBrainsMono Nerd Font
    position = 0, -108
    halign = center
    valign = center
}}
{END}
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rice = os.path.expanduser("~/.config/hypr-rice")
    if "--rice" in sys.argv:
        rice = os.path.expanduser(sys.argv[sys.argv.index("--rice") + 1])
        args = [a for a in args if a != rice and a != sys.argv[sys.argv.index("--rice") + 1]]
    if not args or args[0] not in ("on", "off"):
        print(__doc__)
        return 1
    path = os.path.join(rice, "hyprlock.conf")
    if not os.path.isfile(path):
        print("hyprlock.conf not found:", path)
        return 1
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"\n*%s.*?%s\n?" % (re.escape(BEGIN), re.escape(END)), "\n", t, flags=re.S)   # drop old block
    t = t.replace("Password  ·  or touch the sensor</span>", "Password</span>")
    if args[0] == "on":
        t = t.replace("Password</span>", "Password  ·  or touch the sensor</span>", 1)
        t = t.rstrip("\n") + "\n\n" + block(rice)
    else:
        t = t.rstrip("\n") + "\n"
    open(path, "w", encoding="utf-8").write(t)
    print("fingerprint unlock on the lock screen:", args[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
