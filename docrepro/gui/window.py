"""The window of ``docrepro edit``: the whole way in one window.  On the left the steps,
each with a switch and its state, and the pages; the tabs of the steps whose tools are
installed, in the chain's order (each step brings its own: optdoc's preparation, ocrdoc's
filters, areas and text, tagdoc's description), numbered; and three ways out.

**No step is named here.**  The window goes through the steps as the chain does
(:mod:`docrepro.chain`): each step that is in use is handed what the step in use before it
gives, the first the original (or the originals, to the step that binds pictures).  A
step is opened when its tab is first shown, and opened again whenever what it is handed
changed (a step before it was switched, or a person changed something there), with
everything it held, so that the step's own rule decides what stays of what a person
decided in it: a page that came from the same place and lies as it lay keeps it, a page
that lies otherwise loses it (its origin and its frame, :mod:`doccor.origins`).  So a
picture and the PDF typdoc bound it into show the same pages, and switching typdoc keeps
what was decided in every step after it, with optdoc in use or not.  The status line
says what became of a person's decisions.

**Every step is optional.**  The switches on the left say which steps are in use for this
document; a step that is off hands on what it got, and its tabs are closed and marked.
Beside each switch stands what became of the step: off, in use as suggested, changed by
hand, or to be made anew because a step before it changed.  What a person decided in a
step that is switched off is kept, and back when the step is switched on again.  A step
with nothing to do (typdoc for a PDF) cannot be switched; several pictures are one
document only bound into one, so the step that binds them stays on.

- **Apply** closes; the command line then takes the original through the steps in use with
  the configuration documents of the window, exactly as ``run --config`` would.
- **Save and continue later** closes; the command line writes the chain document.
- **Cancel** (or closing the window) closes; nothing is written.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from doccor import documents, origins
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


@dataclass(eq=False)
class Stage:
    """One step in the window: its tool's adapter; its project once opened, on ``given``,
    standing on ``basis`` (what the steps before it were then); the file it last wrote for
    the step after it, named by what it was made from; its panels and the indices of their
    tabs."""

    step: registry.Step
    adapter: Any
    project: Any = None
    given: Path | list[Path] | None = None
    basis: bytes | None = None
    output: tuple[bytes, Path] | None = None
    panels: list[Any] = field(default_factory=list)
    tabs: list[int] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.step.name


@dataclass
class Opened:
    """A step opened anew off the window's thread, to be put in place on it: its project,
    what it was opened on and stands on, the pages that lost a person's decisions, and
    whether it had to start anew (what it held belonged to another document)."""

    stage: Stage
    project: Any
    given: Path | list[Path]
    basis: bytes
    dropped: list[int]
    anew: bool


class ChainWindow(QMainWindow):
    """The window on one chain.  ``outcome`` is "applied", "saved" or "cancelled" once it
    closes; :meth:`configs` gives the configuration documents of its steps, :attr:`used`
    the steps the person left in use.  ``synchronous`` runs every piece of work at once on
    the window's thread and asks nothing (the tests, the self-test)."""

    def __init__(self, chain: Chain, work: Path, words: Words, synchronous: bool = False) -> None:
        super().__init__()
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
        self.stages = [Stage(step, made) for step, made in chain.steps]
        self._by_name = {stage.name: stage for stage in self.stages}
        self.several = len(chain.originals) > 1  # one document only bound into one
        # a step with nothing to do for these originals (typdoc for a PDF) is not in use
        self.used: set[str] = {name for name in chain.used if name in self._by_name
                               and self._by_name[name].step.has_work(chain.originals)}
        named = chain.original.name + (f" (+{len(chain.originals) - 1})" if self.several else "")
        self.setWindowTitle(self.w("title", tool="docrepro", name=named))
        self.resize(1400, 840)
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
        self._tab_stage: list[Stage] = []  # the step each tab belongs to, by index
        self._tab_labels: list[str] = []  # each tab's words, without its sign
        for stage in self.stages:  # every step's tabs, a placeholder until it is opened
            for label in (stage.adapter.tabs(words) if hasattr(stage.adapter, "tabs") else []):
                index = self.tabs.count()
                self.tabs.addTab(QLabel(self.w("opening_step")), f"{index + 1} {label}")
                stage.tabs.append(index)
                self._tab_stage.append(stage)
                self._tab_labels.append(f"{index + 1} {label}")
        splitter.addWidget(self.tabs)
        splitter.setSizes([230, 1170])
        v.addWidget(splitter, 1)
        v.addLayout(self._build_bar())
        self.setCentralWidget(central)
        for n in range(sum(len(origins.of(o)) for o in chain.originals)):
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

    # -- what the window holds, by step --------------------------------------------------------
    def project(self, name: str) -> Any:
        """A step's project, where the window opened it."""
        stage = self._by_name.get(name)
        return None if stage is None else stage.project

    def given(self, name: str) -> Path | list[Path] | None:
        """What a step's project was opened on."""
        stage = self._by_name.get(name)
        return None if stage is None else stage.given

    def output(self, name: str) -> Path | None:
        """The file a step last wrote for the step after it."""
        stage = self._by_name.get(name)
        return None if stage is None or stage.output is None else stage.output[1]

    def panel(self, name: str, k: int = 0) -> Any:
        """A step's ``k``-th panel, once the step was opened."""
        stage = self._by_name.get(name)
        return stage.panels[k] if stage is not None and k < len(stage.panels) else None

    # -- which steps are in use ----------------------------------------------------------------
    def state(self, name: str) -> str:
        """What became of a step: "missing" (its tool is not installed), "nothing" (it has
        nothing to do for these originals: typdoc for a PDF), "off", "stale" (in use, and
        what it made is to be made anew since a step before it changed), "person" (in use,
        a person decided something in it) or "auto" (in use as suggested)."""
        stage = self._by_name.get(name)
        if stage is None:
            return "missing"
        if not stage.step.has_work(self.chain.originals):
            return "nothing"
        if name not in self.used:
            return "off"
        if name in self._stale and (stage.project is not None or name in self.chain.configs):
            return "stale"
        if stage.project is None:  # not opened in the window: as the chain document has it
            decided = registry.decided_by_person(self.chain.configs.get(name))
        else:
            decided = registry.by_person(stage.adapter, stage.project)
        return "person" if decided else "auto"

    def _refresh(self) -> None:
        """Show which steps are in use: the switches and what stands under them, the
        signs on the tabs, the tabs of a step that is off closed, and nothing to apply
        where no step is in use."""
        for name, switch in self.step_boxes.items():
            state = self.state(name)
            stage = self._by_name.get(name)
            switch.blockSignals(True)
            switch.setChecked(name in self.used)
            switch.blockSignals(False)
            bound = stage is not None and stage.step.takes == "pictures" and self.several
            switch.setEnabled(state not in ("missing", "nothing") and not bound)
            sign = OFF if state in ("missing", "nothing", "off") else IN_USE
            words = self.w(f"chain_{state}")
            if bound:
                words = f"{words} ({self.w('chain_several', count=len(self.chain.originals))})"
            self.step_states[name].setText(f"{sign} {words}")
        for index, stage in enumerate(self._tab_stage):
            on = stage.name in self.used
            self.tabs.setTabEnabled(index, on)
            self.tabs.setTabText(index, f"{IN_USE if on else OFF} {self._tab_labels[index]}")
            self.tabs.setTabToolTip(index, "" if on else self.w("chain_off_tip", step=stage.name))
        idle = self._worker is None
        for button in (self.later_button, self.apply_button):
            button.setEnabled(idle and bool(self.used))
        if not self.used:
            self.status.setText(self.w("chain_none"))

    def _later_than(self, name: str) -> set[str]:
        """The steps in use after ``name``."""
        order = {stage.name: k for k, stage in enumerate(self.stages)}
        return {stage.name for stage in self.stages
                if stage.name in self.used and order[stage.name] > order.get(name, -1)}

    def _toggle(self, name: str, on: bool) -> None:
        """Switch a step on or off: the steps after it are to be made anew, and the step
        itself where what it is handed changed while it was off; a tab that closed is
        left."""
        if on:
            self.used.add(name)
        else:
            self.used.discard(name)
        self.changed = True
        self._stale |= self._later_than(name)
        stage = self._by_name.get(name)
        if on and stage is not None and stage.project is not None \
                and stage.basis != self._basis(stage):
            self._stale.add(name)
        self._stale &= self.used
        self._refresh()
        if not self._leave_closed_tab():
            self._show(self.pages.currentRow())

    def _leave_closed_tab(self) -> bool:
        """Turn to the first open tab where the one shown belongs to a step that is off;
        True when the tab changed (which shows the page)."""
        if self.tabs.count() == 0 or self.tabs.isTabEnabled(self.tabs.currentIndex()):
            return False
        for index in range(self.tabs.count()):
            if self.tabs.isTabEnabled(index):
                self.tabs.setCurrentIndex(index)
                return True
        return False

    # -- the steps joined ----------------------------------------------------------------------
    def _config_bytes(self, stage: Stage, pending: dict[str, Any]) -> bytes:
        """A step's configuration document as it stands: of its project (the one just opened
        where there is one), else the chain document's, else that it starts fresh."""
        project = pending.get(stage.name, stage.project)
        if project is not None:
            return documents.document_bytes(stage.adapter.config(project))
        held = self.chain.configs.get(stage.name)
        return documents.document_bytes(held) if held is not None else b"fresh"

    def _basis(self, stage: Stage, pending: dict[str, Any] | None = None) -> bytes:
        """What a step stands on, named: the originals, and for every step before it
        whether it is in use and its configuration document (which names its input, so
        that what it was handed is in it as well)."""
        pending = pending or {}
        parts = [str(o).encode() for o in self.chain.originals]
        for earlier in self.stages:
            if earlier is stage:
                break
            if earlier.name not in self.used:
                parts.append(earlier.name.encode() + b":off")
            else:
                parts.append(earlier.name.encode() + b":" + self._config_bytes(earlier, pending))
        return b"\n".join(parts)

    def _given(self, stage: Stage, pending: dict[str, Any]) -> Path | list[Path]:
        """What a step is handed: what the step in use before it gives, else the original
        (the originals, to the step that binds pictures)."""
        before = [s for s in self.stages[:self.stages.index(stage)] if s.name in self.used]
        if not before:
            return list(self.chain.originals) if stage.step.takes == "pictures" \
                else self.chain.original
        return self._output(before[-1], pending)

    def _output(self, stage: Stage, pending: dict[str, Any]) -> Path:
        """The file a step gives as it stands, written once for what it was made from (in a
        folder of its own each time, so that an old project can still be closed cleanly)."""
        key = self._basis(stage, pending) + b"\n" + self._config_bytes(stage, pending)
        if stage.output is not None and stage.output[0] == key:
            return stage.output[1]
        self._round += 1
        folder = self.work / stage.name / str(self._round)
        project = pending.get(stage.name, stage.project)
        made: Path = stage.adapter.write(project, folder, self.chain.original.stem,
                                         None)["document"]
        stage.output = (key, made)
        return made

    def _current(self, stage: Stage) -> bool:
        """True when a step is opened on what the steps before it give now."""
        return stage.project is not None and stage.basis == self._basis(stage)

    def _bring(self, target: Stage) -> list[Opened]:
        """Open every step in use up to ``target`` that is not open on what the steps before
        it give now, in their order, each with what it held (its project's configuration
        document, else the chain document's); a step whose rule refuses what it held starts
        anew.  Off the window's thread: nothing here touches a panel."""
        pending: dict[str, Any] = {}
        opened: list[Opened] = []
        for stage in self.stages:
            if stage.name in self.used:
                basis = self._basis(stage, pending)
                if stage.project is None or stage.basis != basis:
                    given = self._given(stage, pending)
                    held = (stage.adapter.config(stage.project) if stage.project is not None
                            else self.chain.configs.get(stage.name))
                    folder = self.work / stage.name
                    anew = False
                    try:
                        project = self.chain.opened(stage.adapter, given, held, folder)
                    except DocError as e:
                        if e.kind != "config-mismatch" or held is None:
                            raise
                        project, anew = self.chain.opened(stage.adapter, given, None, folder), True
                    pending[stage.name] = project
                    opened.append(Opened(stage, project, given, basis,
                                         list(stage.adapter.dropped(project)), anew))
            if stage is target:
                break
        return opened

    def _put(self, opened: list[Opened]) -> None:
        """Put the steps opened anew in place: in their panels (made the first time), the
        old projects closed; and say what became of what a person had decided in them."""
        notes = []
        for done in opened:
            stage, old = done.stage, done.stage.project
            decided = old is not None and registry.by_person(stage.adapter, old)
            stage.project, stage.given, stage.basis = done.project, done.given, done.basis
            self._stale.discard(stage.name)
            if not stage.panels:
                self._make_panels(stage)
            else:
                for panel in stage.panels:
                    panel.project = done.project
                    if hasattr(panel, "show_project"):
                        panel.show_project()
            if old is not None:
                stage.adapter.close(old)
            if decided and done.anew:
                notes.append(self.w("chain_anew", step=stage.name))
            elif decided and done.dropped:
                pages = ", ".join(str(n + 1) for n in done.dropped)
                notes.append(self.w("dropped_pages", step=stage.name, pages=pages))
            elif decided:
                notes.append(self.w("kept_decisions", step=stage.name))
        if opened:
            self._note = " ".join(notes)
        self.status.setText(self._note)

    def _make_panels(self, stage: Stage) -> None:
        """A step's panels, in the place of its placeholders."""
        if not hasattr(stage.adapter, "panels"):
            return
        made = list(stage.adapter.panels(stage.project, self.w, self._work_of_panel))
        current = self.tabs.currentIndex()
        self.tabs.blockSignals(True)
        try:
            for index, panel in zip(stage.tabs, made, strict=True):
                if hasattr(panel, "changed"):
                    panel.changed.connect(lambda *_a, name=stage.name: self._worked_in(name))
                label = self.tabs.tabText(index)
                self.tabs.removeTab(index)
                self.tabs.insertTab(index, panel, label)
            self.tabs.setCurrentIndex(current)
        finally:
            self.tabs.blockSignals(False)
        stage.panels = made

    def _work_of_panel(self, job: Callable[[], object], then: Callable[[], None],
                       status: str) -> None:
        """Work a panel asks for (reading a page, finding its areas), off the window's
        thread, with what it is doing in the status line; then the panel goes on."""
        self.status.setText(status)
        self._run(job, lambda _r: self._done(then))

    def _stage_of_tab(self) -> Stage | None:
        """The step the open tab belongs to."""
        index = self.tabs.currentIndex()
        return self._tab_stage[index] if 0 <= index < len(self._tab_stage) else None

    def _show(self, n: int) -> None:
        """Show page ``n`` in the tab that is open, its step first brought up to what the
        steps before it give now."""
        if n < 0:
            return
        self._commit_panels()
        stage = self._stage_of_tab()
        if stage is None or stage.name not in self.used:  # no tab of a step in use is open
            self._refresh()
            return
        if not self._current(stage):
            self.status.setText(self.w("bringing", step=stage.name))

            def then(opened: list[Opened]) -> None:
                self._put(opened)
                self._show(n)

            self._run(lambda: self._bring(stage), then)
            return
        self._stale.discard(stage.name)  # it stands on what the steps before it give now
        self._show_now(n)

    def _show_now(self, n: int) -> None:
        """Show page ``n`` in the tab that is open (a panel of the whole document shows
        that)."""
        self._mark_pages()
        self._refresh()
        current = self.tabs.currentWidget()
        if hasattr(current, "show_page"):
            current.show_page(n)

    def _corrected(self) -> set[int]:
        """The pages a person corrected, in any step that says so."""
        found: set[int] = set()
        for stage in self.stages:
            if stage.project is not None and hasattr(stage.adapter, "corrected"):
                found |= set(stage.adapter.corrected(stage.project))
        return found

    def _mark_pages(self) -> None:
        """Mark the pages whose text was corrected."""
        corrected = self._corrected()
        for n in range(self.pages.count()):
            item = self.pages.item(n)
            if item is not None:
                item.setText(self.w("page_corrected" if n in corrected else "page",
                                    number=n + 1))

    def _worked_in(self, name: str, *_given: object) -> None:
        """Something changed in a step: the steps in use after it are to be made anew."""
        self.changed = True
        self._stale |= self._later_than(name)
        self._refresh()

    def _commit_panels(self) -> None:
        """Take what was typed into the panels into their projects."""
        for stage in self.stages:
            for panel in stage.panels:
                if hasattr(panel, "commit"):
                    panel.commit()

    def configs(self) -> dict[str, dict[str, Any]]:
        """The configuration documents of the steps as the window holds them: of the steps
        in use, and of those switched off that hold something to keep (a person's
        decisions, or what the chain document held).  A step's document is as its project
        stands, else as the chain document had it; where what it stood on changed since,
        the chain brings it over by the step's own rule, as the window would have."""
        self._commit_panels()
        found: dict[str, dict[str, Any]] = {}
        held = self.chain.configs
        for stage in self.stages:
            if stage.project is not None:
                if stage.name in self.used or stage.name in held \
                        or registry.by_person(stage.adapter, stage.project):
                    found[stage.name] = stage.adapter.config(stage.project)
            elif stage.name in held:
                found[stage.name] = held[stage.name]
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

    def _done(self, then: Callable[[], None]) -> None:
        """A page's work is done: the status line says again what became of the person's
        decisions (if anything did), and the panel goes on."""
        self.status.setText(self._note)
        then()

    # -- the ways out --------------------------------------------------------------------------
    def apply(self) -> None:
        """Close with "applied": the results are to be written."""
        self._commit_panels()
        self.outcome = "applied"
        self.close()

    def later(self) -> None:
        """Close with "saved": the chain document is to be written."""
        self._commit_panels()
        self.outcome = "saved"
        self.close()

    def cancel(self) -> None:
        """Close with "cancelled": nothing is written."""
        self.outcome = "cancelled"
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Closing the window without a choice cancels; after changes, ask first."""
        if self.outcome is None:
            self._commit_panels()
            worked = self.changed or bool(self._corrected())
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
        for stage in self.stages:
            if stage.project is not None:
                stage.adapter.close(stage.project)
                stage.project = None

    # -- the self-test of the standalone program ------------------------------------------------
    def self_test(self) -> None:
        """Go through the window once without a person: every open tab of the first page,
        then apply."""
        for index in range(self.tabs.count()):
            if self.tabs.isTabEnabled(index):
                self.tabs.setCurrentIndex(index)
        self.apply()
