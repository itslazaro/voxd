"""Configuration loading, merging, and platform path resolution for VOXD."""

from __future__ import annotations

import copy
import os
import platform
import sys
from pathlib import Path
from typing import Any

import yaml

from app import APP_NAME

DEFAULT_CONFIG_NAME = "default.yaml"

# Config keys the user may override (whitelist of known top-level sections).
_KNOWN_TOP_LEVEL = {
    "version",
    "model",
    "whisper",
    "audio",
    "hotkey",
    "typing",
    "cleanup",
    "app",
}


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or validated."""


def project_root() -> Path:
    """Absolute path to the project / install root."""
    return Path(__file__).resolve().parent.parent.parent


def default_config_path() -> Path:
    """Path to the bundled config/default.yaml, searching known install layouts."""
    root = project_root()
    candidates = [
        root / "config" / DEFAULT_CONFIG_NAME,          # source tree / one-folder build
        root / "config-default.yaml",                    # AppImage layout
        Path("/etc") / APP_NAME.lower() / DEFAULT_CONFIG_NAME,  # deb layout
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    # Fall back to the canonical path so the error message is meaningful.
    return root / "config" / DEFAULT_CONFIG_NAME


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def _xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))


def user_config_dir() -> Path:
    """User-writable config directory (config.yaml lives here)."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    return _xdg_config_home() / APP_NAME


def user_data_dir() -> Path:
    """User-writable data directory (models, whisper.cpp install)."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME
    return _xdg_data_home() / APP_NAME


def user_state_dir() -> Path:
    """User-writable state directory (logs, temp)."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME
    return _xdg_state_home() / APP_NAME


def user_config_file() -> Path:
    return user_config_dir() / "config.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into a deep copy of base."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key not in result:
            result[key] = copy.deepcopy(value)
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _validate(conf: dict) -> None:
    for key in conf:
        if key not in _KNOWN_TOP_LEVEL:
            raise ConfigError(f"Unknown top-level config key: {key!r}")
    rate = conf.get("audio", {}).get("sample_rate")
    if rate and (not isinstance(rate, int) or rate <= 0):
        raise ConfigError("audio.sample_rate must be a positive integer")


def load_config(default: Path | None = None, user: Path | None = None) -> dict:
    """Load default.yaml merged with the user's config.yaml (if present)."""
    default = default or default_config_path()
    user = user or user_config_file()

    if not default.exists():
        raise ConfigError(f"Default config not found: {default}")

    with default.open("r", encoding="utf-8") as fh:
        merged = yaml.safe_load(fh) or {}

    if user.exists():
        with user.open("r", encoding="utf-8") as fh:
            user_conf = yaml.safe_load(fh) or {}
        merged = _deep_merge(merged, user_conf)

    _validate(merged)
    return merged


def save_user_config(conf: dict, path: Path | None = None) -> Path:
    """Persist the given config to the user config.yaml, preserving defaults."""
    path = path or user_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(conf, fh, sort_keys=False, allow_unicode=True)
    return path


def platform_key() -> str:
    """Return 'linux', 'windows', or 'macos'."""
    sysname = platform.system().lower()
    if sysname.startswith("linux"):
        return "linux"
    if sysname.startswith("win"):
        return "windows"
    if sysname.startswith("darwin"):
        return "macos"
    return sysname


def resolve(conf: dict, section: str, key: str, default: Any = None) -> Any:
    """Safely read a nested config value."""
    return conf.get(section, {}).get(key, default)


def platform_specific(conf: dict, section: str) -> Any:
    """Return a per-platform value under a section.

    Sections may contain a 'default' plus 'linux'/'windows'/'macos' keys.
    """
    data = conf.get(section, {})
    if isinstance(data, dict):
        return data.get(platform_key(), data.get("default"))
    return data
