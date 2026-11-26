"""The joined window, driven without a screen: optdoc's tab and ocrdoc's tabs on one
document; after a change in optdoc, a later tab gets optdoc's new PDF, and a person's
correction stays where the page did not move and goes where it did, with the page named
in the status line."""

from __future__ import annotations

from pathlib import Path

import pytest
from ocrdoc import ocr as ocrlib

from docrepro.chain import Chain
from tests.synthetic import scan

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

from docrepro.gui.window import ChainWindow  # noqa: E402
from docrepro.gui.words import Words  # noqa: E402

needs_engine = pytest.mark.skipif(not ocrlib.available_backends(), reason="no OCR engine")


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication(["docrepro"])


@needs_engine
def test_the_steps_joined_in_one_window(app: QApplication, tmp_path: Path, report: Path) -> None:
    original = scan(report, tmp_path / "scan.pdf", rotation=1.5)
    chain = Chain.open(original)
    window = ChainWindow(chain, tmp_path / "work", Words("de"), synchronous=True)
    try:
        assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == [
            "1 Aufbereiten", "2 Filter für die Texterkennung", "3 Bereiche", "4 Text prüfen",
            "5 Beschreiben"]
        window.tabs.setCurrentWidget(window.text)
        text = window.text.text.toPlainText()
        assert "Ramipril" in text
        window.text.text.setPlainText(text.replace("Ramipril", "Ramipril (ACE)", 1))
        window.tabs.setCurrentWidget(window.cleanup)  # leaving the text keeps the correction
        assert window.read_project.corrected == [0]
        window.cleanup.boxes["contrast"].setChecked(True)  # the page does not move
        window.tabs.setCurrentWidget(window.text)
        assert window.read_project.corrected == [0]
        assert "Ramipril (ACE)" in window.text.text.toPlainText()
        assert "bleibt" in window.status.text()
        window.tabs.setCurrentWidget(window.cleanup)
        window.cleanup.boxes["straighten"].setChecked(False)  # the page moves
        window.tabs.setCurrentWidget(window.filters)
        assert window.read_project.corrected == []
        assert "Seite(n) 1" in window.status.text()
        window.tabs.setCurrentIndex(4)  # describe: ocrdoc's result, then tagdoc's form
        describe = window.later_panels["tagdoc"]
        assert window.tabs.currentWidget() is describe
        describe.edits["title"].setText("Neurologischer Befund")
        describe.commit()
        window.tabs.setCurrentWidget(window.cleanup)
        window.cleanup.boxes["contrast"].setChecked(True)
        window.tabs.setCurrentIndex(4)  # made anew: the person's title stays
        assert window.later_projects["tagdoc"].value("title") == "Neurologischer Befund"
        configs = window.configs()
        assert set(configs) == {"optdoc", "ocrdoc", "tagdoc"}
        assert configs["optdoc"]["pages"][0]["by"] == "person"
        assert configs["tagdoc"]["fields"]["title"] == {"value": "Neurologischer Befund",
                                                        "by": "person"}
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()
