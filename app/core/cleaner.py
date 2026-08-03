"""Text cleanup layer: normalize Whisper output before injection."""

from __future__ import annotations

import re


def clean_text(
    text: str,
    *,
    capitalize: bool = True,
    add_period: bool = True,
    collapse_spaces: bool = True,
) -> str:
    """Clean raw transcription text for safe, natural typing.

    Steps (each configurable):
      - strip surrounding whitespace
      - collapse runs of whitespace/newlines into single spaces
      - capitalize the first letter of each sentence
      - ensure the final sentence ends with a terminal punctuation mark
    """
    if not text:
        return ""

    text = text.strip()

    if collapse_spaces:
        text = re.sub(r"\s+", " ", text)

    if capitalize:
        text = _capitalize_sentences(text)

    if add_period:
        if text and text[-1] not in ".!?;:":
            text += "."

    return text


_SENTENCE_RE = re.compile(r"(^|[.!?;:]\s+)([a-z])")


def _capitalize_sentences(text: str) -> str:
    """Capitalize the first letter after sentence-terminating punctuation."""
    return _SENTENCE_RE.sub(lambda m: m.group(1) + m.group(2).upper(), text)
