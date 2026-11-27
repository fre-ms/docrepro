"""The window's building blocks: words in two languages from every tool's register; the
page view and work off the window's thread."""

from __future__ import annotations

import pytest

from doccor.gui import words


def test_words_from_the_register() -> None:
    """A tool's words in both languages; a key cannot mean two things."""
    words.register({"page_n": ("Page {number}", "Seite {number}")})
    assert words.Words("de")("page_n", number=3) == "Seite 3"
    assert words.Words("en")("page_n", number=3) == "Page 3"
    assert words.Words("xx").language in words.LANGUAGES
    with pytest.raises(ValueError):
        words.register({"page_n": ("Sheet {number}", "Blatt {number}")})


def test_page_view_and_worker() -> None:
    """The page view shows an image with boxes and corners; work runs and reports."""
    pytest.importorskip("PySide6")
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication

    from doccor.gui.view import PageView
    from doccor.gui.worker import Worker

    QApplication.instance() or QApplication(["doccor"])
    image = QImage(200, 300, QImage.Format.Format_RGB32)
    image.fill(QColor(255, 255, 255))
    from PySide6.QtCore import QBuffer, QIODevice

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    view = PageView()
    view.display(bytes(buffer.data()), [((10, 10, 50, 30), QColor(230, 165, 0), "word")])
    view.show_corners([(5, 5), (100, 5), (100, 150), (5, 150)])
    moved = []
    view.corners_moved.connect(moved.append)
    view.move_corner(2, 120, 160)
    assert moved and moved[0][2] == pytest.approx((120, 160))
    results = []
    worker = Worker(lambda: 6 * 7, inline=True)
    worker.done.connect(results.append)
    worker.go()
    assert results == [42]
