#!/usr/bin/env python3
"""Waybar auto-hide for Hyprland (main bar hides, the clock pill stays).

Rules:
  - empty workspace            -> main bar visible
  - app open on the workspace  -> main bar hidden (clock pill stays)
  - workspace switch / peek    -> main bar shown for PEEK seconds
  - pointer in the top strip   -> main bar shown until the pointer leaves
  - fullscreen app             -> the clock pill hides too, and returns afterwards

Commands:  autohide.py            run the watcher (also keeps the clock pill alive)
           autohide.py peek       show the bar briefly
           autohide.py off | on   stop / start the watcher (bar is restored on stop)
"""
import atexit, glob, json, os, select, signal, socket, subprocess, sys, time

PEEK = 1.5
HOVER_ENTER_Y = 45   # the reserved pill strip: pointing anywhere in it opens the bar
HOVER_LEAVE_Y = 80
LEAVE_DELAY = 0.7
POLL = 0.12
SCAN_EVERY = 2.0

HOME = os.path.expanduser("~")
PILL_CFG = f"{HOME}/.config/hypr-rice/waybar-pill/config.jsonc"
PILL_CSS = f"{HOME}/.config/hypr-rice/waybar-pill/style.css"
RUNTIME = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
PIDFILE = f"{RUNTIME}/autohide.pid"


def hypr_base():
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if sig:
        return f"{RUNTIME}/hypr/{sig}"
    dirs = sorted(glob.glob(f"{RUNTIME}/hypr/*/"), key=os.path.getmtime)
    return dirs[-1].rstrip("/") if dirs else None


BASE = hypr_base()


def hypr(cmd):
    try:
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(1)
        s.connect(BASE + "/.socket.sock")
        s.sendall(cmd.encode())
        buf = b""
        while True:
            d = s.recv(65536)
            if not d:
                break
            buf += d
        s.close()
        return json.loads(buf)
    except Exception:
        return None


def ws_state():
    """(windows on the active workspace, has a fullscreen window) or None."""
    a = hypr("j/activeworkspace")
    if not isinstance(a, dict):
        return None
    return a.get("windows", 0), bool(a.get("hasfullscreen"))


def layer_pids():
    layers = hypr("j/layers")
    if not isinstance(layers, dict):
        return None
    found = set()
    for mon in layers.values():
        for level in mon.get("levels", {}).values():
            for layer in level:
                if layer.get("namespace") == "waybar":
                    found.add(layer.get("pid"))
    return found


class Bar:
    """One Waybar process we show/hide with SIGUSR1 (which only flips its state)."""

    def __init__(self):
        self.pid, self.own, self.detect, self.last = None, True, None, 0.0

    def set_pid(self, pid):
        if pid and pid != self.pid:
            self.pid, self.own = pid, True  # a fresh Waybar always starts visible

    def apply(self, want, pids):
        pid = self.pid
        if not pid or pids is None or not os.path.exists(f"/proc/{pid}"):
            return
        present = pid in pids
        actual = present if self.detect else self.own
        if want == actual or time.monotonic() - self.last < 0.3:
            return
        try:
            os.kill(pid, signal.SIGUSR1)
        except OSError:
            return
        self.last = time.monotonic()
        if self.detect is None:
            time.sleep(0.4)
            now_pids = layer_pids() or set()
            self.detect = (pid in now_pids) != present
        self.own = want


def scan():
    """(main waybar pid, pill waybar pid) from /proc; zombies are skipped."""
    main = pill = None
    for d in glob.glob("/proc/[0-9]*"):
        try:
            args = open(d + "/cmdline", "rb").read().split(b"\0")
        except OSError:
            continue
        if not args or os.path.basename(args[0].decode(errors="ignore")) != "waybar":
            continue
        pid = int(d.rsplit("/", 1)[1])
        if b"waybar-pill" in b" ".join(args):
            pill = pill or pid
        else:
            main = main or pid
    return main, pill


def spawn_pill():
    if not os.path.exists(PILL_CFG):
        return
    try:
        subprocess.Popen(["waybar", "-c", PILL_CFG, "-s", PILL_CSS],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def read_pid():
    try:
        pid = int(open(PIDFILE).read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd in ("peek", "off"):
        pid = read_pid()
        if pid:
            os.kill(pid, signal.SIGUSR2 if cmd == "peek" else signal.SIGTERM)
        return
    if cmd == "on":
        if not read_pid():
            subprocess.Popen([sys.executable, os.path.abspath(__file__)],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        return
    if not BASE:
        sys.exit("Hyprland is not running")
    if read_pid():
        sys.exit("autohide is already running")
    open(PIDFILE, "w").write(str(os.getpid()))
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)  # no zombies from the pill

    main_bar, pill_bar = Bar(), Bar()
    last_scan = [0.0]

    def refresh():
        m, p = scan()
        if p is None:
            spawn_pill()
        main_bar.set_pid(m)
        pill_bar.set_pid(p)
        last_scan[0] = time.monotonic()

    def restore():
        pids = layer_pids()
        main_bar.apply(True, pids)
        pill_bar.apply(True, pids)
        try:
            os.remove(PIDFILE)
        except OSError:
            pass

    atexit.register(restore)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    rfd, wfd = os.pipe()
    os.set_blocking(wfd, False)

    def poke(*_):
        try:
            os.write(wfd, b"p")
        except OSError:
            pass

    signal.signal(signal.SIGUSR2, poke)

    ev = socket.socket(socket.AF_UNIX)
    ev.connect(BASE + "/.socket2.sock")

    refresh()
    wins, fs = ws_state() or (0, False)
    peek_until = 0.0
    hover = False
    leave_at = None
    buf = b""
    watch = {"openwindow", "closewindow", "movewindow", "movewindowv2",
             "workspace", "workspacev2", "focusedmon", "fullscreen"}
    switch = {"workspace", "workspacev2", "focusedmon"}

    while True:
        now = time.monotonic()
        if now - last_scan[0] > SCAN_EVERY:
            refresh()

        if wins > 0:
            c = hypr("j/cursorpos")
            if isinstance(c, dict):
                y = c.get("y", 999)
                if y <= HOVER_ENTER_Y and not fs:
                    hover, leave_at = True, None
                elif hover and y > HOVER_LEAVE_Y:
                    if leave_at is None:
                        leave_at = now + LEAVE_DELAY
                    elif now >= leave_at:
                        hover, leave_at = False, None
                elif hover:
                    leave_at = None
        else:
            hover, leave_at = False, None

        pids = layer_pids()
        main_bar.apply(wins == 0 or now < peek_until or hover, pids)
        pill_bar.apply(not fs, pids)

        ready, _, _ = select.select([ev, rfd], [], [], POLL if wins > 0 else SCAN_EVERY)
        now = time.monotonic()

        if rfd in ready:
            os.read(rfd, 64)
            peek_until = now + PEEK

        if ev in ready:
            data = ev.recv(65536)
            if not data:
                sys.exit(1)
            buf += data
            *lines, buf = buf.split(b"\n")
            changed = False
            for line in lines:
                name = line.split(b">>", 1)[0].decode(errors="ignore")
                if name in watch:
                    changed = True
                if name in switch:
                    peek_until = now + PEEK
            if changed:
                n = ws_state()
                if n is not None:
                    wins, fs = n


if __name__ == "__main__":
    main()
