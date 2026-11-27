"""Words a window shows, in English and German.

A window takes the language of the application that opens it (``--language``), else that
of the system.  Every tool registers its own words (:func:`register`); a key registered
twice must mean the same both times.
"""

from __future__ import annotations

import locale
import os
from collections.abc import Mapping

LANGUAGES = ("en", "de")
WORDS: dict[str, tuple[str, str]] = {}  # key: (English, German), every tool's


def register(words: Mapping[str, tuple[str, str]]) -> None:
    """Add a tool's words; a key registered twice must have the same words."""
    for key, pair in words.items():
        if key in WORDS and WORDS[key] != tuple(pair):
            raise ValueError(f"the word {key} is registered with other words already")
        WORDS[key] = (pair[0], pair[1])


def system_language() -> str:
    """The language of the system: German where it is set so, else English."""
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "")
        if value and value not in ("C", "POSIX"):
            return "de" if value.lower().startswith("de") else "en"
    current = locale.getlocale()[0] or ""
    return "de" if current.lower().startswith("de") else "en"


class Words:
    """The words of one language: ``words("page", number=2)``."""

    def __init__(self, language: str | None = None) -> None:
        self.language = language if language in LANGUAGES else system_language()

    def __call__(self, key: str, **values: object) -> str:
        """The word ``key`` in this language, its placeholders filled in."""
        english, german = WORDS[key]
        return (german if self.language == "de" else english).format(**values)
