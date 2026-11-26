"""The window of docrepro: the whole way in one window (``docrepro edit``), a tab for every
step whose tool is installed.  Needs PySide6 (the extra "gui")."""

from __future__ import annotations

import importlib.util


def available() -> bool:
    """True when PySide6 is installed; it is not loaded for that."""
    return importlib.util.find_spec("PySide6") is not None
