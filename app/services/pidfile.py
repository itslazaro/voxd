"""Runtime pidfile helpers for single-instance signalling.

The GUI/daemon writes its PID on startup; the `voxd --toggle` command reads it
and delivers SIGUSR1/SIGUSR2 so a GNOME keybinding can drive the running
instance without needing systemd.
"""

from __future__ import annotations

import logging
import os
import signal
from pathlib import Path

from app.core.config import user_state_dir

log = logging.getLogger(__name__)

PIDFILE_NAME = "voxd.pid"


def pidfile() -> Path:
    return user_state_dir() / PIDFILE_NAME


def write_pidfile() -> Path:
    path = pidfile()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(os.getpid()), encoding="utf-8")
    return path


def remove_pidfile() -> None:
    try:
        pidfile().unlink(missing_ok=True)
    except OSError:
        log.warning("Could not remove pidfile", exc_info=True)


def read_pid() -> int | None:
    path = pidfile()
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _signal_exists(sig: int) -> bool:
    return hasattr(signal, "Signals") and sig in signal.Signals or sig in (1, 2, 15)


def send_toggle(force_start: bool = False, force_stop: bool = False) -> bool:
    """Signal a running VOXD instance (if any). Returns True if signalled."""
    pid = read_pid()
    if not pid:
        log.info("No running VOXD instance (pidfile missing)")
        return False
    try:
        sig = signal.SIGUSR1
        if force_stop:
            sig = signal.SIGUSR2
        elif force_start:
            sig = signal.SIGUSR1
        os.kill(pid, sig)
        log.info("Signalled VOXD pid=%s with %s", pid, sig)
        return True
    except ProcessLookupError:
        log.warning("VOXD pid %s is not running; removing stale pidfile", pid)
        remove_pidfile()
        return False
    except PermissionError:
        log.warning("No permission to signal VOXD pid %s", pid)
        return False
    except (AttributeError, OSError) as exc:
        log.warning("Could not signal VOXD: %s", exc)
        return False
