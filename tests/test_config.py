"""Tests for configuration loading."""

import pytest

from app.core.config import ConfigError, _deep_merge, load_config


def test_load_defaults(tmp_path):
    default = tmp_path / "default.yaml"
    default.write_text(
        "model:\n  path: ''\n  language: en\naudio:\n  sample_rate: 16000\n",
        encoding="utf-8",
    )
    user = tmp_path / "config.yaml"
    user.write_text("audio:\n  sample_rate: 48000\n", encoding="utf-8")

    conf = load_config(default=default, user=user)
    assert conf["audio"]["sample_rate"] == 48000
    assert conf["model"]["language"] == "en"
    assert conf["model"]["path"] == ""


def test_deep_merge_keeps_defaults():
    base = {"a": {"b": 1, "c": 2}, "keep": "x"}
    override = {"a": {"b": 9}}
    merged = _deep_merge(base, override)
    assert merged["a"]["b"] == 9
    assert merged["a"]["c"] == 2
    assert merged["keep"] == "x"
    # Original must be untouched
    assert base["a"]["b"] == 1


def test_unknown_top_level_rejected(tmp_path):
    default = tmp_path / "default.yaml"
    default.write_text("model: {}\nbogus_section:\n  x: 1\n", encoding="utf-8")
    user = tmp_path / "config.yaml"
    user.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(default=default, user=user)


def test_invalid_sample_rate_rejected(tmp_path):
    default = tmp_path / "default.yaml"
    default.write_text("audio:\n  sample_rate: -5\n", encoding="utf-8")
    user = tmp_path / "config.yaml"
    user.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(default=default, user=user)


def test_missing_default_config_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(default=tmp_path / "nope.yaml", user=tmp_path / "c.yaml")
