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
            "typdoc": "○ nichts zu tun: schon ein PDF",
            "optdoc": "● in Gebrauch, wie vorgeschlagen",
            "ocrdoc": "● in Gebrauch, wie vorgeschlagen",
            "tagdoc": "● in Gebrauch, wie vorgeschlagen"}
        assert not window.step_boxes["typdoc"].isEnabled()
        assert window.step_boxes["optdoc"].text() == "optdoc: aufbereiten"
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
        assert configs["ocrdoc"]["input"]["sha256"] == chain.named[0]["sha256"]
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
            ("typdoc", False), ("optdoc", True), ("ocrdoc", False), ("tagdoc", True)]
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()


def test_a_picture_in_the_window(app: QApplication, tmp_path: Path, report: Path) -> None:
    """For a picture typdoc is on unless the person switches it off.  On, the picture goes
    on as a PDF.  Off, it stays a picture through every step in the window too: optdoc is
    handed the picture itself (and starts anew on it), ocrdoc reads optdoc's picture,
    tagdoc describes it; and the chain makes the picture from what the window holds."""
    from tests.synthetic import photo_of

    photo = photo_of(report, tmp_path / "foto.jpg")
    chain = Chain.open(photo, settings={"reader": "none"}, without=("optdoc", "tagdoc"))
    window = ChainWindow(chain, tmp_path / "work", Words("en"), synchronous=True)
    try:
        assert window.used == {"typdoc", "ocrdoc"}
        assert window.step_boxes["typdoc"].text() == "typdoc: bind into a PDF"
        assert window.step_boxes["typdoc"].isChecked() and window.step_boxes["typdoc"].isEnabled()
        assert window.step_states["typdoc"].text() == "● in use, as suggested"
        assert window.tabs.tabText(4) == "○ 5 Describe" and not window.tabs.isTabEnabled(4)
        bound = window._origin  # ocrdoc reads typdoc's PDF: the photo is in it as it came
        assert bound.suffix == ".pdf" and window._read_source == bound
        assert photo.read_bytes() in bound.read_bytes()
        window.step_boxes["optdoc"].setChecked(True)  # optdoc prepares typdoc's PDF
        assert window.prepared_project.config()["input"]["suffix"] == ".pdf"
        window.tabs.setCurrentWidget(window.filters)
        assert window._read_on_optdoc and window._read_source.suffix == ".pdf"
        # a person's work in optdoc and in ocrdoc, on typdoc's PDF
        from ocrdoc import layout
        from optdoc import cleanup

        planned = cleanup.CleanupPlan.from_dict({
            **window.prepared_project.plan(0).full_dict(), "contrast": True,
            "contrast_strength": 4})
        window.prepared_project.set_plan(0, planned)
        window._worked_in("optdoc", 0)
        window.tabs.setCurrentWidget(window.areas)
        drawn = layout.Region("ignore", (60.0, 700.0, 300.0, 760.0))
        window.read_project.set_regions(0, [drawn])
        # typdoc off: optdoc is handed the picture, and every step after it a picture;
        # it shows the same pages, so what the person did stays in both steps
        window.step_boxes["typdoc"].setChecked(False)
        assert window.used == {"optdoc", "ocrdoc"} and window._origin == photo
        assert window.step_states["typdoc"].text() == "○ off"
        assert window.prepared_project.config()["input"]["suffix"] == ".jpg"
        assert window.prepared_project.rebased  # optdoc took the plan along: nothing went
        assert window.status.text() == window.w("kept_decisions")
        assert window.prepared_project.plan(0).full_dict() == planned.full_dict()
        window.tabs.setCurrentWidget(window.areas)
        assert window.read_project.picture and window.read_project.dropped == []
        assert window.read_project.regions(0) == [layout.rounded(drawn)]
        assert window.cleanup.project is window.prepared_project
        window.tabs.setCurrentWidget(window.filters)
        assert window._read_source.suffix == ".jpg" and window.read_project.picture
        window.step_boxes["tagdoc"].setChecked(True)
        window.tabs.setCurrentIndex(4)
        assert window.later_projects["tagdoc"].picture
        configs = window.configs()
        assert "typdoc" not in configs and configs["tagdoc"]["input"]["suffix"] == ".jpg"
        chain.used = set(window.used)
        answer = chain.run(tmp_path / "out", configs=configs)
        assert [(s["tool"], s["used"]) for s in answer["steps"]] == [
            ("typdoc", False), ("optdoc", True), ("ocrdoc", True), ("tagdoc", True)]
        assert Path(answer["document"]).suffix == ".jpg"
        assert b"<x:xmpmeta" in Path(answer["document"]).read_bytes()
        # back on: a PDF again
        window.step_boxes["typdoc"].setChecked(True)
        assert window._origin.suffix == ".pdf"
        assert window.prepared_project.config()["input"]["suffix"] == ".pdf"
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()
    # a chain opened for a picture that is to stay one starts so in the window
    kept = Chain.open(photo, without=("typdoc", "ocrdoc", "tagdoc"))
    window = ChainWindow(kept, tmp_path / "work2", Words("de"), synchronous=True)
    try:
        assert window.used == {"optdoc"} and window._origin == photo
        assert window.step_states["typdoc"].text() == "○ aus"
        assert window.prepared_project.picture
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()


def test_several_pictures_in_the_window(app: QApplication, tmp_path: Path, report: Path) -> None:
    """Several pictures are one document only bound into one: in the window typdoc is on
    and cannot be switched off, and optdoc works on the PDF of all of them."""
    from tests.synthetic import photo_of

    pictures = [photo_of(report, tmp_path / "a.jpg"), photo_of(report, tmp_path / "b.jpg")]
    chain = Chain.open(pictures, settings={"reader": "none"})
    window = ChainWindow(chain, tmp_path / "work", Words("de"), synchronous=True)
    try:
        assert window.several and "typdoc" in window.used
        assert not window.step_boxes["typdoc"].isEnabled()
        assert "2 Bilder: nur gebunden ein Dokument" in window.step_states["typdoc"].text()
        assert window._origin.suffix == ".pdf" and len(window.prepared_project.pages) == 2
        assert "(+1)" in window.windowTitle()
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()
