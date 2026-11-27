"""The joined window, driven without a screen: every step's tabs on one document, each
step opened when its tab is shown; after a change in optdoc, a later tab gets optdoc's new
PDF, and a person's correction stays where the page did not move and goes where it did,
with the page named in the status line.  The steps on the left: each can be switched off
and on, the tabs of a step that is off are closed and marked, and beside each switch stands
what became of the step."""

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
        assert window.project("ocrdoc") is None  # a step opens when its tab is first shown
        window.tabs.setCurrentIndex(3)
        text = window.panel("ocrdoc", 2)
        assert window.tabs.currentWidget() is text
        assert window.given("ocrdoc") == window.output("optdoc")
        assert "Ramipril" in text.text.toPlainText()
        text.text.setPlainText(text.text.toPlainText().replace("Ramipril", "Ramipril (ACE)", 1))
        window.tabs.setCurrentIndex(0)  # leaving the text keeps the correction
        cleanup = window.panel("optdoc")
        assert window.project("ocrdoc").corrected == [0]
        assert window.step_states["ocrdoc"].text() == "● in Gebrauch, von Hand geändert"
        cleanup.boxes["contrast"].setChecked(True)  # the page does not move
        assert window.step_states["optdoc"].text() == "● in Gebrauch, von Hand geändert"
        assert window.step_states["ocrdoc"].text() == "● in Gebrauch, neu zu machen"
        window.tabs.setCurrentIndex(3)
        assert window.project("ocrdoc").corrected == [0]
        assert "Ramipril (ACE)" in text.text.toPlainText()
        assert "bleibt" in window.status.text() and "ocrdoc" in window.status.text()
        assert window.step_states["ocrdoc"].text() == "● in Gebrauch, von Hand geändert"
        window.tabs.setCurrentIndex(0)
        cleanup.boxes["straighten"].setChecked(False)  # the page moves
        window.tabs.setCurrentIndex(1)
        assert window.project("ocrdoc").corrected == []
        assert "Seite(n) 1" in window.status.text()
        window.tabs.setCurrentIndex(4)  # describe: ocrdoc's result, then tagdoc's form
        describe = window.panel("tagdoc")
        assert window.tabs.currentWidget() is describe
        assert window.given("tagdoc") == window.output("ocrdoc")
        describe.edits["title"].setText("Neurologischer Befund")
        describe.commit()
        window.tabs.setCurrentIndex(0)
        cleanup.boxes["contrast"].setChecked(True)
        window.tabs.setCurrentIndex(4)  # made anew: the person's title stays
        assert window.project("tagdoc").value("title") == "Neurologischer Befund"
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
    """optdoc off: its tab closes, ocrdoc reads the original, and keeps a person's
    correction, since optdoc had not moved the page; ocrdoc off: its tabs close, and the
    description opens on what is left; everything off: nothing to apply.  What the window
    hands back says which steps are in use, and keeps what a person decided in a step that
    is off."""
    original = scan(report, tmp_path / "scan.pdf")
    chain = Chain.open(original)
    window = ChainWindow(chain, tmp_path / "work", Words("de"), synchronous=True)
    try:
        window.panel("optdoc").boxes["contrast"].setChecked(True)  # a person's plan in optdoc
        window.tabs.setCurrentIndex(3)
        text = window.panel("ocrdoc", 2)
        assert "Ramipril" in text.text.toPlainText()
        prepared = window.given("ocrdoc")
        assert prepared != original and prepared == window.output("optdoc")
        text.text.setPlainText(text.text.toPlainText().replace("Ramipril", "Ramipril (ACE)", 1))
        window.tabs.setCurrentIndex(1)  # the correction goes into ocrdoc's project
        window.tabs.setCurrentIndex(3)
        window.step_boxes["optdoc"].setChecked(False)
        assert window.used == {"ocrdoc", "tagdoc"}
        assert window.tabs.tabText(0) == "○ 1 Aufbereiten" and not window.tabs.isTabEnabled(0)
        assert "optdoc ist ausgeschaltet" in window.tabs.tabToolTip(0)
        assert window.step_states["optdoc"].text() == "○ aus"
        assert window.given("ocrdoc") == original
        assert window.tabs.currentWidget() is text  # an open tab stays
        assert window.project("ocrdoc").corrected == [0]  # the page lies as it lay
        assert "bleibt" in window.status.text()
        assert "Ramipril (ACE)" in text.text.toPlainText()
        configs = window.configs()
        assert configs["optdoc"]["pages"][0]["by"] == "person"  # kept for later
        assert configs["ocrdoc"]["input"]["sha256"] == chain.named[0]["sha256"]
        window.step_boxes["ocrdoc"].setChecked(False)
        assert window.used == {"tagdoc"}
        assert [window.tabs.isTabEnabled(i) for i in range(5)] == [False] * 4 + [True]
        assert window.tabs.currentIndex() == 4  # the tab that closed is left
        assert window.given("tagdoc") == original  # described: the original
        assert window.step_states["ocrdoc"].text() == "○ aus"
        window.step_boxes["tagdoc"].setChecked(False)
        assert window.used == set() and not window.apply_button.isEnabled()
        assert "nichts zu tun" in window.status.text()
        window.step_boxes["optdoc"].setChecked(True)
        assert window.used == {"optdoc"} and window.apply_button.isEnabled()
        assert window.tabs.currentWidget() is window.panel("optdoc")
        assert window.step_states["optdoc"].text() == "● in Gebrauch, von Hand geändert"
        window.step_boxes["tagdoc"].setChecked(True)
        assert window.step_states["tagdoc"].text() == "● in Gebrauch, neu zu machen"
        window.tabs.setCurrentIndex(4)  # described anew: optdoc's PDF now
        assert window.given("tagdoc") == window.output("optdoc")
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
    handed the picture itself, ocrdoc reads optdoc's picture, tagdoc describes it; every
    page is the same page either way, so what a person decided in optdoc and in ocrdoc
    stays; and the chain makes the picture from what the window holds."""
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
        assert window.tabs.currentIndex() == 1  # optdoc is off: ocrdoc's first tab
        bound = window.given("ocrdoc")  # ocrdoc reads typdoc's PDF: the photo is in it as it came
        assert bound == window.output("typdoc") and bound.suffix == ".pdf"
        assert photo.read_bytes() in bound.read_bytes()
        window.step_boxes["optdoc"].setChecked(True)  # optdoc prepares typdoc's PDF
        assert window.project("optdoc").config()["input"]["suffix"] == ".pdf"
        assert window.given("ocrdoc") == window.output("optdoc")
        assert window.given("ocrdoc").suffix == ".pdf"
        # a person's work in optdoc and in ocrdoc, on typdoc's PDF
        from ocrdoc import layout
        from optdoc import cleanup

        planned = cleanup.CleanupPlan.from_dict({
            **window.project("optdoc").plan(0).full_dict(), "contrast": True,
            "contrast_strength": 4})
        window.project("optdoc").set_plan(0, planned)
        window._worked_in("optdoc", 0)
        window.tabs.setCurrentIndex(2)
        drawn = layout.Region("ignore", (60.0, 700.0, 300.0, 760.0))
        window.project("ocrdoc").set_regions(0, [drawn])
        # typdoc off: optdoc is handed the picture, and every step after it a picture;
        # it shows the same pages, so what the person did stays in both steps
        window.step_boxes["typdoc"].setChecked(False)
        assert window.used == {"optdoc", "ocrdoc"} and window.given("optdoc") == photo
        assert window.step_states["typdoc"].text() == "○ off"
        assert window.project("optdoc").config()["input"]["suffix"] == ".jpg"
        assert window.project("optdoc").rebased  # optdoc took the plan along: nothing went
        for step in ("optdoc", "ocrdoc"):
            assert window.w("kept_decisions", step=step) in window.status.text()
        assert window.project("optdoc").plan(0).full_dict() == planned.full_dict()
        assert window.project("ocrdoc").picture and window.project("ocrdoc").dropped == []
        assert window.project("ocrdoc").regions(0) == [layout.rounded(drawn)]
        window.tabs.setCurrentIndex(0)
        assert window.panel("optdoc").project is window.project("optdoc")
        window.tabs.setCurrentIndex(1)
        assert window.given("ocrdoc").suffix == ".jpg" and window.project("ocrdoc").picture
        window.step_boxes["tagdoc"].setChecked(True)
        window.tabs.setCurrentIndex(4)
        assert window.project("tagdoc").picture
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
        assert window.given("optdoc").suffix == ".pdf"
        assert window.project("optdoc").config()["input"]["suffix"] == ".pdf"
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()
    # a chain opened for a picture that is to stay one starts so in the window
    kept = Chain.open(photo, without=("typdoc", "ocrdoc", "tagdoc"))
    window = ChainWindow(kept, tmp_path / "work2", Words("de"), synchronous=True)
    try:
        assert window.used == {"optdoc"} and window.given("optdoc") == photo
        assert window.step_states["typdoc"].text() == "○ aus"
        assert window.project("optdoc").picture
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
        assert window.given("optdoc").suffix == ".pdf" and len(window.project("optdoc").pages) == 2
        assert "(+1)" in window.windowTitle()
    finally:
        window.outcome = "cancelled"
        window.close()
        window.release()
