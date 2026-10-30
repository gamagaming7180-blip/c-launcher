#!/usr/bin/env bash
set -e
TARGET="$HOME/.config/hypr-rice"
mkdir -p "$TARGET"
cp -r "$(cd "$(dirname "$0")" && pwd)"/* "$TARGET"/
chmod +x "$TARGET"/scripts/*.sh "$TARGET"/scripts/*.py "$TARGET"/aod.py 2>/dev/null || true
find "$TARGET" -type f \( -name "*.jsonc" -o -name "*.rasi" -o -name "*.conf" -o -name "*.py" -o -name "*.sh" \) -exec sed -i "s|/home/gama|$HOME|g" {} +
pkill -9 -f panel.py 2>/dev/null || true
"$TARGET/scripts/panel-toggle.sh" --restart &
echo "C Launcher installed!"
