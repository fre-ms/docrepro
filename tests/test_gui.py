"""The joined window, driven without a screen: optdoc's tab and ocrdoc's tabs on one
document; after a change in optdoc, a later tab gets optdoc's new PDF, and a person's
correction stays where the page did not move and goes where it did, with the page named
in the status line.  The steps on the left: each can be switched off and on, the tabs of
a step that is off are closed and marked, and beside each switch stands what became of
the step."""

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
            "● 1 Aufbereiten", "● 2 Filter für die Texterkennung", "● 3 Bereiche",
            "● 4 Text prüfen", "● 5 Beschreiben"]
        assert window.used == {"optdoc", "ocrdoc", "tagdoc"}
        assert {name: label.text() for name, label in window.step_states.items()} == {
            "optdoc": "● in Gebrauch, wie vorgeschlagen",
            "ocrdoc": "● in Gebrauch, wie vorgeschlagen",
            "semdoc": "○ nicht installiert",
            "tagdoc": "● in Gebrauch, wie vorgeschlagen"}
        assert not window.step_boxes["semdoc"].isEnabled()
        window.tabs.setCurrentWidget(window.text)
        text = window.text.text.toPlainText()
        assert "Ramipril" in text
        window.text.text.setPlainText(text.replace("Ramipril", "Ramipril (ACE)", 1))
        window.tabs.setCurrentWidget(window.cleanup)  # leaving the text keeps the correction
        assert window.read_project.corrected == [0]
        assert window.step_states["ocrdoc"].text() == "● in Gebrauch, von Hand geändert"
        window.cleanup.boxes["contrast"].setChecked(True)  # the page does not move
        assert window.step_states["optdoc"].text() == "● in Gebrauch, von Hand geändert"
        assert window.step_states["ocrdoc"].text() == "● in Gebrauch, neu zu machen"
        window.tabs.setCurrentWidget(window.text)
        assert window.read_project.corrected == [0]
        assert "Ramipril (ACE)" in window.text.text.toPlainText()
        assert "bleibt" in window.status.text()
        assert window.step_states["ocrdoc"].text() == "● in Gebrauch, von Hand geändert"
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


@needs_engine
def test_steps_switched_off_and_on(app: QApplication, tmp_path: Path, report: Path) -> None:
    """optdoc off: its tab closes, ocrdoc reads the original and starts anew; ocrdoc off:
    its tabs close, and the description opens on what is left; everything off: nothing to
    apply.  What the window hands back says which steps are in use, and keeps what a
    person decided in a step that is off."""
    original = scan(report, tmp_path / "scan.pdf")
    chain = Chain.open(original)
    window = ChainWindow(chain, tmp_path / "work", Words("de"), synchronous=True)
    try:
        window.cleanup.boxes["contrast"].setChecked(True)  # a person's plan in optdoc
        window.tabs.setCurrentWidget(window.text)
        assert "Ramipril" in window.text.text.toPlainText()
        prepared = window._read_source
        assert prepared != original and window._read_on_optdoc
        window.step_boxes["optdoc"].setChecked(False)
        assert window.used == {"ocrdoc", "tagdoc"}
        assert window.tabs.tabText(0) == "○ 1 Aufbereiten" and not window.tabs.isTabEnabled(0)
        assert "optdoc ist ausgeschaltet" in window.tabs.tabToolTip(0)
        assert window.step_states["optdoc"].text() == "○ aus"
        assert window._read_source == original and not window._read_on_optdoc
        assert "beginnt neu" in window.status.text()  # what ocrdoc held was of optdoc's PDF
        assert window.tabs.currentWidget() is window.text  # an open tab stays
        assert "Ramipril" in window.text.text.toPlainText()  # read from the original
        configs = window.configs()
        assert configs["optdoc"]["pages"][0]["by"] == "person"  # kept for later
        assert configs["ocrdoc"]["input"]["sha256"] == chain.sha256
        window.step_boxes["ocrdoc"].setChecked(False)
        assert window.used == {"tagdoc"}
        assert [window.tabs.isTabEnabled(i) for i in range(5)] == [False] * 4 + [True]
        assert window.tabs.currentIndex() == 4  # the tab that closed is left
        assert window.later_projects["tagdoc"] is not None  # described: the original
        assert window.step_states["ocrdoc"].text() == "○ aus"
        window.step_boxes["tagdoc"].setChecked(False)
        assert window.used == set() and not window.apply_button.isEnabled()
        assert "nichts zu tun" in window.status.text()
        window.step_boxes["optdoc"].setChecked(True)
        assert window.used == {"optdoc"} and window.apply_button.isEnabled()
        assert window.tabs.currentWidget() is window.cleanup
        assert window.step_states["optdoc"].text() == "● in Gebrauch, von Hand geändert"
        window.step_boxes["tagdoc"].setChecked(True)
        assert window.step_states["tagdoc"].text() == "● in Gebrauch, neu zu machen"
        window.tabs.setCurrentIndex(4)  # described anew: optdoc's PDF now
        assert window._read_on_optdoc
        assert window.step_states["tagdoc"].text() == "● in Gebrauch, wie vorgeschlagen"
        chain.used = set(window.used)
        answer = chain.run(tmp_path / "out", configs=window.configs())
        assert [(s["tool"], s["used"]) for s in answer["steps"]] == [
            ("optdoc", True), ("ocrdoc", False), ("tagdoc", True)]
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()


def test_a_photo_keeps_optdoc(app: QApplication, tmp_path: Path, report: Path) -> None:
    """A photo becomes a PDF through optdoc: its switch is on and cannot be turned, even
    where the chain was opened without it; and a step that is off in the chain document
    is off in the window."""
    from tests.synthetic import photo_of

    photo = photo_of(report, tmp_path / "foto.jpg")
    chain = Chain.open(photo, settings={"reader": "none"}, without=("optdoc", "tagdoc"))
    window = ChainWindow(chain, tmp_path / "work", Words("en"), synchronous=True)
    try:
        assert window.used == {"optdoc", "ocrdoc"}
        assert window.step_boxes["optdoc"].isChecked()
        assert not window.step_boxes["optdoc"].isEnabled()
        assert "a photo becomes a PDF through optdoc" in window.step_states["optdoc"].text()
        assert window.tabs.tabText(4) == "○ 5 Describe" and not window.tabs.isTabEnabled(4)
        assert window.step_states["tagdoc"].text() == "○ off"
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()
