"""Open the window on a chain and wait until it closes (``docrepro edit``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from docrepro.chain import Chain
from docrepro.gui.window import ChainWindow
from docrepro.gui.words import Words


def edit(chain: Chain, out: Path, language: str | None = None,
         self_test: bool = False) -> tuple[str, dict[str, Any]]:
    """Show the window on ``chain``, brought to the front (it is opened from another
    program), and return how it closed ("applied", "saved" or "cancelled") and the
    configuration documents of its steps; the steps the person left in use are the
    chain's from then on (``chain.used``).  What the steps make while the window is open
    goes into the hidden working folder inside ``out`` and is removed when it closes.
    With ``self_test`` it goes through once by itself (the check of the standalone
    program)."""
    app = QApplication.instance() or QApplication(["docrepro"])
    app.setApplicationName("docrepro")
    with chain.working(out) as work:
        window = ChainWindow(chain, work / "edit", Words(language), synchronous=self_test)
        try:
            window.show()
            window.raise_()
            window.activateWindow()
            if self_test:
                QTimer.singleShot(0, window.self_test)
            app.exec()
            outcome = window.outcome or "cancelled"
            configs = window.configs() if outcome != "cancelled" else {}
            if outcome != "cancelled":
                chain.used = set(window.used)
        finally:
            window.release()
    return outcome, configs
