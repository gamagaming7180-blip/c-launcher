#!/usr/bin/env python3
"""Compact, wallpaper-accented MPRIS controls popup with delayed pointer-leave close."""
from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HYPR_RICE_MEDIA_CONTROLS_V2 = True
RICE = Path.home() / ".config" / "hypr-rice"
AUTO_CLOSE_MS = 2100

try:
    ctypes.CDLL("libgtk-layer-shell.so.0", mode=ctypes.RTLD_GLOBAL)
except OSError:
    pass

try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import Gdk, GLib, Gtk, GtkLayerShell, Pango
except (ImportError, ValueError) as exc:
    message = "Media controls need GTK3 and gtk-layer-shell. On CachyOS: sudo pacman -S python-gobject gtk3 gtk-layer-shell"
    try:
        subprocess.Popen(["notify-send", "Media controls", message])
    except OSError:
        print(message, file=sys.stderr)
    raise SystemExit(1) from exc


def run(args: list[str], timeout: float = 1.0) -> tuple[bool, str]:
    try:
        result = subprocess.run(args, check=False, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return result.returncode == 0, (result.stdout.strip() if result.returncode == 0 else result.stderr.strip())


def players() -> list[str]:
    if not shutil.which("playerctl"):
        return []
    ok, out = run(["playerctl", "-l"])
    return [line.strip() for line in out.splitlines() if line.strip()] if ok else []


def current_player() -> str | None:
    available = players()
    paused = None
    for name in available:
        ok, current_status = run(["playerctl", "--player", name, "status"])
        if ok and current_status == "Playing":
            return name
        if ok and current_status == "Paused" and paused is None:
            paused = name
    return paused or (available[0] if available else None)


def value(player: str | None, key: str) -> str:
    if not player:
        return ""
    ok, out = run(["playerctl", "--player", player, "metadata", "--format", "{{" + key + "}}"])
    return out if ok else ""


def status(player: str | None) -> str:
    if not player:
        return "Stopped"
    ok, out = run(["playerctl", "--player", player, "status"])
    return out if ok else "Stopped"


def palette() -> dict[str, str]:
    """Read base text from style.css, then wallpaper accents from colors.css/generated json."""
    colors = {
        "accent": "#89b4fa", "accent2": "#cba6f7", "base": "#1e1e2e",
        "surface0": "#313244", "surface1": "#45475a", "text": "#cdd6f4", "subtext": "#a6adc8",
    }
    css_names = tuple(colors)
    for path in (RICE / "waybar" / "style.css", RICE / "waybar" / "update.css", RICE / "waybar" / "colors.css"):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for name in css_names:
            match = re.search(r"@define-color\s+" + re.escape(name) + r"\s+(#[0-9a-fA-F]{6})\s*;", content)
            if match:
                colors[name] = match.group(1)
    try:
        generated = json.loads((RICE / "generated" / "colors.json").read_text(encoding="utf-8"))
        for name in ("accent", "accent2"):
            value = str(generated.get(name, ""))
            if re.fullmatch(r"#?[0-9a-fA-F]{6}", value):
                colors[name] = value if value.startswith("#") else "#" + value
    except (OSError, ValueError, TypeError):
        pass
    return colors


def rgba(hexcolor: str, alpha: float) -> str:
    h = hexcolor.lstrip("#")
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except (ValueError, IndexError):
        r, g, b = 137, 180, 250
    return f"rgba({r}, {g}, {b}, {alpha})"


class MediaControls:
    def __init__(self) -> None:
        self.alive = True
        self.player = current_player()
        self.colors = palette()
        self.pointer_inside_card = False
        self.close_timer: int | None = None

        self.window = Gtk.Window()
        self.window.set_title("Hypr Rice Media Controls")
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_app_paintable(True)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        visual = self.window.get_screen().get_rgba_visual()
        if visual:
            self.window.set_visual(visual)
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, "rice-media-controls")
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self.window, edge, True)
        GtkLayerShell.set_exclusive_zone(self.window, -1)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, 44)

        provider = Gtk.CssProvider()
        c = self.colors
        css = f"""
        window.media-popup {{ background-color: transparent; color: {c['text']}; }}
        box.media-card {{ background-color: {rgba(c['base'], 0.76)}; border: 1px solid {rgba(c['accent'], 0.50)}; border-radius: 18px; padding: 14px; }}
        label.track-title {{ color: {c['text']}; font-weight: 800; font-size: 14px; }}
        label.track-subtitle {{ color: {c['subtext']}; font-size: 11px; }}
        label.status {{ color: {c['accent2']}; font-size: 10px; }}
        button.control {{ background-image: none; box-shadow: none; text-shadow: none; color: {c['text']}; background-color: {rgba(c['accent'], 0.13)}; border: 1px solid {rgba(c['accent'], 0.34)}; border-radius: 12px; padding: 8px 10px; min-height: 32px; }}
        button.control:hover {{ background-color: {rgba(c['accent'], 0.24)}; border-color: {rgba(c['accent'], 0.72)}; }}
        button.control.primary {{ color: {c['base']}; background-color: {c['accent']}; font-weight: 800; }}
        button.control:disabled {{ opacity: 0.4; }}
        button.close {{ background-image: none; background-color: transparent; border: none; box-shadow: none; color: {c['subtext']}; padding: 0 5px; }}
        """
        provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window.get_style_context().add_class("media-popup")

        bg = Gtk.EventBox()
        bg.set_visible_window(False)
        bg.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        bg.connect("button-press-event", self.on_outside_click)
        self.window.add(bg)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_halign(Gtk.Align.CENTER)
        root.set_valign(Gtk.Align.START)
        root.set_margin_top(2)
        bg.add(root)

        shield = Gtk.EventBox()
        shield.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        shield.connect("button-press-event", lambda *_: True)
        shield.connect("enter-notify-event", self.on_card_enter)
        shield.connect("leave-notify-event", self.on_card_leave)
        root.add(shield)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.set_size_request(370, -1)
        card.get_style_context().add_class("media-card")
        shield.add(card)

        header = Gtk.Box(spacing=8)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.title = Gtk.Label(label="")
        self.title.set_xalign(0)
        self.title.set_ellipsize(Pango.EllipsizeMode.END)
        self.title.set_max_width_chars(34)
        self.title.get_style_context().add_class("track-title")
        self.subtitle = Gtk.Label(label="")
        self.subtitle.set_xalign(0)
        self.subtitle.set_ellipsize(Pango.EllipsizeMode.END)
        self.subtitle.set_max_width_chars(38)
        self.subtitle.get_style_context().add_class("track-subtitle")
        self.state = Gtk.Label(label="")
        self.state.set_xalign(0)
        self.state.get_style_context().add_class("status")
        for widget in (self.title, self.subtitle, self.state):
            info.pack_start(widget, False, False, 0)
        info.set_hexpand(True)
        header.pack_start(info, True, True, 0)
        close = Gtk.Button(label="×")
        close.get_style_context().add_class("close")
        close.set_valign(Gtk.Align.START)
        close.connect("clicked", lambda *_: self.close())
        header.pack_end(close, False, False, 0)
        card.pack_start(header, False, False, 0)

        controls = Gtk.Box(spacing=6)
        controls.set_homogeneous(True)
        self.prev = self.button("⏮ Previous", self.do_previous)
        self.play = self.button("▶ Play", self.do_play_pause, "primary")
        self.next = self.button("⏭ Next", self.do_next)
        self.repeat = self.button("↻ Repeat: Off", self.do_repeat)
        for widget in (self.prev, self.play, self.next, self.repeat):
            controls.pack_start(widget, True, True, 0)
        card.pack_start(controls, False, False, 0)

        self.window.connect("key-press-event", self.on_key)
        self.window.connect("destroy", lambda *_: setattr(self, "alive", False))
        self.window.show_all()
        self.refresh()
        GLib.timeout_add(650, self.refresh)
        # If the user never enters the popup, dismiss it after a short grace period.
        self.schedule_close()

    def button(self, text: str, callback, extra_class: str | None = None):
        b = Gtk.Button(label=text)
        b.get_style_context().add_class("control")
        if extra_class:
            b.get_style_context().add_class(extra_class)
        b.connect("clicked", lambda *_: callback())
        return b

    def schedule_close(self) -> None:
        if not self.alive or self.pointer_inside_card:
            return
        if self.close_timer is not None:
            try:
                GLib.source_remove(self.close_timer)
            except Exception:
                pass
        self.close_timer = GLib.timeout_add(AUTO_CLOSE_MS, self.close_if_pointer_outside)

    def cancel_scheduled_close(self) -> None:
        if self.close_timer is not None:
            try:
                GLib.source_remove(self.close_timer)
            except Exception:
                pass
            self.close_timer = None

    def close_if_pointer_outside(self) -> bool:
        self.close_timer = None
        if self.alive and not self.pointer_inside_card:
            self.close()
        return False

    def on_card_enter(self, _widget, event) -> bool:
        # Ignore crossings between the card eventbox and its child controls.
        if getattr(event, "mode", Gdk.CrossingMode.NORMAL) != Gdk.CrossingMode.NORMAL:
            return False
        if getattr(event, "detail", None) == Gdk.NotifyType.INFERIOR:
            return False
        self.pointer_inside_card = True
        self.cancel_scheduled_close()
        return False

    def on_card_leave(self, _widget, event) -> bool:
        # A leave with INFERIOR detail only means the pointer moved onto a child button.
        if getattr(event, "mode", Gdk.CrossingMode.NORMAL) != Gdk.CrossingMode.NORMAL:
            return False
        if getattr(event, "detail", None) == Gdk.NotifyType.INFERIOR:
            return False
        self.pointer_inside_card = False
        self.schedule_close()
        return False

    def command(self, action: str) -> tuple[bool, str]:
        if not shutil.which("playerctl"):
            return False, "playerctl is not installed (sudo pacman -S playerctl)"
        self.player = current_player()
        if not self.player:
            return False, "Nothing is playing. Start a player that supports MPRIS."
        return run(["playerctl", "--player", self.player, *action.split()])

    def do_previous(self) -> None:
        ok, detail = self.command("previous")
        if not ok and detail:
            self.state.set_text(detail[:90])
        GLib.timeout_add(300, self.refresh)

    def do_next(self) -> None:
        ok, detail = self.command("next")
        if not ok and detail:
            self.state.set_text(detail[:90])
        GLib.timeout_add(300, self.refresh)

    def do_play_pause(self) -> None:
        ok, detail = self.command("play-pause")
        if not ok and detail:
            self.state.set_text(detail[:90])
        GLib.timeout_add(300, self.refresh)

    def do_repeat(self) -> None:
        player = current_player()
        if not player:
            self.state.set_text("Nothing to repeat")
            return
        ok, current = run(["playerctl", "--player", player, "loop"])
        current = current.strip().capitalize() if ok else "None"
        modes = {"None": "Track", "Track": "Playlist", "Playlist": "None", "Off": "Track"}
        next_mode = modes.get(current, "Track")
        ok, detail = run(["playerctl", "--player", player, "loop", next_mode])
        if not ok:
            self.state.set_text("This player may not support repeat mode")
        GLib.timeout_add(250, self.refresh)

    def refresh(self) -> bool:
        if not self.alive:
            return False
        self.player = current_player()
        if not shutil.which("playerctl"):
            self.title.set_text("playerctl is not installed")
            self.subtitle.set_text("Run: sudo pacman -S playerctl")
            self.state.set_text("Media controls unavailable")
            for button in (self.prev, self.play, self.next, self.repeat):
                button.set_sensitive(False)
            return True
        if not self.player:
            self.title.set_text("Nothing playing")
            self.subtitle.set_text("Start Spotify, Firefox, VLC or another MPRIS player")
            self.state.set_text("Waiting for a media player")
            for button in (self.prev, self.play, self.next, self.repeat):
                button.set_sensitive(False)
            self.play.set_label("▶ Play")
            self.repeat.set_label("↻ Repeat: Off")
            return True
        track = value(self.player, "title") or "Unknown track"
        artist = value(self.player, "artist")
        player_name = value(self.player, "playerName") or self.player
        current_status = status(self.player)
        self.title.set_text(track)
        self.subtitle.set_text((artist + " · " if artist else "") + player_name)
        self.state.set_text("Playing" if current_status == "Playing" else "Paused" if current_status == "Paused" else current_status)
        for button in (self.prev, self.play, self.next, self.repeat):
            button.set_sensitive(True)
        self.play.set_label("⏸ Pause" if current_status == "Playing" else "▶ Play")
        ok, mode = run(["playerctl", "--player", self.player, "loop"])
        mode = mode.strip().capitalize() if ok else "Off"
        self.repeat.set_label("↻ Repeat: " + (mode if mode in ("Track", "Playlist") else "Off"))
        return True

    def on_outside_click(self, _widget, _event) -> bool:
        self.close()
        return True

    def on_key(self, _window, event) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def close(self) -> None:
        if self.alive:
            self.cancel_scheduled_close()
            self.alive = False
            self.window.destroy()


if __name__ == "__main__":
    if not shutil.which("playerctl"):
        try:
            subprocess.Popen(["notify-send", "Media controls", "Install playerctl: sudo pacman -S playerctl"])
        except OSError:
            pass
    app = MediaControls()
    Gtk.main()
