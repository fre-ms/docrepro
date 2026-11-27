"""The window's building blocks, shared by the tools' windows: the page view, work off the
window's thread, and words in two languages.  Needs PySide6 (the extra "gui")."""

from __future__ import annotations

import importlib.util


def available() -> bool:
    """True when PySide6 is installed; it is not loaded for that."""
    return importlib.util.find_spec("PySide6") is not None
