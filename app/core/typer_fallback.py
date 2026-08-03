"""Fallback typing engines that require optional third-party packages."""

from __future__ import annotations

import time

from app.core.typer import BaseTyper, TypingError


class PyAutoGUITyper(BaseTyper):
    """Type text via pyautogui (used on Windows/macOS as a fallback)."""

    engine_name = "pyautogui"

    def __init__(self):
        try:
            import pyautogui
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise TypingError("pyautogui is not installed") from exc
        self._pyautogui = pyautogui
        # Avoid pyautogui's emergency failsafe (mouse to corner) interrupting.
        try:
            pyautogui.FAILSAFE = False
        except Exception:  # noqa: BLE001
            pass

    def type_text(self, text: str) -> None:
        if not text:
            return
        self._pyautogui.write(text)
        time.sleep(0.01)
