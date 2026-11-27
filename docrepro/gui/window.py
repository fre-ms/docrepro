"""The window of ``docrepro edit``: the whole way in one window.  On the left the steps,
each with a switch and its state, and the pages; a tab for every panel of the steps whose
tools are installed, in the chain's order (optdoc's preparation, ocrdoc's filters, areas
and text, tagdoc's description), and three ways out.

**Every step is optional.**  The switches on the left say which steps are in use for this
document; a step that is off hands on what it got, and its tabs are closed and marked.
Beside each switch stands what became of the step: off, in use as suggested, changed by
hand, or to be made anew because a step before it changed.  A step that needs another
(semdoc needs ocrdoc's reading) goes off with it.  What a person decided in a step that is
switched off is kept, and back when the step is switched on again.

typdoc, which binds a picture into a PDF, has no tab: it has nothing to decide.  For a PDF
it has nothing to do.  For a picture it stays on in this window: the steps after optdoc
read PDFs only, as the tools stand, and the window is built on them.  (A picture that is to
stay a picture is prepared on the command line, with typdoc and those steps left out, or
in optdoc's own window.)

The steps work as in their own windows; their panels are theirs.  What joins them: when
the person turns from optdoc's tab to a later one after changing a page there, optdoc's
PDF is made anew (in the hidden working folder inside the results) and ocrdoc opens it
with everything it held so far.  ocrdoc's own rule decides what stays: where a page did
not move (only its light, contrast or colour changed), what the person decided there
stays; where it moved, it goes, and the status line names the pages.  Where optdoc is
off, ocrdoc reads the original.

The steps after ocrdoc that bring a panel (tagdoc's form, "5 Describe") get their tab the
same way: when the person turns to it, ocrdoc writes its result as it stands (it reads the
pages not read yet), and the step opens it with what it held; a description is of the
whole document, so a person's fields stay whatever changed before.  Where ocrdoc is off,
the step opens what optdoc gave, or the original.

- **Apply** closes; the command line then takes the original through the steps in use with
  the configuration documents of the window, exactly as ``run --config`` would.
- **Save and continue later** closes; the command line writes the chain document.
- **Cancel** (or closing the window) closes; nothing is written.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from doccor import documents
from doccor.errors import DocError
from doccor.gui.worker import Worker
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
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

from docrepro import steps as registry
from docrepro.chain import Chain
from docrepro.errors import describe_error
from docrepro.gui.words import WORDS, Words

IN_USE, OFF = "●", "○"  # the signs of a step in use and of one that is off


class ChainWindow(QMainWindow):
    """The window on one chain.  ``outcome`` is "applied", "saved" or "cancelled" once it
    closes; :meth:`configs` gives the configuration documents of its steps, :attr:`used`
    the steps the person left in use.  ``synchronous`` runs every piece of work at once on
    the window's thread and asks nothing (the tests, the self-test)."""

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
        self._note = ""  # what became of the person's decisions when a step before changed
        self._stale: set[str] = set()  # steps that may have to be made anew
        adapters = {step.name: made for step, made in chain.steps}
        self.optdoc, self.ocrdoc = adapters["optdoc"], adapters["ocrdoc"]
        self.typdoc: Any = adapters.get("typdoc")  # None where it is not installed
        self.used: set[str] = set(chain.used)
        # in this window a picture goes on as a PDF, through typdoc; a PDF needs none
        self.photo = chain.original.suffix.lower() != ".pdf"
        if not self.photo:
            self.used.discard("typdoc")
        elif self.typdoc is not None:
            self.used.add("typdoc")
        self.bound_project: Any = None
        if self.typdoc is not None and self.photo:
            self.bound_project = chain.opened(self.typdoc, chain.original,
                                              chain.configs.get("typdoc"), work / "typdoc")
        self._origin = self._bound()  # what optdoc is handed: typdoc's PDF, or the original
        self.prepared_project = chain.opened(self.optdoc, self._origin,
                                             chain.configs.get("optdoc"), work / "optdoc")
        self.read_project: Any = None
        self._prepared_key = b""
        self._read_source = chain.original  # what ocrdoc's project is opened on
        self._read_on_optdoc = False  # whether that is optdoc's PDF
        self._swap(*self._remake(None))  # ocrdoc on what optdoc gives, before the window shows
        # the steps after ocrdoc that bring a panel (tagdoc): opened when their tab is shown
        self.after_ocrdoc = [(step, made) for step, made in chain.steps
                             if step.order > 20 and hasattr(made, "panel")]
        self.later_projects: dict[str, Any] = {step.name: None for step, _m in self.after_ocrdoc}
        self.later_panels: dict[str, Any] = {}
        self.later_keys: dict[str, bytes] = {}
        self.setWindowTitle(self.w("title", tool="docrepro", name=chain.original.name))
        self.resize(1400, 840)
        self.cleanup = CleanupPanel(self.prepared_project, words)
        self.cleanup.changed.connect(lambda n: self._worked_in("optdoc", n))
        reading: Any = self.read_project  # ocrdoc's project, made just above
        self.filters = FiltersPanel(reading, words)
        self.filters.changed.connect(lambda n: self._worked_in("ocrdoc", n))
        self.areas = RegionsPanel(reading, words, self._find_regions)
        self.areas.changed.connect(lambda n: self._worked_in("ocrdoc", n))
        self.text = TextPanel(reading, words, self._read_page)
        central = QWidget()
        v = QVBoxLayout(central)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        column = QVBoxLayout(left)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self._build_steps())
        self.pages = QListWidget()
        column.addWidget(self.pages, 1)
        left.setMaximumWidth(250)
        splitter.addWidget(left)
        self.tabs = QTabWidget()
        self._tab_steps: list[str] = []  # the step each tab belongs to, by index
        self._tab_labels: list[str] = []  # each tab's words, without its sign
        for panel, key, name in ((self.cleanup, "tab_prepare", "optdoc"),
                                 (self.filters, "tab_filters_2", "ocrdoc"),
                                 (self.areas, "tab_regions_3", "ocrdoc"),
                                 (self.text, "tab_text_4", "ocrdoc")):
            self.tabs.addTab(panel, self.w(key))
            self._tab_steps.append(name)
            self._tab_labels.append(self.w(key))
        self.placeholders: dict[str, QWidget] = {}
        for number, (step, _made) in enumerate(self.after_ocrdoc, 5):
            placeholder = QLabel(self.w("opening_step"))
            self.placeholders[step.name] = placeholder
            label = self.w(f"tab_{step.name}") if f"tab_{step.name}" in WORDS else step.name
            self.tabs.addTab(placeholder, f"{number} {label}")
            self._tab_steps.append(step.name)
            self._tab_labels.append(f"{number} {label}")
        splitter.addWidget(self.tabs)
        splitter.setSizes([230, 1170])
        v.addWidget(splitter, 1)
        v.addLayout(self._build_bar())
        self.setCentralWidget(central)
        for n in range(len(self.prepared_project.pages)):
            self.pages.addItem(self.w("page", number=n + 1))
        self.pages.setCurrentRow(0)  # before the signal is connected: shown just below
        self.pages.currentRowChanged.connect(self._show)
        self.tabs.currentChanged.connect(lambda _i: self._show(self.pages.currentRow()))
        self._refresh()
        self._leave_closed_tab()
        self._show(0)

    def _build_steps(self) -> QGroupBox:
        """The steps on the left: for each a switch (in use or not) and, under it, what
        became of it; a step whose tool is not installed is shown and cannot be switched."""
        box = QGroupBox(self.w("chain_steps"))
        rows = QVBoxLayout(box)
        self.step_boxes: dict[str, QCheckBox] = {}
        self.step_states: dict[str, QLabel] = {}
        language = self.w.language
        for step in registry.STEPS:
            key = f"chain_{step.name}"
            short = self.w(key) if key in WORDS else step.name
            switch = QCheckBox(f"{step.name}: {short}")
            switch.setToolTip(step.does.get(language, step.does["en"]))
            switch.toggled.connect(lambda on, name=step.name: self._toggle(name, on))
            state = QLabel("")
            state.setIndent(22)
            state.setWordWrap(True)
            rows.addWidget(switch)
            rows.addWidget(state)
            self.step_boxes[step.name], self.step_states[step.name] = switch, state
        self.steps_box = box
        return box

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

    # -- which steps are in use ----------------------------------------------------------------
    def state(self, name: str) -> str:
        """What became of a step: "missing" (its tool is not installed), "nothing" (it has
        nothing to do for this original: typdoc for a PDF), "off", "stale"
        (in use, and what it made is to be made anew since a step before it changed),
        "person" (in use, a person decided something in it) or "auto" (in use as
        suggested)."""
        adapters = {step.name: made for step, made in self.chain.steps}
        if name not in adapters:
            return "missing"
        if name == "typdoc" and not self.photo:
            return "nothing"
        if name not in self.used:
            return "off"
        if name == "typdoc":
            project: Any = self.bound_project
        elif name == "optdoc":
            project = self.prepared_project
        elif name == "ocrdoc":
            project = self.read_project
        else:
            project = self.later_projects.get(name)
        if name in self._stale and (project is not None or name in self.chain.configs):
            return "stale"
        if project is None:  # not opened in the window: as the chain document has it
            decided = registry.decided_by_person(self.chain.configs.get(name))
        else:
            decided = registry.by_person(adapters[name], project)
        return "person" if decided else "auto"

    def _unmet(self, name: str) -> str | None:
        """The step that ``name`` needs and that is not in use, if there is one."""
        step = registry.by_name(name)
        return next((needed for needed in (step.needs if step else ())
                     if needed not in self.used), None)

    def _refresh(self) -> None:
        """Show which steps are in use: the switches and what stands under them, the
        signs on the tabs, the tabs of a step that is off closed, and nothing to apply
        where no step is in use."""
        for name, switch in self.step_boxes.items():
            state = self.state(name)
            unmet = self._unmet(name)
            switch.blockSignals(True)
            switch.setChecked(name in self.used)
            switch.blockSignals(False)
            fixed = name == "typdoc" and self.photo  # it makes the PDF the window works on
            switch.setEnabled(state not in ("missing", "nothing") and not fixed
                              and unmet is None)
            sign = OFF if state in ("missing", "nothing", "off") else IN_USE
            words = self.w(f"chain_{state}")
            if fixed:
                words = f"{words} ({self.w('chain_photo')})"
            elif unmet is not None and state != "missing":
                words = f"{words} ({self.w('chain_needs', needs=unmet)})"
            self.step_states[name].setText(f"{sign} {words}")
        for index, name in enumerate(self._tab_steps):
            on = name in self.used
            self.tabs.setTabEnabled(index, on)
            self.tabs.setTabText(index, f"{IN_USE if on else OFF} {self._tab_labels[index]}")
            self.tabs.setTabToolTip(index, "" if on else self.w("chain_off_tip", step=name))
        idle = self._worker is None
        for button in (self.later_button, self.apply_button):
            button.setEnabled(idle and bool(self.used))
        if not self.used:
            self.status.setText(self.w("chain_none"))

    def _later_than(self, name: str) -> set[str]:
        """The steps in use after ``name``."""
        order = {step.name: step.order for step in registry.STEPS}
        return {step.name for step, _made in self.chain.steps
                if step.name in self.used and order[step.name] > order[name]}

    def _toggle(self, name: str, on: bool) -> None:
        """Switch a step on or off.  A step that needs one which is off goes off with it;
        the steps after it are to be made anew; a tab that closed is left."""
        if on:
            self.used.add(name)
        else:
            self.used.discard(name)
        for step, _made in self.chain.steps:  # in the order of the steps: needs come first
            if step.name in self.used and any(n not in self.used for n in step.needs):
                self.used.discard(step.name)
        self.changed = True
        self._stale |= self._later_than(name)
        if on and name != "optdoc":
            self._stale.add(name)  # what it gets may have changed while it was off
        self._stale &= self.used
        self._refresh()
        if not self._leave_closed_tab():
            self._show(self.pages.currentRow())

    def _leave_closed_tab(self) -> bool:
        """Turn to the first open tab where the one shown belongs to a step that is off;
        True when the tab changed (which shows the page)."""
        if self.tabs.isTabEnabled(self.tabs.currentIndex()):
            return False
        for index in range(self.tabs.count()):
            if self.tabs.isTabEnabled(index):
                self.tabs.setCurrentIndex(index)
                return True
        return False

    # -- the steps joined ----------------------------------------------------------------------
    def _bound(self) -> Path:
        """What optdoc is handed: typdoc's PDF where typdoc is in use, else the original."""
        if "typdoc" not in self.used or self.bound_project is None:
            return self.chain.original
        self._round += 1
        folder = self.work / "typdoc" / str(self._round)
        made: Path = self.typdoc.write(self.bound_project, folder, self.chain.original.stem,
                                       None)["document"]
        return made

    def _key(self) -> bytes:
        """What the steps after optdoc get, named: optdoc's configuration document as it
        is now where optdoc is in use, else that it is off and what was handed on."""
        if "optdoc" not in self.used:
            return b"off|typdoc" if self._origin != self.chain.original else b"off"
        return documents.document_bytes(self.optdoc.config(self.prepared_project))

    def _remake(self, _previous: Any) -> tuple[Any, list[int], bytes, Path, bool]:
        """What optdoc gives as it is now (its PDF as its plans are, or what it was
        handed where it is off), and ocrdoc opened on it with what it held (its
        configuration document so far, else the chain's): the new project, the pages that
        lost a person's decisions, what it was made from (by name and as a file), and
        whether ocrdoc had to start anew (what it held belongs to another file: optdoc
        was switched off, and what it was handed carries no frames).  A new folder each
        time, so that the old project can still be closed cleanly."""
        self._round += 1
        key = self._key()
        if "optdoc" in self.used:
            folder = self.work / "optdoc" / str(self._round)
            pdf = self.optdoc.write(self.prepared_project, folder, self.chain.original.stem,
                                    None)["document"]
        else:
            pdf = self._origin
        held = (self.ocrdoc.config(self.read_project) if self.read_project is not None
                else self.chain.configs.get("ocrdoc"))
        anew = False
        try:
            project = self.chain.opened(self.ocrdoc, pdf, held, self.work / "ocrdoc")
        except DocError as e:
            if e.kind != "config-mismatch" or held is None:
                raise
            project, anew = self.chain.opened(self.ocrdoc, pdf, None, self.work / "ocrdoc"), True
        return project, self.ocrdoc.dropped(project), key, pdf, anew

    def _swap(self, project: Any, dropped: list[int], key: bytes, pdf: Path,
              anew: bool) -> None:
        """Put the new ocrdoc project in place of the old one, in every panel, and say what
        became of the person's decisions."""
        old, self.read_project, self._prepared_key = self.read_project, project, key
        self._read_source, self._read_on_optdoc = pdf, not key.startswith(b"off")
        self._stale.discard("ocrdoc")
        for name in ("filters", "areas", "text"):
            panel = getattr(self, name, None)
            if panel is not None:
                panel.project = project
        if old is not None:
            self.ocrdoc.close(old)
            pages = ", ".join(str(n + 1) for n in dropped)
            self._note = (self.w("chain_anew") if anew
                          else self.w("dropped_pages", pages=pages) if dropped
                          else self.w("kept_decisions"))
            if "ocrdoc" not in self.used and not (anew or dropped):
                self._note = ""  # nothing of ocrdoc's is in use, and nothing of it went
            self.status.setText(self._note)

    def _step_of_tab(self) -> str:
        """The step the open tab belongs to."""
        return self._tab_steps[self.tabs.currentIndex()]

    def _later_step(self) -> tuple[Any, Any] | None:
        """The step after ocrdoc whose tab is open, with its adapter; None for another."""
        name = self._step_of_tab()
        return next(((step, made) for step, made in self.after_ocrdoc if step.name == name),
                    None)

    def _read_key(self) -> bytes:
        """What the steps after ocrdoc get, named: ocrdoc's configuration document as it
        is now (or that ocrdoc is off), with what ocrdoc itself was made on."""
        if "ocrdoc" not in self.used:
            return self._prepared_key + b"|off"
        return self._prepared_key + b"|" + documents.document_bytes(
            self.ocrdoc.config(self.read_project))

    def _remake_later(self, step: Any, made: Any) -> tuple[Any, bytes]:
        """What the step before gives as it stands (ocrdoc's result where ocrdoc is in
        use, else what ocrdoc would have got: optdoc's PDF or the original), and the later
        step opened on it with what it held (its configuration document so far, else the
        chain's)."""
        self._round += 1
        key = self._read_key()
        if "ocrdoc" in self.used:
            folder = self.work / "ocrdoc" / str(self._round)
            pdf = self.ocrdoc.write(self.read_project, folder, self.chain.original.stem,
                                    None)["document"]
        else:
            pdf = self._read_source
        old = self.later_projects[step.name]
        held = made.config(old) if old is not None else self.chain.configs.get(step.name)
        return self.chain.opened(made, pdf, held, self.work / step.name), key

    def _swap_later(self, step: Any, made: Any, project: Any, key: bytes) -> None:
        """Put the later step's new project in place, its panel made at the first time."""
        old = self.later_projects[step.name]
        self.later_projects[step.name], self.later_keys[step.name] = project, key
        self._stale.discard(step.name)
        panel = self.later_panels.get(step.name)
        if panel is None:
            panel = made.panel(project, self.w)
            panel.changed.connect(lambda: self._worked_in(step.name, 0))
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
        optdoc first gets what optdoc gives now, and a step after ocrdoc ocrdoc's result."""
        if n < 0:
            return
        self.text.commit()
        self._commit_later()
        name = self._step_of_tab()
        if name not in self.used:  # no tab of a step in use is open
            self._refresh()
            return
        if name != "optdoc" and self._key() != self._prepared_key:
            self.status.setText(self.w("preparing"))

            def then(made: tuple[Any, list[int], bytes, Path, bool]) -> None:
                self._swap(*made)
                self._show(n)

            self._run(lambda: self._remake(self.read_project), then)
            return
        self._stale.discard("ocrdoc")  # it stands on what optdoc gives now
        later = self._later_step()
        if later is not None and self.later_keys.get(later[0].name) != self._read_key():
            step, made = later
            self.status.setText(self.w("describing"))

            def described(result: tuple[Any, bytes]) -> None:
                self._swap_later(step, made, *result)
                self.status.setText(self._note)
                self._refresh()

            self._run(lambda: self._remake_later(step, made), described)
            return
        if later is not None:
            self._stale.discard(later[0].name)
        self._show_now(n)

    def _show_now(self, n: int) -> None:
        """Show page ``n`` in the tab that is open."""
        self._mark_pages()
        self._refresh()
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

    def _worked_in(self, name: str, _n: int) -> None:
        """Something changed in a step: the steps in use after it are to be made anew."""
        self.changed = True
        self._stale |= self._later_than(name)
        self._refresh()

    def configs(self) -> dict[str, dict[str, Any]]:
        """The configuration documents of the steps as the window holds them, of the steps
        in use and of those switched off that hold something to keep (a person's
        decisions, or what the chain document held).  ocrdoc's is as it stands where the
        window opened it on what optdoc gives now, else what it held (the person did not
        turn to its tabs after a change in optdoc: the chain then brings it over by the
        same rule), and none where what it held cannot be brought over (optdoc was
        switched off since: ocrdoc then starts anew); a later step's as its tab left it,
        else the chain's."""
        self.text.commit()
        self._commit_later()
        found: dict[str, dict[str, Any]] = {}
        held = self.chain.configs
        if self.bound_project is not None and ("typdoc" in self.used or "typdoc" in held):
            found["typdoc"] = self.typdoc.config(self.bound_project)
        if "optdoc" in self.used or "optdoc" in held \
                or registry.by_person(self.optdoc, self.prepared_project):
            found["optdoc"] = self.optdoc.config(self.prepared_project)
        fits = self._read_on_optdoc == ("optdoc" in self.used) or not self._read_on_optdoc
        if fits and ("ocrdoc" in self.used or "ocrdoc" in held
                     or registry.by_person(self.ocrdoc, self.read_project)):
            found["ocrdoc"] = self.ocrdoc.config(self.read_project)
        for step, made in self.chain.steps:
            if step.name in ("typdoc", "optdoc", "ocrdoc"):
                continue
            project = self.later_projects.get(step.name)
            if project is not None:
                found[step.name] = made.config(project)
            elif step.name in held:
                found[step.name] = held[step.name]
        return found

    # -- work off the window's thread ----------------------------------------------------------
    def _run(self, job: Callable[[], object], then: Callable[[Any], None]) -> None:
        """Do ``job``, then ``then`` with its result; one at a time, the latest waits."""
        if self._worker is not None:
            self._pending = (job, then)
            return
        self.tabs.setEnabled(False)
        self.steps_box.setEnabled(False)
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
        self.steps_box.setEnabled(True)
        self._refresh()
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
        if self.bound_project is not None:
            self.typdoc.close(self.bound_project)
        self.optdoc.close(self.prepared_project)
        if self.read_project is not None:
            self.ocrdoc.close(self.read_project)
        for step, made in self.after_ocrdoc:
            if self.later_projects[step.name] is not None:
                made.close(self.later_projects[step.name])

    # -- the self-test of the standalone program ------------------------------------------------
    def self_test(self) -> None:
        """Go through the window once without a person: every open tab of the first page,
        then apply."""
        for index in range(self.tabs.count()):
            if self.tabs.isTabEnabled(index):
                self.tabs.setCurrentIndex(index)
        self.apply()
