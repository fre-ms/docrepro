"""The window's building blocks are tested without a screen."""

import os


def pytest_configure() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
