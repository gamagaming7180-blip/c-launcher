#!/usr/bin/env bash
# A friendly random line for the lock screen. Add your own lines to the list.
quips=(
  "Welcome back. The pixels missed you."
  "Fingers at the ready."
  "Locked, loaded, and looking good."
  "Nothing to see here, officially."
  "Your files say hi."
  "One touch and you're in."
  "Arch, btw."
  "Be right back, said the screen."
  "The cursor was getting lonely."
  "Tiny whorls, big access."
  "Sensor warmed up and waiting."
  "Another day, another rice."
  "Hyprland: now with 100% more you."
  "Hydrate. Stretch. Then unlock."
)
echo "${quips[RANDOM % ${#quips[@]}]}"
