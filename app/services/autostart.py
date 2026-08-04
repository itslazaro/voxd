"""Platform autostart management.

Linux: writes a .desktop file into ~/.config/autostart so the system launches
VOXD at login. Windows: writes a HKCU Run registry entry.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
import textwrap
from pathlib import Path

log = logging.getLogger(__name__)

DESKTOP_ENTRY_NAME = "voxd.desktop"
WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WIN_RUN_VALUE = "VOXD"


def _launcher_command() -> str:
    """Command the autostart entry should run.

    Prefers a `voxd` on PATH (installed); falls back to the current interpreter
    (source/dev checkout).
    """
    import shutil

    if shutil.which("voxd"):
        return "voxd gui"
    # sys.executable might be a venv python; use it with the module.
    return f'"{sys.executable}" -m app.main gui'


def _linux_autostart_file() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart" / DESKTOP_ENTRY_NAME


def _entry_contents() -> str:
    return textwrap.dedent(
        f"""\
        [Desktop Entry]
        Type=Application
        Name=VOXD
        Comment=Local-first AI voice dictation
        Exec={_launcher_command()}
        Icon=voxd
        Terminal=false
        X-GNOME-Autostart-enabled=true
        """
    )


def autostart_enabled() -> bool:
    """Return True if VOXD is set to launch at login on this platform."""
    if platform.system() == "Windows":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY) as key:
                winreg.QueryValueEx(key, WIN_RUN_VALUE)
                return True
        except FileNotFoundError:
            return False
        except OSError:
            return False
    return _linux_autostart_file().exists()


def enable_autostart() -> bool:
    """Register VOXD to start at login. Returns True on success."""
    if platform.system() == "Windows":
        try:
            import winreg

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY) as key:
                winreg.SetValueEx(key, WIN_RUN_VALUE, 0, winreg.REG_SZ, _launcher_command())
            return True
        except OSError as exc:
            log.error("Failed to write autostart registry key: %s", exc)
            return False

    path = _linux_autostart_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_entry_contents(), encoding="utf-8")
        log.info("Autostart enabled: %s", path)
        return True
    except OSError as exc:
        log.error("Failed to write autostart entry: %s", exc)
        return False


def disable_autostart() -> bool:
    """Remove the VOXD login autostart registration. Returns True on success."""
    if platform.system() == "Windows":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, WIN_RUN_VALUE)
            return True
        except FileNotFoundError:
            return True  # already absent
        except OSError as exc:
            log.error("Failed to remove autostart registry key: %s", exc)
            return False

    path = _linux_autostart_file()
    try:
        if path.exists():
            path.unlink()
        log.info("Autostart disabled: %s", path)
        return True
    except OSError as exc:
        log.error("Failed to remove autostart entry: %s", exc)
        return False
