"""Real audio levels for the media ticker and the media card, read from `cava` (optional).

get() returns a list of 8 floats in 0..1 while cava is running and delivering data, else None
(callers then fall back to the decorative animation). Install cava with:  sudo pacman -S cava
"""
import os
import shutil
import subprocess
import threading
import time

BARS = 8
CONF = os.path.expanduser("~/.cache/hypr-rice/cava-media.conf")
CONF_TEXT = """[general]
bars = 8
framerate = 30

[smoothing]
noise_reduction = 55

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
bar_delimiter = 59
frame_delimiter = 10
"""


class Spectrum:
    def __init__(self):
        self.proc = None
        self.levels = None
        self.stamp = 0.0
        self.lock = threading.Lock()

    @staticmethod
    def available():
        return shutil.which("cava") is not None

    def start(self):
        with self.lock:
            if self.proc is not None or not self.available():
                return
            try:
                os.makedirs(os.path.dirname(CONF), exist_ok=True)
                with open(CONF, "w") as fh:
                    fh.write(CONF_TEXT)
                proc = subprocess.Popen(["cava", "-p", CONF], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        stdin=subprocess.DEVNULL, text=True, bufsize=1)
            except OSError:
                return
            self.proc = proc
        threading.Thread(target=self._read, args=(proc,), daemon=True).start()

    def stop(self):
        with self.lock:
            proc, self.proc, self.levels = self.proc, None, None
        if proc is not None:
            try:
                proc.terminate()
            except OSError:
                pass

    def _read(self, proc):
        try:
            for line in proc.stdout:
                vals = [v for v in line.strip().strip(";").split(";") if v]
                if len(vals) < BARS:
                    continue
                try:
                    lv = [max(0.0, min(1.0, int(v) / 100.0)) for v in vals[:BARS]]
                except ValueError:
                    continue
                with self.lock:
                    self.levels, self.stamp = lv, time.monotonic()
        finally:
            with self.lock:
                if self.proc is proc:
                    self.proc, self.levels = None, None

    def get(self):
        with self.lock:
            if self.levels is not None and time.monotonic() - self.stamp < 0.8:
                return list(self.levels)
        return None
