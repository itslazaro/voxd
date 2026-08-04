"""Tests for the pidfile single-instance signalling helpers."""

from __future__ import annotations

import subprocess
import sys
import time

from app.services import pidfile


def test_write_read_remove_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(pidfile, "user_state_dir", lambda: tmp_path)
    assert pidfile.read_pid() is None

    path = pidfile.write_pidfile()
    assert path == tmp_path / pidfile.PIDFILE_NAME
    assert path.exists()
    assert pidfile.read_pid() == __import__("os").getpid()

    pidfile.remove_pidfile()
    assert not path.exists()
    assert pidfile.read_pid() is None


def test_send_toggle_no_instance(tmp_path, monkeypatch):
    monkeypatch.setattr(pidfile, "user_state_dir", lambda: tmp_path)
    assert pidfile.send_toggle() is False
    assert pidfile.send_toggle(force_start=True) is False


def test_send_toggle_stale_pidfile_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(pidfile, "user_state_dir", lambda: tmp_path)
    # A PID that is very unlikely to exist.
    bogus = 999_999
    (tmp_path / pidfile.PIDFILE_NAME).write_text(str(bogus), encoding="utf-8")
    assert pidfile.send_toggle(force_start=True) is False
    # Stale pidfile should have been cleaned up.
    assert not (tmp_path / pidfile.PIDFILE_NAME).exists()


def test_send_toggle_signals_running_process(tmp_path, monkeypatch):
    monkeypatch.setattr(pidfile, "user_state_dir", lambda: tmp_path)
    code = (
        "import signal, time\n"
        "signal.signal(signal.SIGUSR1, lambda *a: exit(0))\n"
        "signal.signal(signal.SIGUSR2, lambda *a: exit(42))\n"
        "while True:\n"
        "    time.sleep(0.05)\n"
    )
    child = subprocess.Popen([sys.executable, "-c", code])
    try:
        # Wait for child to install handlers.
        time.sleep(0.4)
        (tmp_path / pidfile.PIDFILE_NAME).write_text(str(child.pid), encoding="utf-8")

        assert pidfile.send_toggle(force_start=True) is True
        assert child.wait(timeout=5) == 0
    finally:
        child.terminate()
        child.wait(timeout=5)


def test_send_toggle_stop_signals_running_process(tmp_path, monkeypatch):
    monkeypatch.setattr(pidfile, "user_state_dir", lambda: tmp_path)
    code = (
        "import signal, time\n"
        "signal.signal(signal.SIGUSR1, lambda *a: exit(0))\n"
        "signal.signal(signal.SIGUSR2, lambda *a: exit(7))\n"
        "while True:\n"
        "    time.sleep(0.05)\n"
    )
    child = subprocess.Popen([sys.executable, "-c", code])
    try:
        time.sleep(0.4)
        (tmp_path / pidfile.PIDFILE_NAME).write_text(str(child.pid), encoding="utf-8")
        assert pidfile.send_toggle(force_stop=True) is True
        assert child.wait(timeout=5) == 7
    finally:
        child.terminate()
        child.wait(timeout=5)
