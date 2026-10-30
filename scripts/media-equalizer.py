#!/usr/bin/env python3
"""Animated Waybar MPRIS ticker. Bars are decorative, not a real audio spectrum."""
import json, math, os, shutil, subprocess, sys, threading, time

try:                                   # real audio levels when cava is installed (optional)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mediaspec import Spectrum
except Exception:
    Spectrum = None
USE_CAVA = True

POLL_INTERVAL = 0.55
FRAME_INTERVAL = 0.14
HIDE_DELAY = 2.0
BAR_LEVELS = "▁▂▃▄▅▆▇"

def run(args, timeout=0.9):
    try:
        p = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return p.stdout.strip() if p.returncode == 0 else ""

def compact(value, maxlen):
    value = " ".join((value or "").replace("\n", " ").replace("\r", " ")
                     .replace("\t", " ").split())
    return value if len(value) <= maxlen else value[:maxlen-1].rstrip() + "…"

def query_active_media():
    if not shutil.which("playerctl"):
        return None
    fmt = "{{playerName}}\t{{status}}\t{{title}}\t{{artist}}\t{{album}}"
    output_text = run(["playerctl", "-a", "metadata", "--format", fmt])
    playing, paused = [], []
    for line in output_text.splitlines():
        fields = (line.split("\t") + [""] * 5)[:5]
        player, state, title, artist, album = [part.strip() for part in fields]
        if state not in ("Playing", "Paused") or not (title or artist or album):
            continue
        item = {"player": player or "Media player", "status": state,
                "title": title or "Unknown track", "artist": artist, "album": album}
        (playing if state == "Playing" else paused).append(item)
    return playing[0] if playing else (paused[0] if paused else None)

def wave_frame(t, levels=None):
    bars = []
    if levels:                                     # the real song: one bar per frequency band
        return "".join(BAR_LEVELS[min(6, int(max(0.0, min(1.0, v)) * 7))] for v in levels[:8])
    for i in range(8):
        a = (math.sin(t*5.3 - i*0.88) + 1.0) / 2.0
        b = (math.sin(t*3.1 + i*0.63 + 0.8) + 1.0) / 2.0
        c = (math.sin(t*7.1 - i*1.17 + 1.4) + 1.0) / 2.0
        level = int(max(0.0, min(1.0, a*0.54 + b*0.31 + c*0.15)) * 6)
        bars.append(BAR_LEVELS[level])
    return "".join(bars)

def output(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()

def monitor(shared, lock, stop):
    while not stop.is_set():
        media = query_active_media()
        with lock:
            shared["media"] = media
            shared["updated"] = time.monotonic()
            shared["seq"] = int(shared.get("seq", 0)) + 1
        stop.wait(POLL_INTERVAL)

def ensure_card():
    """Start the background helpers (media card watcher, volume / brightness pop-up). Each is single-instance, so
    this is harmless when they are already running."""
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("media-card.py", "osd.py"):
        path = os.path.join(here, name)
        if not os.path.isfile(path):
            continue
        try:
            log = open(os.path.expanduser("~/.cache/hypr-rice-%s.log" % name[:-3]), "a")
            subprocess.Popen([sys.executable, path, "--hidden"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=log, start_new_session=True)
        except OSError:
            pass


def main():
    ensure_card()
    spec = Spectrum() if (Spectrum and USE_CAVA and Spectrum.available()) else None
    idle_since = None
    last_ensure = time.monotonic()
    shared = {"media": None, "updated": time.monotonic(), "seq": 0}
    lock, stop = threading.Lock(), threading.Event()
    threading.Thread(target=monitor, args=(shared, lock, stop), daemon=True).start()
    last_seq, current, last_valid = -1, None, None
    missing_since = None
    last_render_key = ("hidden",)
    started = time.monotonic()
    output({"text": "", "tooltip": "", "class": "hidden"})
    try:
        while True:
            now = time.monotonic()
            if now - last_ensure > 15:
                last_ensure = now
                ensure_card()
            with lock:
                seq, polled_media = int(shared["seq"]), shared["media"]
                updated_at = float(shared["updated"])
            if seq != last_seq:
                last_seq = seq
                if polled_media:
                    current, last_valid, missing_since = dict(polled_media), dict(polled_media), None
                else:
                    current = None
                    if last_valid is not None and missing_since is None:
                        missing_since = updated_at
            visible_media = current
            status = visible_media["status"] if visible_media else ""
            if visible_media is None and last_valid is not None and missing_since is not None:
                if now - missing_since < HIDE_DELAY:
                    visible_media, status = last_valid, "Paused"
                else:
                    last_valid, missing_since = None, None
            if visible_media is None:
                key = ("hidden",)
                if key != last_render_key:
                    output({"text": "", "tooltip": "", "class": "hidden"})
                    last_render_key = key
            else:
                title = compact(visible_media.get("title", "Unknown track"), 22)
                artist = compact(visible_media.get("artist", ""), 70)
                player = compact(visible_media.get("player", "Media player"), 35)
                playing = status == "Playing"
                if spec is not None:
                    if playing:
                        spec.start()
                        idle_since = None
                    else:
                        idle_since = idle_since or now
                        if now - idle_since > 3.0:
                            spec.stop()
                bars = wave_frame(now-started, spec.get() if spec else None) if playing else "▁▂▁▁▂▁▁▂"
                text = f"{bars}  {title}"
                tooltip = f"{status} · {artist + ' — ' if artist else ''}{visible_media.get('title', title)} · {player}"
                key = ("playing" if playing else "paused", text, tooltip)
                if playing or key != last_render_key:
                    output({"text": text, "tooltip": tooltip,
                            "class": "playing" if playing else "paused"})
                    last_render_key = key
            stop.wait(FRAME_INTERVAL)
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        stop.set()
        if spec is not None:
            spec.stop()

if __name__ == "__main__":
    main()
