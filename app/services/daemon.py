"""Background daemon running the dictation engine.

Two operational modes:
  * signal mode  (Linux/systemd)  — SIGUSR1 starts, SIGUSR2 stops
  * inline mode  (GUI/other)      — direct method calls
"""

from __future__ import annotations

import logging
import signal
import sys
import time

from app.core.engine import DictationEngine

log = logging.getLogger(__name__)


class Daemon:
    """Long-lived owner of the DictationEngine.

    In signal mode this daemon integrates with the existing GNOME/Wayland
    trigger path (custom keybinding → start/stop scripts → SIGUSR1/SIGUSR2),
    so the working prototype behavior is preserved.
    """

    def __init__(self, engine: DictationEngine, enable_signals: bool | None = None):
        self.engine = engine
        if enable_signals is None:
            enable_signals = sys.platform.startswith("linux")
        self._enable_signals = enable_signals
        self._installed = False

    def install(self) -> None:
        """Install signal handlers if enabled (idempotent)."""
        if not self._enable_signals or self._installed:
            return
        for sig in (signal.SIGUSR1, signal.SIGUSR2):
            signal.signal(sig, self._on_signal)
        self._installed = True
        log.info("Signal handlers installed (SIGUSR1=start, SIGUSR2=stop)")

    def _on_signal(self, signum, frame) -> None:
        if signum == signal.SIGUSR1:
            log.info("SIGUSR1 → start dictation")
            self.engine.start_recording()
        elif signum == signal.SIGUSR2:
            log.info("SIGUSR2 → stop dictation")
            self.engine.stop_recording()

    def run(self) -> None:
        """Block forever, servicing the engine. Used by the daemon entrypoint."""
        self.install()
        log.info("VOXD daemon running (pid=%s)", __import__("os").getpid())
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("Shutting down")
            self.engine.shutdown()

    def serve_inline(self) -> None:
        """Non-blocking setup for embedding in a GUI process."""
        self.install()
