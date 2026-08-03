"""Cross-platform text injection.

Linux/Wayland: ydotool type.
Windows: Windows SendInput (ctypes) or pyautogui.
macOS (future): pyautogui / Quartz.
"""

from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import time


class TypingError(Exception):
    """Raised when text cannot be injected."""


class BaseTyper:
    engine_name = "base"

    def type_text(self, text: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class YdotoolTyper(BaseTyper):
    engine_name = "ydotool"

    def __init__(self, socket_path: str | None = None):
        self.socket_path = socket_path
        self._bin = shutil.which("ydotool")

    def type_text(self, text: str) -> None:
        if not text:
            return
        if not self._bin:
            raise TypingError("ydotool not found on PATH")
        env = os.environ.copy()
        if self.socket_path:
            env["YDOTOOL_SOCKET"] = self.socket_path
        try:
            result = subprocess.run(
                [self._bin, "type", text],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise TypingError("ydotool type timed out") from exc
        if result.returncode != 0:
            raise TypingError(f"ydotool failed: {result.stderr.strip()}")


class WindowsSendInputTyper(BaseTyper):
    """Type text using the Windows SendInput API (no third-party deps)."""

    engine_name = "sendinput"

    # ctypes bindings
    _user32 = ctypes.windll.user32 if platform.system() == "Windows" else None
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004

    def type_text(self, text: str) -> None:
        if not text:
            return
        if self._user32 is None:
            raise TypingError("Windows SendInput unavailable on this platform")
        for ch in text:
            self._press_unicode(ord(ch))
            time.sleep(0.001)

    def _press_unicode(self, code: int) -> None:
        class KeyInput(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
            ]

        class Input(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_ulong),
                ("ki", KeyInput),
            ]

        down = Input(
            type=self.INPUT_KEYBOARD,
            ki=KeyInput(
                wVk=0,
                wScan=code,
                dwFlags=self.KEYEVENTF_UNICODE,
                time=0,
                dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0)),
            ),
        )
        up = Input(
            type=self.INPUT_KEYBOARD,
            ki=KeyInput(
                wVk=0,
                wScan=code,
                dwFlags=self.KEYEVENTF_UNICODE | self.KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0)),
            ),
        )
        self._user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(down))
        self._user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))


def create_typer(engine: str = "auto", socket_path: str | None = None) -> BaseTyper:
    """Select a typer based on the platform and configured engine."""
    if platform.system() == "Windows":
        if engine in ("auto", "sendinput", "pyautogui"):
            try:
                return WindowsSendInputTyper()
            except Exception:  # noqa: BLE001
                from app.core.typer_fallback import PyAutoGUITyper

                return PyAutoGUITyper()
    elif platform.system() == "Linux":
        if engine in ("auto", "ydotool"):
            return YdotoolTyper(socket_path=socket_path)

    raise TypingError(f"No typing engine available for engine={engine!r}")
