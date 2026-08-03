"""Tests for the text cleanup layer."""

import pytest

from app.core.cleaner import clean_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", ""),
        ("   hello world   ", "Hello world."),
        ("this is a test", "This is a test."),
        ("first sentence. second sentence", "First sentence. Second sentence."),
        ("already has period.", "Already has period."),
        ("question?", "Question?"),
        ("tab\tand\nnewline", "Tab and newline."),
    ],
)
def test_clean_text(raw, expected):
    assert clean_text(raw) == expected


def test_disable_all_options():
    assert clean_text("a\nb", capitalize=False, add_period=False, collapse_spaces=False) == "a\nb"


def test_collapse_spaces_only():
    assert clean_text("a   b", capitalize=False, add_period=False) == "a b"


def test_capitalize_only():
    assert clean_text("a. b", collapse_spaces=False, add_period=False) == "A. B"
