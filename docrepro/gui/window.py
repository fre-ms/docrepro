"""The window of ``docrepro edit``: the whole way in one window.  The pages on the left, a
tab for every step whose tool is installed, in the chain's order (optdoc's preparation,
ocrdoc's filters, areas and text), and three ways out.

The steps work as in their own windows; their panels are theirs.  What joins them: when
the person turns from optdoc's tab to a later one after changing a page there, optdoc's
PDF is made anew (in the hidden working folder inside the results) and ocrdoc opens it
with everything it held so far.  ocrdoc's own rule decides what stays: where a page did
not move (only its light, contrast or colour changed), what the person decided there
stays; where it moved, it goes, and the status line names the pages.

The steps after ocrdoc that bring a panel (tagdoc's form, "5 Describe") get their tab the
same way: when the person turns to it, ocrdoc writes its result as it stands (it reads the
pages not read yet), and the step opens it with what it held; a description is of the
whole document, so a person's fields stay whatever changed before.

- **Apply** closes; the command line then takes the original through every step with
  the configuration documents of the window, exactly as ``run --config`` would.
- **Save and continue later** closes; the command line writes the chain document.
- **Cancel** (or closing the window) closes; nothing is written.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from doccor import documents
from doccor.gui.worker import Worker
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from docrepro.chain import Chain
from docrepro.errors import describe_error
from docrepro.gui.words import WORDS, Words


class ChainWindow(QMainWindow):
    """The window on one chain.  ``outcome`` is "applied", "saved" or "cancelled" once it
    closes; :meth:`configs` gives the configuration documents of its steps.
    ``synchronous`` runs every piece of work at once on the window's thread and asks
    nothing (the tests, the self-test)."""

    def __init__(self, chain: Chain, work: Path, words: Words, synchronous: bool = False) -> None:
        super().__init__()
        from ocrdoc.gui.filters_panel import FiltersPanel
        from ocrdoc.gui.regions_panel import RegionsPanel
        from ocrdoc.gui.text_panel import TextPanel
        from optdoc.gui.cleanup_panel import CleanupPanel

        self.chain = chain
        self.work = work
        self.w = words
        self.synchronous = synchronous
        self.outcome: str | None = None
        self.changed = False
        self._worker: Worker | None = None
        self._pending: tuple[Callable[[], object], Callable[[Any], None]] | None = None
        self._round = 0
        self._note = ""  # what became of the person's decisions when optdoc changed
        adapters = {step.name: made for step, made in chain.steps}
        self.optdoc, self.ocrdoc = adapters["optdoc"], adapters["ocrdoc"]
        self.prepared_project = chain.opened(self.optdoc, chain.original,
                                             chain.configs.get("optdoc"), work / "optdoc")
        self.read_project: Any = None
        self._prepared_key = b""
        self._swap(*self._remake(None))  # ocrdoc on optdoc's PDF, before the window shows
        # the steps after ocrdoc that bring a panel (tagdoc): opened when their tab is shown
        self.after_ocrdoc = [(step, made) for step, made in chain.steps
                      if step.order > 20 and hasattr(made, "panel")]
        self.later_projects: dict[str, Any] = {step.name: None for step, _m in self.after_ocrdoc}
        self.later_panels: dict[str, Any] = {}
        self.later_keys: dict[str, bytes] = {}
        self.setWindowTitle(self.w("title", tool="docrepro", name=chain.original.name))
        self.resize(1320, 840)
        self.cleanup = CleanupPanel(self.prepared_project, words)
        self.cleanup.changed.connect(self._worked)
        reading: Any = self.read_project  # ocrdoc's project, made just above
        self.filters = FiltersPanel(reading, words)
        self.filters.changed.connect(self._worked)
        self.areas = RegionsPanel(reading, words, self._find_regions)
        self.areas.changed.connect(self._worked)
        self.text = TextPanel(reading, words, self._read_page)
        central = QWidget()
        v = QVBoxLayout(central)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.pages = QListWidget()
        self.pages.setMaximumWidth(160)
        splitter.addWidget(self.pages)
        self.tabs = QTabWidget()
        for panel, key in ((self.cleanup, "tab_prepare"), (self.filters, "tab_filters_2"),
                           (self.areas, "tab_regions_3"), (self.text, "tab_text_4")):
            self.tabs.addTab(panel, self.w(key))
        self.placeholders: dict[str, QWidget] = {}
        for number, (step, _made) in enumerate(self.after_ocrdoc, 5):
            placeholder = QLabel(self.w("opening_step"))
            self.placeholders[step.name] = placeholder
            label = self.w(f"tab_{step.name}") if f"tab_{step.name}" in WORDS else step.name
            self.tabs.addTab(placeholder, f"{number} {label}")
        splitter.addWidget(self.tabs)
        splitter.setSizes([140, 1180])
        v.addWidget(splitter, 1)
        v.addLayout(self._build_bar())
        self.setCentralWidget(central)
        for n in range(len(self.prepared_project.pages)):
            self.pages.addItem(self.w("page", number=n + 1))
        self.pages.setCurrentRow(0)  # before the signal is connected: shown just below
        self.pages.currentRowChanged.connect(self._show)
        self.tabs.currentChanged.connect(lambda _i: self._show(self.pages.currentRow()))
        self._show(0)

    def _build_bar(self) -> QHBoxLayout:
        """Status and the three ways out."""
        bar = QHBoxLayout()
        self.status = QLabel("")
        self.status.setWordWrap(True)
        bar.addWidget(self.status, 1)
        self.cancel_button = QPushButton(self.w("cancel"))
        self.cancel_button.clicked.connect(self.cancel)
        self.later_button = QPushButton(self.w("later"))
        self.later_button.clicked.connect(self.later)
        self.apply_button = QPushButton(self.w("apply"))
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.apply)
        for button in (self.cancel_button, self.later_button, self.apply_button):
            button.setMinimumHeight(32)
            bar.addWidget(button)
        return bar

    # -- the steps joined ----------------------------------------------------------------------
    def _key(self) -> bytes:
        """optdoc's configuration document as it is now."""
        return documents.document_bytes(self.optdoc.config(self.prepared_project))

    def _remake(self, _previous: Any) -> tuple[Any, list[int], bytes]:
        """optdoc's PDF as its plans are now, and ocrdoc opened on it with what it held
        (its configuration document so far, else the chain's): the new project, the pages
        that lost a person's decisions, and the optdoc document it was made from.  A new
        folder each time, so that the old project can still be closed cleanly."""
        self._round += 1
        key = self._key()
        folder = self.work / "optdoc" / str(self._round)
        stem = self.chain.original.stem
        pdf = self.optdoc.write(self.prepared_project, folder, stem, None)["pdf"]
        held = (self.ocrdoc.config(self.read_project) if self.read_project is not None
                else self.chain.configs.get("ocrdoc"))
        project = self.chain.opened(self.ocrdoc, pdf, held, self.work / "ocrdoc")
        return project, self.ocrdoc.dropped(project), key

    def _swap(self, project: Any, dropped: list[int], key: bytes) -> None:
        """Put the new ocrdoc project in place of the old one, in every panel, and say what
        became of the person's decisions."""
        old, self.read_project, self._prepared_key = self.read_project, project, key
        for name in ("filters", "areas", "text"):
            panel = getattr(self, name, None)
            if panel is not None:
                panel.project = project
        if old is not None:
            self.ocrdoc.close(old)
            pages = ", ".join(str(n + 1) for n in dropped)
            self._note = (self.w("dropped_pages", pages=pages) if dropped
                          else self.w("kept_decisions"))
            self.status.setText(self._note)

    def _later_tab(self) -> bool:
        """True when a tab of a step after optdoc is open."""
        return self.tabs.currentWidget() is not self.cleanup

    def _later_step(self) -> tuple[Any, Any] | None:
        """The step after ocrdoc whose tab is open, with its adapter; None for another."""
        current = self.tabs.currentWidget()
        for step, made in self.after_ocrdoc:
            if current is self.placeholders.get(step.name) \
                    or current is self.later_panels.get(step.name):
                return step, made
        return None

    def _read_key(self) -> bytes:
        """ocrdoc's configuration document as it is now, with optdoc's it was made on."""
        return self._prepared_key + documents.document_bytes(self.ocrdoc.config(self.read_project))

    def _remake_later(self, step: Any, made: Any) -> tuple[Any, bytes]:
        """ocrdoc's result as it stands, and the later step opened on it with what it held
        (its configuration document so far, else the chain's)."""
        self._round += 1
        key = self._read_key()
        folder = self.work / "ocrdoc" / str(self._round)
        pdf = self.ocrdoc.write(self.read_project, folder, self.chain.original.stem, None)["pdf"]
        old = self.later_projects[step.name]
        held = made.config(old) if old is not None else self.chain.configs.get(step.name)
        return self.chain.opened(made, pdf, held, self.work / step.name), key

    def _swap_later(self, step: Any, made: Any, project: Any, key: bytes) -> None:
        """Put the later step's new project in place, its panel made at the first time."""
        old = self.later_projects[step.name]
        self.later_projects[step.name], self.later_keys[step.name] = project, key
        panel = self.later_panels.get(step.name)
        if panel is None:
            panel = made.panel(project, self.w)
            panel.changed.connect(lambda: self._worked(0))
            placeholder = self.placeholders[step.name]
            index = self.tabs.indexOf(placeholder)
            label = self.tabs.tabText(index)
            self.tabs.blockSignals(True)
            try:
                self.tabs.removeTab(index)
                self.tabs.insertTab(index, panel, label)
                self.tabs.setCurrentIndex(index)
            finally:
                self.tabs.blockSignals(False)
            self.later_panels[step.name] = panel
        else:
            panel.project = project
            panel.show_project()
        if old is not None:
            made.close(old)

    def _commit_later(self) -> None:
        """Take what was typed into the later steps' panels into their projects."""
        for panel in self.later_panels.values():
            panel.commit()

    def _show(self, n: int) -> None:
        """Show page ``n`` in the tab that is open; a later step's tab after a change in
        optdoc first gets optdoc's new PDF, and a step after ocrdoc ocrdoc's result."""
        if n < 0:
            return
        self.text.commit()
        self._commit_later()
        if self._later_tab() and self._key() != self._prepared_key:
            self.status.setText(self.w("preparing"))

            def then(made: tuple[Any, list[int], bytes]) -> None:
                self._swap(*made)
                self._show_now(n)

            self._run(lambda: self._remake(self.read_project), then)
            return
        later = self._later_step()
        if later is not None and self.later_keys.get(later[0].name) != self._read_key():
            step, made = later
            self.status.setText(self.w("describing"))

            def described(result: tuple[Any, bytes]) -> None:
                self._swap_later(step, made, *result)
                self.status.setText(self._note)

            self._run(lambda: self._remake_later(step, made), described)
            return
        self._show_now(n)

    def _show_now(self, n: int) -> None:
        """Show page ``n`` in the tab that is open."""
        self._mark_pages()
        current = self.tabs.currentWidget()
        if current is self.text:
            self.text.show_page(n)
        elif current is self.areas:
            self.areas.show_page(n)
        elif current is self.filters:
            self.filters.show_page(n)
        elif current is self.cleanup:
            self.cleanup.show_page(n)
        # a later step's panel shows the whole document, not a page

    def _mark_pages(self) -> None:
        """Mark the pages whose text was corrected."""
        for n, page in enumerate(self.read_project.pages):
            key = "page_corrected" if page.correction is not None else "page"
            item = self.pages.item(n)
            if item is not None:
                item.setText(self.w(key, number=n + 1))

    def _worked(self, _n: int) -> None:
        """Something of a page changed in one of the steps."""
        self.changed = True

    def configs(self) -> dict[str, dict[str, Any]]:
        """The configuration documents of the steps as the window holds them: ocrdoc's as
        it stands where the window opened it on optdoc's PDF as it is now, else what it
        held (the person did not turn to its tabs after a change in optdoc: the chain then
        brings it to the new PDF by the same rule); a later step's as its tab left it, else
        the chain's."""
        self.text.commit()
        self._commit_later()
        found = {"optdoc": self.optdoc.config(self.prepared_project),
                 "ocrdoc": self.ocrdoc.config(self.read_project)}
        for step, made in self.after_ocrdoc:
            project = self.later_projects[step.name]
            if project is not None:
                found[step.name] = made.config(project)
            elif step.name in self.chain.configs:
                found[step.name] = self.chain.configs[step.name]
        return found

    # -- work off the window's thread ----------------------------------------------------------
    def _run(self, job: Callable[[], object], then: Callable[[Any], None]) -> None:
        """Do ``job``, then ``then`` with its result; one at a time, the latest waits."""
        if self._worker is not None:
            self._pending = (job, then)
            return
        self.tabs.setEnabled(False)
        for button in (self.later_button, self.apply_button):
            button.setEnabled(False)
        self._worker = Worker(job, self, inline=self.synchronous)
        self._worker.done.connect(lambda result: self._finished(then, result))
        self._worker.failed.connect(self._failed)
        self._worker.go()

    def _finished(self, then: Callable[[Any], None], result: Any) -> None:
        """A job is done: free the window, go on with what waited, then ``then``."""
        self._release()
        then(result)

    def _failed(self, error: Exception) -> None:
        """A job failed: say so in the status line; the window stays open."""
        self._release()
        self.status.setText(self.w("failed", error=describe_error(error, self.w.language)))
        if self.synchronous:
            raise error

    def _release(self) -> None:
        """Nothing runs any more; start what waited."""
        self._worker = None
        self.tabs.setEnabled(True)
        for button in (self.later_button, self.apply_button):
            button.setEnabled(True)
        if self._pending is not None:
            job, then = self._pending
            self._pending = None
            self._run(job, then)

    def _read_page(self, n: int, then: Callable[[], None]) -> None:
        """Read page ``n`` (for the text panel), then call back."""
        self.status.setText(self.w("reading_page", number=n + 1,
                                   total=len(self.read_project.pages)))
        self._run(lambda: self.read_project.read(n), lambda _r: self._done(then))

    def _find_regions(self, n: int, then: Callable[[], None]) -> None:
        """Find the areas of page ``n`` (for the areas panel), then call back."""
        self.status.setText(self.w("finding_regions", number=n + 1))
        self._run(lambda: self.read_project.regions(n), lambda _r: self._done(then))

    def _done(self, then: Callable[[], None]) -> None:
        """A page's work is done: the status line says again what became of the person's
        decisions (if anything did), and the panel goes on."""
        self.status.setText(self._note)
        then()

    # -- the ways out --------------------------------------------------------------------------
    def apply(self) -> None:
        """Close with "applied": the results are to be written."""
        self.text.commit()
        self.outcome = "applied"
        self.close()

    def later(self) -> None:
        """Close with "saved": the chain document is to be written."""
        self.text.commit()
        self.outcome = "saved"
        self.close()

    def cancel(self) -> None:
        """Close with "cancelled": nothing is written."""
        self.outcome = "cancelled"
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Closing the window without a choice cancels; after changes, ask first."""
        if self.outcome is None:
            self.text.commit()
            worked = self.changed or bool(self.read_project.corrected)
            if worked and not self.synchronous and QMessageBox.question(
                    self, self.w("discard_title"), self.w("discard_text")) \
                    != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.outcome = "cancelled"
        if self._worker is not None:
            self._worker.wait()
        event.accept()

    def release(self) -> None:
        """Close the steps' projects."""
        self.optdoc.close(self.prepared_project)
        if self.read_project is not None:
            self.ocrdoc.close(self.read_project)
        for step, made in self.after_ocrdoc:
            if self.later_projects[step.name] is not None:
                made.close(self.later_projects[step.name])

    # -- the self-test of the standalone program ------------------------------------------------
    def self_test(self) -> None:
        """Go through the window once without a person: every tab of the first page, then
        apply."""
        for index in range(self.tabs.count()):
            self.tabs.setCurrentIndex(index)
        self.apply()
