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
        sig_start = getattr(signal, "SIGUSR1", None)
        sig_stop = getattr(signal, "SIGUSR2", None)
        if sig_start is None or sig_stop is None:
            log.warning("SIGUSR1/SIGUSR2 unavailable on this platform; signals disabled")
            self._enable_signals = False
            return
        signal.signal(sig_start, self._on_signal)
        signal.signal(sig_stop, self._on_signal)
        self._installed = True
        log.info("Signal handlers installed (SIGUSR1=start, SIGUSR2=stop)")

    def _on_signal(self, signum, frame) -> None:
        sig_start = getattr(signal, "SIGUSR1", None)
        if signum == sig_start:
            log.info("SIGUSR1 → start dictation")
            self.engine.start_recording()
        else:
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
