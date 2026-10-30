#!/usr/bin/env bash
# Restart only Waybar launched with this rice's exact config and stylesheet.
# Other Waybar instances (including those used by other WMs) are left alone.
set -euo pipefail
RICE="$HOME/.config/hypr-rice"
CONFIG="$RICE/waybar/config.jsonc"
STYLE="$RICE/waybar/style.css"
if [[ ! -f "$CONFIG" || ! -f "$STYLE" ]]; then
  echo "Hypr Rice Waybar config/style not found; nothing restarted." >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to safely identify this rice's Waybar process." >&2
  exit 1
fi
python3 - "$CONFIG" "$STYLE" <<'PY'
import os, signal, subprocess, sys, time
from pathlib import Path
config = os.path.realpath(sys.argv[1])
style = os.path.realpath(sys.argv[2])
found = []
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit():
        continue
    pid = int(entry.name)
    if pid == os.getpid() or pid == os.getppid():
        continue
    try:
        raw = (entry / 'cmdline').read_bytes()
        args = [x.decode(errors='replace') for x in raw.split(b'\0') if x]
    except (OSError, PermissionError):
        continue
    if not args or Path(args[0]).name != 'waybar':
        continue
    normalized = [os.path.realpath(a) if a.startswith('/') else a for a in args]
    if config in normalized and style in normalized:
        found.append((pid, args))
if not found:
    print('No running Waybar instance using this rice config was found. Nothing restarted.')
    print('The new button will appear the next time this rice starts Waybar.')
    raise SystemExit(0)
for pid, _ in found:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
for _ in range(40):
    alive = []
    for pid, _ in found:
        try:
            os.kill(pid, 0)
            alive.append(pid)
        except ProcessLookupError:
            pass
    if not alive:
        break
    time.sleep(0.05)
still_alive = []
for pid, _ in found:
    try:
        os.kill(pid, 0)
        still_alive.append(pid)
    except ProcessLookupError:
        pass
if still_alive:
    print('Could not stop the existing rice Waybar process(es): ' + ', '.join(map(str, still_alive)), file=sys.stderr)
    print('Nothing was relaunched to avoid creating duplicate bars.', file=sys.stderr)
    raise SystemExit(1)
log_path = os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), 'hypr-rice-waybar.log')
os.makedirs(os.path.dirname(log_path), exist_ok=True)
with open(log_path, 'ab') as log:
    for _, args in found:
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
print(f'Restarted {len(found)} Waybar instance(s) using only this rice config.')
PY
