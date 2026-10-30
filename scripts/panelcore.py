"""panelcore: everything the control panel does, with no GTK in it.

Each function shells out to a standard tool and returns plain Python values.
Every call is safe when the tool is missing (returns None / "" / [] / False).
Nothing here blocks the UI: panel.py calls all of it from worker threads.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess as sp
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

RICE = os.path.expanduser("~/.config/hypr-rice")
CACHE = os.path.expanduser("~/.cache/hypr-rice-panel")
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
ENV = {**os.environ, "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}


# ---------------------------------------------------------------- plumbing
def have(cmd):
    return bool(shutil.which(cmd))


def run(cmd, timeout=3.0, stdin=None):
    """Run a command; return CompletedProcess or None if missing / timed out."""
    if not have(cmd[0]):
        return None
    try:
        return sp.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV, input=stdin)
    except (OSError, sp.SubprocessError):
        return None


def sh(cmd, timeout=3.0):
    """stdout text of a command, '' on any failure."""
    r = run(cmd, timeout)
    return r.stdout if r else ""


def spawn(cmd):
    """Start a command fully detached (it outlives the panel)."""
    if isinstance(cmd, str):
        cmd = ["bash", "-c", cmd]
    try:
        sp.Popen(cmd, stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL, start_new_session=True)
    except OSError:
        pass


def notify(title, body=""):
    spawn(["notify-send", "-a", "Control panel", "-t", "3500", title, body])


def split_terse(line):
    """Split nmcli --terse output, honouring \\: and \\\\ escapes."""
    fields, part, esc = [], [], False
    for ch in line.rstrip("\n"):
        if esc:
            part.append(ch)
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            fields.append("".join(part))
            part = []
        else:
            part.append(ch)
    fields.append("".join(part))
    return fields


def tidy(text, limit=140):
    text = re.sub(r"\s+", " ", (text or "").strip())
    text = re.sub(r"^Error:\s*", "", text)
    return text[:limit]


# ---------------------------------------------------------------- audio / light
def volume():
    """-> (percent 0..150, muted) or None"""
    m = re.search(r"Volume:\s*([\d.]+)(\s*\[MUTED\])?", sh(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]))
    return (round(float(m.group(1)) * 100), bool(m.group(2))) if m else None


def set_volume(pct):
    sh(["wpctl", "set-volume", "-l", "1", "@DEFAULT_AUDIO_SINK@", f"{int(pct)}%"])


def toggle_mute():
    sh(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])


def mic_muted():
    out = sh(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"])
    return None if not out else "[MUTED]" in out


def toggle_mic():
    sh(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"])


def brightness():
    """-> percent or None  (brightnessctl -m: dev,class,cur,pct,max)"""
    parts = sh(["brightnessctl", "-m"]).strip().split(",")
    try:
        return int(parts[3].rstrip("%"))
    except (IndexError, ValueError):
        return None


def set_brightness(pct):
    sh(["brightnessctl", "-q", "set", f"{max(1, int(pct))}%"])


def audio_devices(kind="sink"):
    """Outputs (kind='sink') or inputs ('source'): [dict(id, name, default, kind)] sorted default-first.
    Uses pactl (works on PipeWire and PulseAudio)."""
    if not have("pactl"):
        return []
    default = sh(["pactl", f"get-default-{kind}"]).strip()
    out = []
    raw = sh(["pactl", "-f", "json", "list", f"{kind}s"], 4.0)
    try:
        for d in json.loads(raw):
            name = d.get("name", "")
            if kind == "source" and (name.endswith(".monitor") or d.get("monitor_of_sink") not in (None, 4294967295)):
                continue
            out.append(dict(id=name, name=d.get("description") or name, default=name == default, kind=kind,
                            hint=" ".join([name, str(d.get("properties", {}).get("device.form_factor", "")),
                                           str(d.get("properties", {}).get("device.bus", ""))]).lower()))
    except (ValueError, TypeError, AttributeError):
        out = []
        for line in sh(["pactl", "list", "short", f"{kind}s"], 4.0).splitlines():
            p = line.split("\t")
            if len(p) < 2 or (kind == "source" and p[1].endswith(".monitor")):
                continue
            pretty = re.sub(r"^(alsa_output|alsa_input|bluez_output|bluez_input)\.", "", p[1]).replace("_", " ").replace(".", " ")
            out.append(dict(id=p[1], name=pretty, default=p[1] == default, kind=kind, hint=p[1].lower()))
    return sorted(out, key=lambda d: (not d["default"], d["name"].lower()))


def set_default_audio(kind, name):
    """Make `name` the default and move every playing stream to it."""
    sh(["pactl", f"set-default-{kind}", name])
    streams, move = ("sink-inputs", "move-sink-input") if kind == "sink" else ("source-outputs", "move-source-output")
    for line in sh(["pactl", "list", "short", streams]).splitlines():
        sid = line.split("\t")[0]
        if sid.isdigit():
            sh(["pactl", move, sid, name])


# ---------------------------------------------------------------- Wi-Fi
def wifi():
    """-> (enabled, active connection name or '') or None"""
    st = sh(["nmcli", "radio", "wifi"]).strip()
    if not st:
        return None
    name = ""
    for line in sh(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"]).splitlines():
        f = split_terse(line)
        if len(f) >= 2 and f[1] == "802-11-wireless" and f[0] != HOTSPOT:
            name = f[0]
            break
    return (st == "enabled", name)


def set_wifi(on):
    sh(["nmcli", "radio", "wifi", "on" if on else "off"], 6.0)


def wifi_device():
    for line in sh(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"]).splitlines():
        f = split_terse(line)
        if len(f) >= 2 and f[1] == "wifi":
            return f[0]
    return ""


def wifi_saved():
    """Names of saved Wi-Fi profiles (normally the same as the SSID)."""
    names = set()
    for line in sh(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]).splitlines():
        f = split_terse(line)
        if len(f) >= 2 and f[1] == "802-11-wireless" and f[0] != HOTSPOT:
            names.add(f[0])
    return names


def wifi_list():
    """Nearby networks from NetworkManager's cache (instant), strongest first, one per SSID.
    [dict(ssid, signal, security, active, band)]"""
    out = sh(["nmcli", "-t", "-e", "yes", "-f", "IN-USE,SSID,SIGNAL,SECURITY,FREQ", "device", "wifi", "list"], 5.0)
    best = {}
    for line in out.splitlines():
        f = split_terse(line)
        if len(f) < 5 or not f[1].strip():
            continue
        try:
            sig = max(0, min(100, int(f[2])))
        except ValueError:
            sig = 0
        m = re.match(r"\d+", f[4])
        freq = int(m.group(0)) if m else 0
        item = dict(ssid=f[1], signal=sig, security=f[3].strip(), active=f[0].strip() == "*",
                    band="5 GHz" if freq >= 4900 else ("2.4 GHz" if freq else ""))
        old = best.get(f[1])
        if not old or item["active"] or (not old["active"] and sig > old["signal"]):
            best[f[1]] = item
    return sorted(best.values(), key=lambda n: (not n["active"], -n["signal"], n["ssid"].lower()))


def wifi_rescan():
    sh(["nmcli", "device", "wifi", "rescan"], 6.0)


def wifi_ip():
    dev = wifi_device()
    if not dev:
        return ""
    for line in sh(["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", dev]).splitlines():
        if ":" in line:
            return line.split(":", 1)[1].split("/")[0]
    return ""


def wifi_connect(ssid, password=None):
    """-> (ok, message, needs_password).
    A saved network is simply brought up. A new one is created, and if that fails the half-made profile
    is deleted again, so a wrong password never leaves a broken entry behind."""
    saved = ssid in wifi_saved()
    if saved and password:
        run(["nmcli", "connection", "modify", "id", ssid, "wifi-sec.psk", password], 6.0)
    if saved:
        cmd = ["nmcli", "-w", "25", "connection", "up", "id", ssid]
    else:
        cmd = ["nmcli", "-w", "25", "device", "wifi", "connect", ssid] + (["password", password] if password else [])
    r = run(cmd, 40.0)
    if r is None:
        return False, "nmcli is not available", False
    if r.returncode == 0:
        return True, f"Connected to {ssid}", False
    msg = tidy(r.stderr or r.stdout)
    if not saved and ssid in wifi_saved():
        run(["nmcli", "connection", "delete", "id", ssid], 6.0)
    needs = bool(re.search(r"secret|password|psk|auth|activation failed|no suitable", msg, re.I))
    return False, msg or "Could not connect", needs


def wifi_disconnect():
    dev = wifi_device()
    if dev:
        sh(["nmcli", "device", "disconnect", dev], 8.0)


def wifi_forget(ssid):
    sh(["nmcli", "connection", "delete", "id", ssid], 6.0)


# ---------------------------------------------------------------- hotspot
HOTSPOT = "rice-hotspot"


def hotspot_active():
    for line in sh(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"]).splitlines():
        if split_terse(line)[0] == HOTSPOT:
            return True
    return False


def hotspot_info():
    """-> (ssid, password) of the saved hotspot, or ('', '') if never set up."""
    if HOTSPOT not in {split_terse(l)[0] for l in sh(["nmcli", "-t", "-f", "NAME", "connection", "show"]).splitlines()}:
        return "", ""
    ssid = sh(["nmcli", "-g", "802-11-wireless.ssid", "connection", "show", HOTSPOT]).strip()
    psk = sh(["nmcli", "-s", "-g", "802-11-wireless-security.psk", "connection", "show", HOTSPOT]).strip()
    return ssid, psk


def _random_password(n=10):
    return hashlib.sha256(os.urandom(16)).hexdigest()[:n]


def hotspot_save(ssid=None, password=None):
    """Create or update the hotspot profile. -> (ok, message)"""
    cur_ssid, cur_psk = hotspot_info()
    ssid = (ssid or cur_ssid or (os.uname().nodename[:20] or "rice-hotspot")).strip()
    password = (password or cur_psk or _random_password()).strip()
    if len(password) < 8 or len(password) > 63:
        return False, "Password must be 8-63 characters"
    if not cur_ssid:
        dev = wifi_device()
        if not dev:
            return False, "No Wi-Fi adapter found"
        r = run(["nmcli", "connection", "add", "type", "wifi", "ifname", dev, "con-name", HOTSPOT,
                 "autoconnect", "no", "ssid", ssid, "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg",
                 "ipv4.method", "shared", "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password], 8.0)
    else:
        r = run(["nmcli", "connection", "modify", HOTSPOT, "802-11-wireless.ssid", ssid,
                 "wifi-sec.psk", password], 8.0)
    if r is None or r.returncode:
        return False, tidy(r.stderr if r else "nmcli is not available")
    return True, "Saved"


def hotspot_set(on):
    """-> (ok, message)"""
    if not on:
        r = run(["nmcli", "connection", "down", HOTSPOT], 10.0)
        return True, "Hotspot off"
    ok, msg = hotspot_save()
    if not ok:
        return False, msg
    if not (wifi() or (False,))[0]:
        set_wifi(True)
        time.sleep(1.2)
    r = run(["nmcli", "-w", "20", "connection", "up", HOTSPOT], 30.0)
    if r and r.returncode == 0:
        return True, "Hotspot on"
    return False, tidy(r.stderr if r else "nmcli is not available") or "Could not start the hotspot"


# ---------------------------------------------------------------- airplane mode
def airplane():
    """-> True if every wifi + bluetooth radio is soft-blocked, None if rfkill is missing."""
    out = sh(["rfkill", "-n", "-o", "TYPE,SOFT"])
    rows = [l.split() for l in out.splitlines() if l.strip()]
    rows = [r for r in rows if r[0] in ("wlan", "bluetooth") and len(r) >= 2]
    if not rows:
        return None
    return all(r[1] == "blocked" for r in rows)


def set_airplane(on):
    if have("rfkill"):
        sh(["rfkill", "block" if on else "unblock", "wifi"])
        sh(["rfkill", "block" if on else "unblock", "bluetooth"])
    else:
        sh(["nmcli", "radio", "all", "off" if on else "on"])


# ---------------------------------------------------------------- Bluetooth
def bluetooth():
    """-> powered bool or None (no bluetooth tools / no adapter)"""
    out = sh(["bluetoothctl", "show"], 3.0)
    if not out or "Powered" not in out:
        return None
    return "Powered: yes" in out


def set_bluetooth(on):
    if on:
        sh(["rfkill", "unblock", "bluetooth"])
    sh(["bluetoothctl", "power", "on" if on else "off"], 5.0)


def _bt_info(mac):
    out = sh(["bluetoothctl", "info", mac], 3.0)
    d = dict(mac=mac, name=mac, icon="", paired=False, connected=False, trusted=False, battery=None, rssi=None)
    for line in out.splitlines():
        k, _, v = line.strip().partition(": ")
        if k == "Alias" and v:
            d["name"] = v
        elif k == "Name" and d["name"] == mac:
            d["name"] = v
        elif k == "Icon":
            d["icon"] = v
        elif k in ("Paired", "Connected", "Trusted"):
            d[k.lower()] = v == "yes"
        elif k == "Battery Percentage":
            m = re.search(r"\((\d+)\)", v)
            d["battery"] = int(m.group(1)) if m else None
        elif k == "RSSI":
            m = re.search(r"-?\d+", v)
            d["rssi"] = int(m.group(0)) if m else None
    return d


def bt_devices(seen=()):
    """Paired devices plus anything seen during this scan, with live state.
    Sorted: connected, paired, then nearby by signal."""
    macs = set()
    for line in sh(["bluetoothctl", "devices"], 4.0).splitlines():
        m = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s", line)
        if m:
            macs.add(m.group(1).upper())
    if not macs:
        return []
    with ThreadPoolExecutor(max_workers=6) as ex:
        infos = list(ex.map(_bt_info, sorted(macs)))
    seen = {s.upper() for s in seen}
    keep = [d for d in infos if d["paired"] or d["connected"] or d["mac"] in seen]
    keep = [d for d in keep if d["name"] != d["mac"].replace(":", "-")]       # unnamed randomised addresses
    return sorted(keep, key=lambda d: (not d["connected"], not d["paired"], -(d["rssi"] if d["rssi"] is not None else -999),
                                       d["name"].lower()))


def bt_connected():
    """Names of connected devices (verified per device, since old BlueZ ignores the 'Connected' filter)."""
    macs = [m.group(1).upper() for l in sh(["bluetoothctl", "devices", "Connected"], 3.0).splitlines()
            for m in [re.match(r"Device\s+([0-9A-Fa-f:]{17})\s", l)] if m]
    return [d["name"] for d in map(_bt_info, macs[:6]) if d["connected"]]


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][A-Z0-9]|[\x01\x02\x07]")
_PROMPT = re.compile(r"\[[^\[\]]*\]#\s?")


class BtSession:
    """One long-lived `bluetoothctl` on a pseudo-terminal. It scans, pairs, connects and answers the pairing
    prompts, and reports everything through callback(kind, **info):
        seen(mac, name)  changed(mac)  confirm(passkey)  pin()  result(step, ok, text)  line(text)"""

    def __init__(self, callback):
        self.cb = callback
        self.pid = None
        self.fd = None
        self.alive = False
        self.scanning = False
        self.lock = threading.Lock()

    def start(self):
        import pty
        import termios
        if not have("bluetoothctl") or self.alive:
            return self.alive
        try:
            master, slave = pty.openpty()
            attrs = termios.tcgetattr(slave)
            attrs[3] &= ~termios.ECHO
            termios.tcsetattr(slave, termios.TCSANOW, attrs)
            proc = sp.Popen(["bluetoothctl"], stdin=slave, stdout=slave, stderr=slave, close_fds=True,
                            start_new_session=True, env=ENV)
            os.close(slave)
        except (OSError, sp.SubprocessError):
            return False
        self.proc, self.fd, self.alive = proc, master, True
        threading.Thread(target=self._read, daemon=True).start()
        self.send("agent KeyboardDisplay")
        self.send("default-agent")
        return True

    def send(self, line):
        if not self.alive:
            return
        try:
            with self.lock:
                os.write(self.fd, (line + "\n").encode())
        except OSError:
            self.alive = False

    def scan(self, on):
        self.scanning = on
        self.send("scan on" if on else "scan off")

    def stop(self):
        if not self.alive:
            return
        try:
            self.send("scan off")
            self.send("quit")
            time.sleep(0.1)
        finally:
            self.alive = False
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1.5)
            except Exception:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except Exception:
                    pass
            try:
                os.close(self.fd)
            except OSError:
                pass

    # -- reading
    def _read(self):
        buf = ""
        last_prompt = ""
        while self.alive:
            try:
                data = os.read(self.fd, 4096)
            except OSError:
                break
            if not data:
                break
            buf += _ANSI.sub("", data.decode(errors="replace")).replace("\r", "\n")
            *lines, buf = buf.split("\n")
            for ln in lines:
                ln = _PROMPT.sub("", ln).strip()
                if ln and ln == last_prompt:               # the prompt we already reacted to, now newline-terminated
                    last_prompt = ""
                    continue
                self._line(ln)
            tail = _PROMPT.sub("", buf).strip()
            if tail and tail != last_prompt and re.search(r"\((yes/no|y/n)\):?$|Enter (PIN code|passkey)[^:]*:?$", tail, re.I):
                last_prompt = tail
                self._line(tail)
        self.alive = False

    def _line(self, ln):
        if not ln:
            return
        e = self.cb
        m = re.match(r"\[NEW\]\s+Device\s+([0-9A-F:]{17})\s+(.+)", ln, re.I)
        if m:
            return e("seen", mac=m.group(1).upper(), name=m.group(2))
        m = re.match(r"\[CHG\]\s+Device\s+([0-9A-F:]{17})\s+(.+?):\s*(.*)", ln, re.I)
        if m:
            mac, key, val = m.group(1).upper(), m.group(2), m.group(3)
            if key in ("Name", "Alias", "RSSI") and val:
                e("seen", mac=mac, name=val if key != "RSSI" else "")
            return e("changed", mac=mac)
        m = re.search(r"Confirm passkey\s+(\d+)", ln, re.I)
        if m:
            return e("confirm", passkey=m.group(1))
        if re.search(r"Authorize service|Request authorization", ln, re.I):
            self.send("yes")
            return
        if re.search(r"Enter (PIN code|passkey)", ln, re.I):
            return e("pin")
        if re.search(r"Pairing successful", ln, re.I):
            return e("result", step="pair", ok=True, text="Paired")
        m = re.search(r"Failed to pair:\s*(.*)", ln, re.I)
        if m:
            return e("result", step="pair", ok=False, text=_bt_error(m.group(1)))
        if re.search(r"Connection successful", ln, re.I):
            return e("result", step="connect", ok=True, text="Connected")
        m = re.search(r"Failed to connect:\s*(.*)", ln, re.I)
        if m:
            return e("result", step="connect", ok=False, text=_bt_error(m.group(1)))
        if re.search(r"Successful disconnected|Disconnection successful", ln, re.I):
            return e("result", step="disconnect", ok=True, text="Disconnected")
        m = re.search(r"Failed to disconnect:\s*(.*)", ln, re.I)
        if m:
            return e("result", step="disconnect", ok=False, text=_bt_error(m.group(1)))
        if re.search(r"Device has been removed", ln, re.I):
            return e("result", step="remove", ok=True, text="Removed")


def _bt_error(text):
    t = text.strip()
    if "AuthenticationCanceled" in t or "AuthenticationRejected" in t:
        return "Pairing was declined"
    if "AuthenticationTimeout" in t:
        return "Pairing timed out"
    if "AlreadyExists" in t:
        return "Already paired"
    if "InProgress" in t:
        return "Busy, try again"
    if "page-timeout" in t or "ConnectionAttemptFailed" in t or "Host is down" in t:
        return "Device not reachable"
    return tidy(re.sub(r"org\.bluez\.Error\.", "", t)) or "Failed"


# ---------------------------------------------------------------- power / misc
def dnd():
    """-> bool or None (mako not running)"""
    if not have("makoctl"):
        return None
    r = run(["makoctl", "mode"], 2)
    return None if (r is None or r.returncode) else "do-not-disturb" in r.stdout.split()


def toggle_dnd():
    sh(["makoctl", "mode", "-t", "do-not-disturb"])


NL = os.path.join(RICE, "scripts", "nightlight.sh")


NL_NATIVE = not os.path.isfile(NL)          # no helper script: drive hyprsunset directly
NL_TEMP_FILE = os.path.join(CACHE, "nightlight-temp")


def nightlight_available():
    return have("hyprsunset") and (not NL_NATIVE or have("pgrep"))


def _hs_pid_temp():
    """(running, temperature) of a hyprsunset started with -t, read from /proc."""
    for pid in sh(["pgrep", "-x", "hyprsunset"]).split():
        try:
            args = open(f"/proc/{pid}/cmdline").read().split("\0")
        except OSError:
            continue
        if "-t" in args and args.index("-t") + 1 < len(args):
            try:
                return True, int(args[args.index("-t") + 1])
            except ValueError:
                pass
        return True, None
    return False, None


def _hs_start(kelvin):
    kelvin = int(max(1000, min(6500, kelvin)))
    sh(["pkill", "-x", "hyprsunset"])
    time.sleep(0.15)
    spawn(["hyprsunset", "-t", str(kelvin)])
    try:
        os.makedirs(CACHE, exist_ok=True)
        open(NL_TEMP_FILE, "w").write(str(kelvin))
    except OSError:
        pass


def _hs_saved():
    try:
        return int(open(NL_TEMP_FILE).read().strip())
    except (OSError, ValueError):
        return 4000


def nightlight():
    """-> dict(on, temp, auto, frm, to) or None"""
    if NL_NATIVE:
        on, temp = _hs_pid_temp()
        return dict(on=on, temp=temp or _hs_saved(), auto=False, frm="", to="")
    out = sh([NL, "status"]).split("\n")
    try:
        on, temp = out[0].split()
        kv = dict(x.split("=") for x in out[1].split())
        return dict(on=on == "on", temp=int(temp), auto=kv["auto"] == "1", frm=kv["from"], to=kv["to"])
    except (ValueError, IndexError, KeyError):
        return None


def toggle_nightlight():
    if NL_NATIVE:
        if _hs_pid_temp()[0]:
            sh(["pkill", "-x", "hyprsunset"])
        else:
            _hs_start(_hs_saved())
        return
    sh([NL, "toggle"])


def set_warmth(kelvin):
    if NL_NATIVE:
        _hs_start(kelvin)
        return
    sh([NL, "on", str(int(kelvin))])


def set_night_auto(on):
    if not NL_NATIVE:
        sh([NL, "auto", "on" if on else "off"])


PROFILES = ["power-saver", "balanced", "performance"]


def profile():
    return sh(["powerprofilesctl", "get"]).strip() or None


def cycle_profile():
    cur = profile()
    if not cur:
        return
    avail = sh(["powerprofilesctl", "list"])
    order = [p for p in PROFILES if p in avail] or PROFILES
    sh(["powerprofilesctl", "set", order[(order.index(cur) + 1) % len(order)] if cur in order else order[0]])


def _num(path):
    try:
        return float(open(path).read().strip())
    except (OSError, ValueError):
        return None


def battery():
    """-> (percent 0..100, status) or None (desktop). Some firmware reports a capacity above 100, so when
    that happens the percentage is worked out from the charge / energy counters instead, then clamped."""
    total_now = total_full = 0.0
    pcts, status = [], ""
    for d in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        cap = _num(d + "/capacity")
        if cap is None:
            continue
        pcts.append(cap)
        status = status or (open(d + "/status").read().strip() if os.path.exists(d + "/status") else "")
        for now, full in (("energy_now", "energy_full"), ("charge_now", "charge_full")):
            n, f = _num(f"{d}/{now}"), _num(f"{d}/{full}")
            if n is not None and f:
                total_now += n
                total_full += f
                break
    if not pcts:
        return None
    pct = sum(pcts) / len(pcts)
    if (pct > 100 or pct < 0) and total_full:
        pct = 100.0 * total_now / total_full
    return int(max(0, min(100, round(pct)))), status


# ---- stay awake (blocks idle + sleep through systemd-inhibit; nothing persistent is installed)
CAFFEINE_PID = os.path.join(RUNTIME, "hypr-rice-caffeine.pid")


def caffeine_available():
    return have("systemd-inhibit") and have("sleep")


def caffeine_on():
    """True if the stay-awake lock is currently held."""
    try:
        pid = int(open(CAFFEINE_PID).read().strip())
        os.kill(pid, 0)
        return "hypr-rice-caffeine" in open(f"/proc/{pid}/cmdline").read()
    except (OSError, ValueError):
        return False


def set_caffeine(on):
    if not on:
        try:
            pid = int(open(CAFFEINE_PID).read().strip())
            os.killpg(pid, signal.SIGTERM)
        except (OSError, ValueError):
            pass
        try:
            os.unlink(CAFFEINE_PID)
        except OSError:
            pass
        return True
    if caffeine_on():
        return True
    try:
        p = sp.Popen(["systemd-inhibit", "--what=idle:sleep", "--who=hypr-rice", "--why=hypr-rice-caffeine",
                      "--mode=block", "sleep", "infinity"], stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL,
                     start_new_session=True)
        time.sleep(0.25)
        if p.poll() is not None:
            notify("Stay awake", "Could not take the idle lock.")
            return False
        open(CAFFEINE_PID, "w").write(str(p.pid))
        return True
    except OSError:
        return False


# ---- screen recording. Uses your own screen-record-toggle.sh if you have one, otherwise wf-recorder directly.
REC = os.path.join(RICE, "scripts", "screen-record-toggle.sh")
REC_SCRIPT = os.path.isfile(REC)
REC_DIR = os.path.expanduser("~/Videos/Recordings")
REC_PID = os.path.join(RUNTIME, "hypr-rice-rec.pid")


def rec_available():
    return have("wf-recorder")


def _rec_state():
    """(pid, started_at, outfile) of a live native recording, else None."""
    try:
        pid, started, out = open(REC_PID).read().split(" ", 2)
        os.kill(int(pid), 0)
        if "wf-recorder" in open(f"/proc/{pid}/cmdline").read():
            return int(pid), float(started), out.strip()
    except (OSError, ValueError):
        pass
    return None


def rec_status():
    """-> (recording?, seconds so far)"""
    if REC_SCRIPT:
        try:
            return json.loads(sh([REC, "status"])).get("class") == "recording", 0
        except ValueError:
            return False, 0
    st = _rec_state()
    return (True, int(time.time() - st[1])) if st else (False, 0)


REC_MODS = os.path.join(RUNTIME, "hypr-rice-rec.mods")


def _pa(*a):
    return sh(["pactl", *a], 4.0).strip()


def _rec_audio_device(mode):
    """PulseAudio/PipeWire source for wf-recorder. mode: mic | sys | both. -> name or None."""
    if not have("pactl"):
        return None
    mic = _pa("get-default-source")
    sink = _pa("get-default-sink")
    if mode == "mic":
        return mic or None
    if mode == "sys":
        return (sink + ".monitor") if sink else None
    if not mic or not sink:                                   # both: mix mic + system sound into a virtual sink
        return (sink + ".monitor") if sink else (mic or None)
    mods = []
    for args in (["load-module", "module-null-sink", "sink_name=hypr_rec_mix",
                  "sink_properties=device.description=RecordingMix"],
                 ["load-module", "module-loopback", f"source={mic}", "sink=hypr_rec_mix", "latency_msec=40"],
                 ["load-module", "module-loopback", f"source={sink}.monitor", "sink=hypr_rec_mix", "latency_msec=40"]):
        mid = _pa(*args)
        if not mid.isdigit():
            for m in mods:
                _pa("unload-module", m)
            return (sink + ".monitor")
        mods.append(mid)
    open(REC_MODS, "w").write(" ".join(mods))
    return "hypr_rec_mix.monitor"


def _rec_audio_cleanup():
    try:
        mods = open(REC_MODS).read().split()
        os.unlink(REC_MODS)
    except OSError:
        return
    for m in reversed(mods):
        _pa("unload-module", m)


def rec_start(region=False, audio=""):
    """Start recording. region: drag a box (needs slurp). audio: "" | "mic" | "sys" | "both". -> True if recording."""
    if audio is True:
        audio = "mic"
    if REC_SCRIPT:                                            # your screen-record-toggle.sh does the recording
        spawn([REC, "start", audio or "none"] + (["region"] if region else []))
        return True
    if _rec_state():
        return True
    cmd = ["wf-recorder"]
    if audio:
        dev = _rec_audio_device(audio)
        if not dev:
            notify("Screen record", "No audio device found, recording without sound.")
        else:
            cmd.append("--audio=" + dev)
    if region:
        geo = sh(["slurp"], 90.0).strip()
        if not geo:
            return False
        cmd += ["-g", geo]
    try:
        os.makedirs(REC_DIR, exist_ok=True)
        out = os.path.join(REC_DIR, "rec-" + time.strftime("%Y%m%d-%H%M%S") + ".mp4")
        p = sp.Popen(cmd + ["-f", out], stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL, start_new_session=True)
        time.sleep(0.5)
        if p.poll() is not None:
            _rec_audio_cleanup()
            notify("Screen record", "wf-recorder could not start.")
            return False
        open(REC_PID, "w").write(f"{p.pid} {time.time()} {out}")
        notify("Recording started", "Open the panel and tap Screen record to stop.")
        return True
    except OSError:
        return False


def rec_stop():
    if REC_SCRIPT:
        spawn([REC, "stop"])
        return
    st = _rec_state()
    if not st:
        return
    try:
        os.kill(st[0], signal.SIGINT)                # wf-recorder finishes the file on SIGINT
        for _ in range(30):
            time.sleep(0.1)
            try:
                os.kill(st[0], 0)
            except OSError:
                break
    except OSError:
        pass
    try:
        os.unlink(REC_PID)
    except OSError:
        pass
    _rec_audio_cleanup()
    notify("Recording saved", st[2])


def rec_on():
    return rec_status()[0]


# ---------------------------------------------------------------- media
def media():
    """Pick the active MPRIS player. -> dict(player status title artist art pos length) or None."""
    fmt = "{{playerName}}\t{{status}}\t{{title}}\t{{artist}}\t{{mpris:artUrl}}\t{{position}}\t{{mpris:length}}"
    best = None
    for line in sh(["playerctl", "-a", "metadata", "--format", fmt]).splitlines():
        p = line.split("\t")
        if len(p) < 7:
            continue
        item = dict(player=p[0], status=p[1], title=p[2], artist=p[3], art=p[4], pos=_us(p[5]), length=_us(p[6]))
        if item["status"] == "Playing":
            return item
        if best is None and item["status"] == "Paused":
            best = item
    return best


def _us(s):
    try:
        return int(s) / 1_000_000
    except ValueError:
        return 0.0


def player_cmd(player, *args):
    sh(["playerctl", "-p", player, *args])


def art_file(url):
    """Local path for an album-art URL (downloads and caches http(s)). '' if none."""
    if not url:
        return ""
    if url.startswith("file://"):
        p = urllib.request.url2pathname(url[7:])
        return p if os.path.isfile(p) else ""
    if url.startswith(("http://", "https://")):
        os.makedirs(CACHE, exist_ok=True)
        p = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest())
        if not os.path.isfile(p):
            try:
                with urllib.request.urlopen(url, timeout=4) as r, open(p, "wb") as f:
                    f.write(r.read(4_000_000))
            except Exception:
                return ""
        return p
    return ""


def fmt_time(sec):
    sec = int(max(0, sec))
    return f"{sec // 60}:{sec % 60:02d}"


# ---------------------------------------------------------------- colours
COLORS_CSS = os.path.join(RICE, "waybar", "colors.css")


def sync_wallpaper_colors():
    """If the wallpaper on screen is not the one the accents were taken from (you changed it by hand),
    re-sample it. Returns True when the colours changed. Cheap no-op otherwise."""
    wp = ""
    for line in sh(["hyprctl", "hyprpaper", "listactive"], 2.5).splitlines():
        m = re.search(r"(/\S.*?\.(?:png|jpe?g|webp))\s*$", line.strip(), re.I)
        if m and os.path.isfile(m.group(1)):
            wp = m.group(1)
            break
    if not wp:
        return False
    try:
        known = json.load(open(os.path.join(RICE, "generated", "colors.json"))).get("wallpaper")
    except (OSError, ValueError):
        known = None
    if known == wp:
        return False
    script = os.path.join(RICE, "scripts", "wallcolors.py")
    if not os.path.isfile(script):
        return False
    r = run(["python3", script, wp, "--no-reload"], 20.0)
    return bool(r and r.returncode == 0)


def css_colors():
    base = (
        "@define-color base #1e1e2e; @define-color surface0 #313244; @define-color surface1 #45475a;\n"
        "@define-color text #cdd6f4; @define-color subtext #a6adc8; @define-color red #f38ba8;\n"
        "@define-color green #a6e3a1; @define-color accent #cba6f7; @define-color accent2 #89b4fa;\n"
    )
    try:
        extra = open(COLORS_CSS, encoding="utf-8").read()
        extra = "\n".join(l for l in extra.splitlines() if l.strip().startswith("@define-color"))
    except OSError:
        extra = ""
    return base + extra + "\n"
