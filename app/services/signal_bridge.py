"""Qt-aware signal bridge for out-of-process dictation triggers.

Python signal handlers installed with :func:`signal.signal` do **not** run
while the main thread is blocked inside Qt's C++ event loop
(``QApplication.exec()``).  VOXD relies on ``SIGUSR1``/``SIGUSR2`` to start
and stop dictation from an external trigger (a GNOME custom keybinding running
``voxd toggle``), so in GUI mode we cannot rely on plain handlers.

This bridge uses :func:`signal.set_wakeup_fd` paired with a
:class:`QSocketNotifier`: the low-level wakeup writes the signal number as a
single byte to a socketpair, the notifier wakes the Qt event loop, and we
dispatch the start/stop action on the Qt thread.

For the headless ``voxd daemon`` path (no Qt), plain :func:`signal.signal`
handlers work fine because the blocking ``time.sleep()`` loop yields to the
interpreter; see :class:`app.services.daemon.Daemon`.
"""

from __future__ import annotations

import logging
import signal
import socket

log = logging.getLogger(__name__)


class QtSignalBridge:
    """Deliver SIGUSR1/SIGUSR2 to a running Qt application instance."""

    def __init__(self, on_start, on_stop):
        from PySide6.QtCore import QSocketNotifier

        self._on_start = on_start
        self._on_stop = on_stop
        self._r, self._w = socket.socketpair()
        self._r.setblocking(False)
        self._w.setblocking(False)
        self._notifier = QSocketNotifier(self._r.fileno(), QSocketNotifier.Read)
        self._notifier.activated.connect(self._on_ready)
        self._prev_wakeup: int | None = None
        self._installed = False

    def install(self) -> None:
        """Install the bridge. Idempotent."""
        if self._installed:
            return
        sig_start = getattr(signal, "SIGUSR1", None)
        sig_stop = getattr(signal, "SIGUSR2", None)
        if sig_start is None or sig_stop is None:
            log.warning("SIGUSR1/SIGUSR2 unavailable on this platform; bridge disabled")
            return
        # No-op Python handlers are required so CPython installs the wakeup
        # write for these signals. Dispatch happens via the notifier, not here.
        signal.signal(sig_start, lambda *_: None)
        signal.signal(sig_stop, lambda *_: None)
        try:
            self._prev_wakeup = signal.set_wakeup_fd(self._w.fileno())
        except (ValueError, OSError) as exc:
            log.warning("Could not set wakeup fd; signal bridge inactive: %s", exc)
            return
        self._notifier.setEnabled(True)
        self._installed = True
        log.info("Qt signal bridge installed (SIGUSR1=start, SIGUSR2=stop)")

    def _on_ready(self) -> None:
        """Called by the Qt event loop when a byte arrives on the wakeup socket."""
        try:
            data = self._r.recv(1024)
        except BlockingIOError:
            return
        except OSError:
            return
        sig_start = getattr(signal, "SIGUSR1", None)
        sig_stop = getattr(signal, "SIGUSR2", None)
        for byte in data:
            if byte == sig_start:
                log.info("SIGUSR1 → start dictation")
                try:
                    self._on_start()
                except Exception:  # noqa: BLE001
                    log.exception("start handler raised")
            elif byte == sig_stop:
                log.info("SIGUSR2 → stop dictation")
                try:
                    self._on_stop()
                except Exception:  # noqa: BLE001
                    log.exception("stop handler raised")

    def remove(self) -> None:
        """Tear down the bridge and restore the previous wakeup fd."""
        if not self._installed:
            return
        self._notifier.setEnabled(False)
        try:
            if self._prev_wakeup is not None:
                signal.set_wakeup_fd(self._prev_wakeup)
        except (ValueError, OSError):
            log.warning("Could not restore wakeup fd", exc_info=True)
        self._installed = False
        for sock in (self._r, self._w):
            try:
                sock.close()
            except OSError:
                pass
