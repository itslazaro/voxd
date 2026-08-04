"""Tests for the platform login-autostart manager."""

from __future__ import annotations

import platform

import pytest

from app.services import autostart

pytestmark = pytest.mark.skipif(
    platform.system() == "Windows",
    reason="autostart writes registry on Windows; tested on Linux only",
)


def test_enable_creates_desktop_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    assert autostart.autostart_enabled() is False

    assert autostart.enable_autostart() is True
    assert autostart.autostart_enabled() is True

    entry = autostart._linux_autostart_file()
    assert entry.exists()
    text = entry.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    assert "Name=VOXD" in text
    assert "Terminal=false" in text
    assert "Exec=" in text


def test_disable_removes_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    autostart.enable_autostart()
    assert autostart.autostart_enabled() is True

    assert autostart.disable_autostart() is True
    assert autostart.autostart_enabled() is False
    assert not autostart._linux_autostart_file().exists()


def test_disable_when_already_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    # Disabling with no entry should succeed and stay False.
    assert autostart.disable_autostart() is True
    assert autostart.autostart_enabled() is False
