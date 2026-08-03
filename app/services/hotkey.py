"""Hotkey registration.

Linux/Wayland: relies on a GNOME custom keybinding wired to `voxd --toggle`;
there is no reliable global key grab on Wayland, so we only document/verify the
binding here (see scripts/install-gnome-keybinding.sh).

Windows: registers a true global hotkey with pynput.
"""

from __future__ import annotations

import logging
import platform
import subprocess
import threading

log = logging.getLogger(__name__)


class HotkeyService:
    """Manage platform hotkey registration and the GNOME binding helper."""

    def __init__(self, on_toggle=None, key: str = "f8"):
        self._on_toggle = on_toggle
        self._key = key
        self._listener = None
        self._thread: threading.Thread | None = None

    # -- Linux / Wayland ------------------------------------------------

    @staticmethod
    def install_gnome_keybinding(binding: str = "<Super>v", command: str = "voxd --toggle") -> bool:
        """Register a GNOME Shell custom keybinding via gsettings.

        Returns True on success, False if GNOME/gsettings is unavailable.
        """
        schema = "org.gnome.settings-daemon.plugins.media-keys"
        path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voxd/"
        try:
            key = f"custom-keybindings/{path}"
            current = subprocess.run(
                ["gsettings", "get", schema, "custom-keybindings"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            bindings: list = []
            if current not in ("@as []", "[]", ""):
                import ast

                try:
                    bindings = list(ast.literal_eval(current))
                except (ValueError, SyntaxError):
                    bindings = []
            if path not in bindings:
                bindings.append(path)
            subprocess.run(
                ["gsettings", "set", schema, "custom-keybindings", repr(bindings)],
                check=True,
                capture_output=True,
            )
            subprocess.run(["gsettings", "set", schema, key + "name", "VOXD Dictate"], check=True)
            subprocess.run(["gsettings", "set", schema, key + "command", command], check=True)
            subprocess.run(["gsettings", "set", schema, key + "binding", binding], check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            log.warning("No GNOME keybinding tooling (Wayland global hotkeys unsupported)")
            return False

    # -- Windows / other ------------------------------------------------

    def start(self) -> None:
        """Start listening for global hotkeys (Windows uses pynput)."""
        if self._listener is not None:
            return
        if platform.system() != "Windows":
            # Wayland/other: no global hook; rely on GNOME binding / tray.
            log.info("Global hotkey unsupported on %s; using tray + OS binding", platform.system())
            return
        try:
            from pynput import keyboard
        except ImportError:  # pragma: no cover
            log.warning("pynput not available; hotkeys disabled")
            return

        key = self._parse_key(self._key)
        self._listener = keyboard.Listener(on_press=lambda k: self._press(k, key))
        self._listener.start()
        log.info("Global hotkey listening on %s", self._key)

    def _press(self, pressed, wanted) -> None:
        if pressed == wanted and self._on_toggle:
            self._on_toggle()

    @staticmethod
    def _parse_key(spec: str):
        from pynput import keyboard

        return getattr(keyboard.Key, spec, None) or spec

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:  # noqa: BLE001
                pass
            self._listener = None
