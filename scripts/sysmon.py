#!/usr/bin/env python3
"""sysmon: a small system monitor popup for the rice.

Shows CPU (total + per core), RAM, swap, storage + SSD I/O, GPU, and the top
CPU / memory processes, with a confirm-before-kill option.

- Pure Python 3 standard library, reads /proc and /sys directly.
- Only samples while it is open (every 2 s), so it costs nothing when closed.

Keys:  up/down or j/k  select      Tab / left / right  sort by CPU or memory
       x  terminate (SIGTERM)      X  force kill (SIGKILL)   (both ask first)
       g  group by name on/off     space  pause              q / Esc  quit
Touch / mouse: tap a process to select it, tap CPU / Memory to sort.
Debug: sysmon.py --dump 64x24      print one frame as plain text
"""
import curses
import glob
import locale
import os
import re
import shutil
import signal
import subprocess
import sys
import time

CLK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")
REFRESH = 2.0
PROTECTED = {"Hyprland", "hyprland", "systemd", "init"}
GENERIC = {"python", "python3", "node", "java", "bash", "sh", "zsh", "perl", "ruby"}
FS_OK = {"ext4", "ext3", "xfs", "btrfs", "f2fs", "ntfs3", "ntfs", "exfat", "vfat", "zfs"}

# Catppuccin Mocha: (256-color approximation for curses, true hex for dumps)
PALETTE = {
    "text":   (189, "#cdd6f4"), "sub":    (146, "#a6adc8"), "dim":   (60,  "#6c7086"),
    "mauve":  (183, "#cba6f7"), "blue":   (111, "#89b4fa"), "green": (151, "#a6e3a1"),
    "yellow": (223, "#f9e2af"), "red":    (211, "#f38ba8"), "teal":  (116, "#94e2d5"),
    "pink":   (218, "#f5c2e7"), "sel":    (189, "#cdd6f4"),
}


def _hex_to_256(hx):
    r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    lv = (0, 95, 135, 175, 215, 255)
    q = lambda c: min(range(6), key=lambda i: abs(lv[i] - c))
    return 16 + 36 * q(r) + 6 * q(g) + q(b)


def _load_accents():
    try:
        import json
        c = json.load(open(os.path.expanduser("~/.config/hypr-rice/generated/colors.json")))
        PALETTE["mauve"] = (_hex_to_256(c["accent"]), "#" + c["accent"])
        PALETTE["blue"] = (_hex_to_256(c["accent2"]), "#" + c["accent2"])
    except Exception:
        pass


_load_accents()


# --------------------------------------------------------------------- helpers
def read(path):
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def num(path):
    try:
        return float(read(path).strip())
    except ValueError:
        return None


def fit(s, n):
    if n <= 0:
        return ""
    return s if len(s) <= n else s[: max(0, n - 1)] + "…"


def fmt_cap(b):
    return f"{b / 2**40:.1f}T" if b >= 2**40 else f"{b / 2**30:.0f}G"


def fmt_mem(b):
    return f"{b / 2**30:.2f} GiB" if b >= 2**30 else f"{b / 2**20:.0f} MiB"


def fmt_rate(b):
    return f"{b / 2**20:.1f} MB/s"


def fmt_up(sec):
    d, r = divmod(int(sec), 86400)
    h, r = divmod(r, 3600)
    return (f"{d}d " if d else "") + f"{h}h {r // 60}m"


def load_color(p):
    return "green" if p < 60 else "yellow" if p < 85 else "red"


# -------------------------------------------------------------------- sampling
def read_cpu_times():
    out = {}
    for line in read("/proc/stat").splitlines():
        if line.startswith("cpu"):
            p = line.split()
            v = list(map(int, p[1:9]))
            out[p[0]] = (v[3] + v[4], sum(v))  # idle+iowait, total
    return out


def read_procs():
    res = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as f:
                s = f.read()
        except OSError:
            continue
        rp = s.rfind(")")
        comm = s[s.find("(") + 1: rp]
        rest = s[rp + 2:].split()
        try:
            ticks = int(rest[11]) + int(rest[12])      # utime + stime
            rss = int(rest[21]) * PAGE
        except (IndexError, ValueError):
            continue
        if rss > 0:                                    # skips kernel threads
            res[int(d)] = (comm, ticks, rss)
    return res


def read_diskio():
    out = {}
    for line in read("/proc/diskstats").splitlines():
        p = line.split()
        if len(p) > 9 and re.match(r"^(nvme\d+n\d+|sd[a-z]+|vd[a-z]+|mmcblk\d+)$", p[2]):
            out[p[2]] = (int(p[5]) * 512, int(p[9]) * 512)
    return out


def read_mounts():
    seen, out = set(), []
    for line in read("/proc/mounts").splitlines():
        p = line.split()
        if len(p) < 3 or not p[0].startswith("/dev/") or p[2] not in FS_OK:
            continue
        mp = p[1].replace("\\040", " ")
        if p[0] in seen or "/snap/" in mp:
            continue
        seen.add(p[0])
        try:
            st = os.statvfs(mp)
        except OSError:
            continue
        total = st.f_blocks * st.f_frsize
        if total > 0:
            out.append((mp, total - st.f_bfree * st.f_frsize, total))
    out.sort(key=lambda m: (m[0] != "/", len(m[0])))
    return out[:3]


def cpu_temp():
    for want in ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz"):
        for hw in glob.glob("/sys/class/hwmon/hwmon*"):
            if read(hw + "/name").strip() != want:
                continue
            best = None
            for inp in sorted(glob.glob(hw + "/temp*_input")):
                label = read(inp.replace("_input", "_label")).strip()
                v = num(inp)
                if v is None:
                    continue
                if re.search(r"Package|Tctl|Tdie", label):
                    return v / 1000
                best = best if best is not None else v
            if best is not None:
                return best / 1000
    return None


def cpu_freq_ghz():
    vals = [num(f) for f in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq")]
    vals = [v for v in vals if v]
    if vals:
        return sum(vals) / len(vals) / 1e6
    mh = [float(l.split(":")[1]) for l in read("/proc/cpuinfo").splitlines() if l.startswith("cpu MHz")]
    return sum(mh) / len(mh) / 1000 if mh else None


def meminfo():
    d = {}
    for line in read("/proc/meminfo").splitlines():
        k, _, v = line.partition(":")
        try:
            d[k] = int(v.split()[0]) * 1024
        except (IndexError, ValueError):
            pass
    return d


def read_gpus():
    gpus = []
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2).stdout
            for line in out.strip().splitlines():
                n, u, mu, mt, t = [x.strip() for x in line.split(",")]
                gpus.append(dict(name=n, util=float(u), vram_used=float(mu) * 2**20,
                                 vram_total=float(mt) * 2**20, temp=float(t), note=""))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    for card in sorted(glob.glob("/sys/class/drm/card[0-9]*")):
        if not re.search(r"card\d+$", card):
            continue
        dev = card + "/device"
        vendor = read(dev + "/vendor").strip()
        if vendor == "0x1002":                                      # AMD
            util = num(dev + "/gpu_busy_percent")
            temps = glob.glob(dev + "/hwmon/hwmon*/temp1_input")
            gpus.append(dict(
                name=read(dev + "/product_name").strip() or "AMD GPU",
                util=util, vram_used=num(dev + "/mem_info_vram_used"),
                vram_total=num(dev + "/mem_info_vram_total"),
                temp=(num(temps[0]) / 1000) if temps and num(temps[0]) else None, note=""))
        elif vendor == "0x8086":                                    # Intel iGPU
            cur = num(card + "/gt_cur_freq_mhz") or num(card + "/gt/gt0/rps_cur_freq_mhz")
            mx = num(card + "/gt_max_freq_mhz") or num(card + "/gt/gt0/rps_max_freq_mhz")
            note = f"{cur:.0f}/{mx:.0f} MHz" if cur and mx else "no usage counter (needs root)"
            gpus.append(dict(name="Intel integrated GPU", util=None, vram_used=None,
                             vram_total=None, temp=None, note=note))
    return gpus


class Sampler:
    def __init__(self):
        self.t = self.cpu = self.procs = self.disk = None
        self.model = "CPU"
        for l in read("/proc/cpuinfo").splitlines():
            if l.startswith("model name"):
                self.model = l.split(":", 1)[1].strip()
                break

    def sample(self):
        now = time.monotonic()
        dt = (now - self.t) if self.t else None
        cpu, procs, disk = read_cpu_times(), read_procs(), read_diskio()
        d = dict(model=self.model, total=0.0, cores=[], procs=[], io=[])
        if self.cpu:
            for name, (idle, total) in cpu.items():
                pi, pt = self.cpu.get(name, (idle, total))
                dtot = total - pt
                pct = 100.0 * (1 - (idle - pi) / dtot) if dtot > 0 else 0.0
                if name == "cpu":
                    d["total"] = pct
                else:
                    d["cores"].append((int(name[3:]), pct))
            d["cores"] = [p for _, p in sorted(d["cores"])]
        else:
            d["cores"] = [0.0] * (os.cpu_count() or 1)
        for pid, (comm, ticks, rss) in procs.items():
            pct = 0.0
            if self.procs and dt and pid in self.procs:
                pct = max(0.0, (ticks - self.procs[pid][1]) / CLK / dt * 100)
            d["procs"].append(dict(pid=pid, name=comm, cpu=pct, rss=rss))
        for dev, (rd, wr) in sorted(disk.items()):
            prd, pwr = (self.disk or {}).get(dev, (rd, wr))
            rate = (lambda a, b: max(0, a - b) / dt) if dt else (lambda a, b: 0)
            base = f"/sys/block/{dev}"
            d["io"].append(dict(
                dev=dev, model=read(base + "/device/model").strip(),
                kind="SSD" if read(base + "/queue/rotational").strip() == "0" else "HDD",
                rd=rate(rd, prd), wr=rate(wr, pwr)))
        mi = meminfo()
        d["mem"] = dict(total=mi.get("MemTotal", 0), avail=mi.get("MemAvailable", 0),
                        cache=mi.get("Cached", 0), buffers=mi.get("Buffers", 0),
                        swap_total=mi.get("SwapTotal", 0), swap_free=mi.get("SwapFree", 0),
                        zram="zram" in read("/proc/swaps"))
        d.update(mounts=read_mounts(), gpus=read_gpus(), temp=cpu_temp(), freq=cpu_freq_ghz(),
                 load=os.getloadavg(), uptime=float(read("/proc/uptime").split()[0] or 0),
                 threads=os.cpu_count() or 1)
        self.t, self.cpu, self.procs, self.disk = now, cpu, procs, disk
        return d


# --------------------------------------------------------------------- canvases
class CursesCanvas:
    def __init__(self, scr):
        self.scr, self.pairs = scr, {}
        curses.start_color()
        curses.use_default_colors()
        rich = curses.COLORS >= 256
        fallback = dict(text=7, sub=7, dim=7, mauve=5, blue=4, green=2, yellow=3, red=1, teal=6, pink=5)
        for i, (name, (c256, _)) in enumerate(PALETTE.items(), start=1):
            fg = c256 if rich else fallback.get(name, 7)
            bg = 237 if (name == "sel" and rich) else (-1 if name != "sel" else 0)
            curses.init_pair(i, fg, bg)
            self.pairs[name] = curses.color_pair(i)

    def size(self):
        return self.scr.getmaxyx()

    def text(self, y, x, s, color="text", bold=False):
        h, w = self.size()
        if y < 0 or y >= h or x >= w or x < 0:
            return
        s = s[: max(0, w - x - (1 if y == h - 1 else 0))]
        try:
            self.scr.addstr(y, x, s, self.pairs[color] | (curses.A_BOLD if bold else 0))
        except curses.error:
            pass

    def erase(self):
        self.scr.erase()

    def flush(self):
        self.scr.refresh()


class GridCanvas:
    """Off-screen canvas used by --dump and tests."""
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cells = [[(" ", "text", False)] * w for _ in range(h)]

    def size(self):
        return self.h, self.w

    def text(self, y, x, s, color="text", bold=False):
        if y < 0 or y >= self.h:
            return
        for i, ch in enumerate(s):
            if 0 <= x + i < self.w:
                self.cells[y][x + i] = (ch, color, bold)

    def plain(self):
        return "\n".join("".join(c[0] for c in row).rstrip() for row in self.cells)


# ------------------------------------------------------------------------- app
def bar(cv, y, x, w, frac, color=None):
    frac = max(0.0, min(1.0, frac))
    n = int(round(frac * w))
    cv.text(y, x, "━" * n, color or load_color(frac * 100))
    cv.text(y, x + n, "━" * (w - n), "dim")


SPARK = "▁▂▃▄▅▆▇█"


class App:
    def __init__(self):
        self.sampler = Sampler()
        self.data = None
        self.grouped = True
        self.paused = False
        self.panel = "cpu"
        self.sel = {"cpu": None, "mem": None}
        self.idx = {"cpu": 0, "mem": 0}
        self.view = {"cpu": [], "mem": []}
        self.confirm = None
        self.status = ("", 0.0, "sub")
        self.names = {}
        self.last_h = 0
        self.hits = {"tabs": [], "rows": []}

    def refresh(self):
        self.data = self.sampler.sample()

    # ---- process lists
    def entries(self):
        procs = self.data["procs"]
        if not self.grouped:
            return [dict(key=p["pid"], name=p["name"], pids=[p["pid"]], cpu=p["cpu"],
                         rss=p["rss"], n=1, pid=p["pid"]) for p in procs]
        g = {}
        for p in procs:
            e = g.setdefault(p["name"], dict(key=p["name"], name=p["name"], pids=[],
                                             cpu=0.0, rss=0, n=0, pid=p["pid"]))
            e["pids"].append(p["pid"])
            e["cpu"] += p["cpu"]
            e["rss"] += p["rss"]
            e["n"] += 1
        return list(g.values())

    def pretty(self, e):
        name = e["name"]
        if name not in GENERIC:
            return name
        pid = e["pid"]
        if pid not in self.names:
            args = read(f"/proc/{pid}/cmdline").split("\0")
            real = [a for a in args[1:] if a and not a.startswith("-")]
            self.names[pid] = os.path.basename(real[0]) if real else name
        return self.names[pid]

    # ---- drawing
    def row(self, cv, y, label, frac, right, w, color=None):
        """label  ━━━━━━╌╌╌╌  right-aligned text (fixed column so bars line up)"""
        rw = 22
        cv.text(y, 2, label, "mauve", True)
        bar(cv, y, 7, max(6, w - 2 - 5 - rw - 2), frac, color)
        cv.text(y, w - 2 - rw, right.rjust(rw), color or load_color(frac * 100))

    def draw(self, cv):
        h, w = cv.size()
        d = self.data
        self.hits = {"tabs": [], "rows": []}
        self.last_h = h
        if w < 60 or h < 22:
            cv.text(1, 2, f"Too small ({w}x{h}), need 60x22", "yellow")
            return

        cv.text(0, 2, "◆ System", "mauve", True)
        info = f"up {fmt_up(d['uptime'])}"
        if self.paused:
            info = "paused · " + info
        cv.text(0, w - 2 - len(info), info, "yellow" if self.paused else "sub")

        # CPU + per-core sparkline
        right = f"{d['total']:3.0f}%"
        if d["freq"]:
            right += f"  {d['freq']:.1f}GHz"
        if d["temp"] is not None:
            right += f"  {d['temp']:.0f}°C"
        self.row(cv, 2, "CPU", d["total"] / 100, right, w)
        x = 7
        for p in d["cores"]:
            lvl = min(7, int(p / 100 * 8))
            cv.text(3, x, SPARK[lvl], load_color(p))
            x += 2
        cv.text(3, x + 1, f"{d['threads']} threads", "dim")

        # RAM / swap
        m = d["mem"]
        used = m["total"] - m["avail"]
        pct = 100 * used / m["total"] if m["total"] else 0
        self.row(cv, 5, "RAM", pct / 100, f"{used / 2**30:.1f}/{m['total'] / 2**30:.1f}G {pct:3.0f}%", w, "blue" if pct < 85 else "red")
        y = 6
        if m["swap_total"]:
            su = m["swap_total"] - m["swap_free"]
            sp = 100 * su / m["swap_total"]
            self.row(cv, y, "SWP", sp / 100, f"{su / 2**30:.1f}/{m['swap_total'] / 2**30:.1f}G {sp:3.0f}%", w, "blue" if sp < 85 else "red")
            y += 1

        # GPU (first one only)
        if d["gpus"]:
            g = d["gpus"][0]
            if g["util"] is not None:
                right = f"{g['util']:3.0f}%"
                if g["vram_total"]:
                    right += f"  {g['vram_used'] / 2**30:.1f}/{g['vram_total'] / 2**30:.1f}G"
                if g["temp"] is not None:
                    right += f"  {g['temp']:.0f}°C"
                self.row(cv, y, "GPU", g["util"] / 100, right, w, "teal")
            else:
                cv.text(y, 2, "GPU", "mauve", True)
                cv.text(y, 7, fit(f"{g['name']}  {g['note']}", w - 9), "sub")
            y += 1

        # storage
        for mp, u, t in d["mounts"][:2]:
            sp = 100 * u / t
            self.row(cv, y, fit(mp, 4).ljust(4), sp / 100, f"{fmt_cap(u)}/{fmt_cap(t)} {sp:3.0f}%", w, "teal" if sp < 85 else "red")
            y += 1
        rd = sum(i["rd"] for i in d["io"])
        wr = sum(i["wr"] for i in d["io"])
        cv.text(y, 2, "I/O", "mauve", True)
        cv.text(y, 7, f"read {fmt_rate(rd)}    write {fmt_rate(wr)}", "sub")
        y += 2

        # process list: one panel, sorted by CPU or memory
        focus = self.panel
        cv.text(y, 2, "Processes", "text", True)
        x = 14
        for key, label in (("cpu", "CPU"), ("mem", "Memory")):
            on = focus == key
            txt = f" {label} "
            cv.text(y, x, txt, "sel" if on else "sub", on)
            self.hits["tabs"].append((y, x, x + len(txt), key))
            x += len(txt) + 1
        grp = "grouped" if self.grouped else "all processes"
        cv.text(y, w - 2 - len(grp), grp, "dim")
        y += 1
        nw = w - 4 - 6 - 8 - 11 - 3
        cv.text(y, 2, f"{'PID':>6}  {'NAME':<{nw}}{'CPU':>7} {'MEM':>10}", "dim")
        y += 1
        rows = max(3, h - y - 3)
        ents = self.entries()
        lists = {
            "cpu": sorted(ents, key=lambda e: -e["cpu"])[:rows],
            "mem": sorted(ents, key=lambda e: -e["rss"])[:rows],
        }
        self.view = lists
        for pn in lists:
            keys = [e["key"] for e in lists[pn]]
            k = self.sel[pn]
            idx = keys.index(k) if k in keys else min(self.idx[pn], max(0, len(keys) - 1))
            self.idx[pn] = idx
            self.sel[pn] = keys[idx] if keys else None
        for i, e in enumerate(lists[focus]):
            idstr = f"×{e['n']}" if e["n"] > 1 else str(e["pid"])
            line = f"{idstr:>6}  {fit(self.pretty(e), nw):<{nw}}{e['cpu']:>6.1f}% {fmt_mem(e['rss']):>10}"
            if i == self.idx[focus]:
                cv.text(y + i, 1, " " + line + " ", "sel", True)
            else:
                cv.text(y + i, 2, line[: 8 + nw], "text")
                cv.text(y + i, 2 + 8 + nw, line[8 + nw:], "sub")
            self.hits["rows"].append((y + i, i))

        # footer
        if self.confirm:
            e, sig = self.confirm
            what = f"{self.pretty(e)} ({e['n']} processes)" if e["n"] > 1 else f"{self.pretty(e)} (pid {e['pid']})"
            verb = "FORCE KILL" if sig == signal.SIGKILL else "End"
            cv.text(h - 2, 2, f"{verb} {what}?  y / tap here = yes, else cancel", "red", True)
        elif self.status[1] > time.monotonic():
            cv.text(h - 2, 2, self.status[0], self.status[2])
        cv.text(h - 1, 2, "↑↓ select · tab sort · x end · X kill · g group · ␣ pause", "dim")

    def click(self, y, x):
        if self.confirm:                       # tap the red prompt = yes, tap anywhere else = cancel
            e, sig = self.confirm
            self.confirm = None
            if y == getattr(self, "last_h", 0) - 2:
                self.kill(e, sig)
                self.refresh()
            else:
                self.say("Cancelled.")
            return
        for ty, x0, x1, key in self.hits.get("tabs", []):
            if y == ty and x0 <= x < x1:
                self.panel = key
                return
        for ry, i in self.hits.get("rows", []):
            if y == ry:
                lst = self.view[self.panel]
                if i < len(lst):
                    if self.idx[self.panel] == i and not self.confirm:   # second tap on same row = end it
                        self.confirm = (lst[i], signal.SIGTERM)
                    self.idx[self.panel] = i
                    self.sel[self.panel] = lst[i]["key"]
                return

    # ---- input
    def current(self):
        lst = self.view[self.panel]
        i = self.idx[self.panel]
        return lst[i] if lst and i < len(lst) else None

    def say(self, msg, color="sub"):
        self.status = (msg, time.monotonic() + 4, color)

    def kill(self, e, sig):
        name = self.pretty(e)
        if e["name"] in PROTECTED or name in PROTECTED or any(p in (1, os.getpid()) for p in e["pids"]):
            return self.say(f"Refusing to kill {name}: it would end your session or this monitor.", "yellow")
        ok = denied = 0
        for pid in e["pids"]:
            try:
                os.kill(pid, sig)
                ok += 1
            except PermissionError:
                denied += 1
            except ProcessLookupError:
                pass
        sname = signal.Signals(sig).name
        if denied and not ok:
            self.say(f"Not permitted: {name} belongs to another user.", "red")
        else:
            self.say(f"Sent {sname} to {name} ({ok} process{'es' if ok != 1 else ''})", "green")

    def key(self, k):
        if self.confirm:
            e, sig = self.confirm
            self.confirm = None
            if k in (ord("y"), ord("Y")):
                self.kill(e, sig)
                self.refresh()
            else:
                self.say("Cancelled.")
            return
        if k in (ord("q"), 27):
            return "quit"
        pn = self.panel
        if k in (curses.KEY_UP, ord("k")):
            self.idx[pn] = max(0, self.idx[pn] - 1)
        elif k in (curses.KEY_DOWN, ord("j")):
            self.idx[pn] = min(len(self.view[pn]) - 1, self.idx[pn] + 1)
        elif k in (curses.KEY_LEFT, curses.KEY_RIGHT, 9, ord("h"), ord("l")):
            self.panel = "mem" if pn == "cpu" else "cpu"
        elif k in (ord("x"), curses.KEY_DC, ord("X")):
            e = self.current()
            if e:
                self.confirm = (e, signal.SIGKILL if k == ord("X") else signal.SIGTERM)
        elif k == ord("g"):
            self.grouped = not self.grouped
        elif k == ord(" "):
            self.paused = not self.paused
        elif k == ord("r"):
            self.refresh()
        # keep selection key in sync with the moved index
        lst = self.view[self.panel]
        if lst:
            self.sel[self.panel] = lst[min(self.idx[self.panel], len(lst) - 1)]["key"]


def run(scr):
    curses.curs_set(0)
    scr.keypad(True)
    curses.mousemask(curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED)
    cv = CursesCanvas(scr)
    app = App()
    app.refresh()
    time.sleep(0.3)
    app.refresh()
    next_t = time.monotonic() + REFRESH
    while True:
        cv.erase()
        app.draw(cv)
        cv.flush()
        scr.timeout(max(50, min(1000, int((next_t - time.monotonic()) * 1000))))
        k = scr.getch()
        if k == curses.KEY_MOUSE:
            try:
                _, mx, my, _, _ = curses.getmouse()
                app.click(my, mx)
            except curses.error:
                pass
        elif k not in (-1, curses.KEY_RESIZE) and app.key(k) == "quit":
            break
        if time.monotonic() >= next_t:
            if not app.paused:
                app.refresh()
            next_t = time.monotonic() + REFRESH


def main():
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    if len(sys.argv) >= 3 and sys.argv[1] == "--dump":
        w, h = map(int, sys.argv[2].split("x"))
        app = App()
        app.refresh()
        time.sleep(0.3)
        app.refresh()
        cv = GridCanvas(w, h)
        app.draw(cv)
        print(cv.plain())
        return
    curses.wrapper(run)


if __name__ == "__main__":
    main()
