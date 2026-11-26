"""The steps of docrepro: one tool for one step, in a fixed order.

=========  =====  ==========================================  ===========================
tool       order  its one step                                takes
=========  =====  ==========================================  ===========================
optdoc     10     make the page faithful                      the original (photo, scan)
ocrdoc     20     recognise: areas, text, tables, barcodes    optdoc's PDF
semdoc     30     understand: medical terms, identifying      ocrdoc's reading
                  information (lexterm, lexident); planned
tagdoc     40     describe: title, kind, date, authors (the   ocrdoc's PDF (and, once
                  metadata of medRDS)                         there, semdoc's annotations)
=========  =====  ==========================================  ===========================

Every step keeps the same contract (``docs/family-design.md`` in optdoc): it has a
configuration document of its own (``<stem>.<tool>.json``), from which it makes its
result again byte for byte, and which the PDF it writes carries.  docrepro reaches each
step through an :class:`Adapter`.  optdoc's and ocrdoc's are here; any other step brings
its own through the entry-point group ``docrepro.steps``, named after the step (tagdoc
does; semdoc is to)::

    [project.entry-points."docrepro.steps"]
    semdoc = "semdoc.docrepro:ADAPTER"

so that installing it is all it takes to put it into the chain and the window.  A step
that is not installed is left out; a chain document that names one is refused
("step-missing"), since without it the result cannot be made again.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

Progress = Callable[[int, int], None]  # page (from 1) about to be done, and how many


@dataclass(frozen=True)
class Step:
    """One step of the chain: its tool, its place, what it takes and gives, what it does
    (in English and German), and whether it is still to come."""

    name: str
    order: int
    takes: str
    gives: str
    does: dict[str, str]
    planned: bool = False


STEPS: tuple[Step, ...] = (
    Step("optdoc", 10, "original", "pdf",
         {"en": "makes the page faithful: upright, unwarped, evenly lit, in its colours",
          "de": "macht die Seite getreu: aufrecht, entzerrt, gleichmäßig hell, in ihren Farben"}),
    Step("ocrdoc", 20, "pdf", "pdf, reading",
         {"en": "recognises areas, text, tables and barcodes, and lays the text over the page",
          "de": "erkennt Bereiche, Text, Tabellen und Barcodes und legt den Text über die Seite"}),
    Step("semdoc", 30, "reading", "annotations",
         {"en": "understands the text: medical terms and identifying information",
          "de": "versteht den Text: medizinische Begriffe und identifizierende Angaben"},
         planned=True),
    Step("tagdoc", 40, "pdf", "pdf with metadata (medRDS 7), or a sidecar",
         {"en": "describes the document: title, kind, date, authors, the people it names",
          "de": "beschreibt das Dokument: Titel, Art, Datum, Autoren, die Personen darin"}),
)


class Adapter(Protocol):
    """How docrepro works a step: open its project on the input (fresh, or as its
    configuration document says), give its configuration document, make and write its
    result, and say which pages lost a person's decisions because the input changed.
    A step's project is the tool's own object; docrepro hands it back unopened."""

    version: str

    def open(self, source: Path, config: dict[str, Any] | None,
             settings: dict[str, Any], scratch: Path) -> Any:
        """The step's project on ``source``: fresh with ``settings``, or as ``config``
        left it.  ``scratch`` is a folder for a moment's file, inside the results."""

    def config(self, project: Any) -> dict[str, Any]:
        """The step's configuration document as it is now."""

    def write(self, project: Any, folder: Path, stem: str,
              progress: Progress | None) -> dict[str, Path]:
        """Make the result and write it into ``folder``; its files by kind ("pdf", and
        what else the step writes)."""

    def dropped(self, project: Any) -> list[int]:
        """The pages (from 0) whose decisions went, since the input changed under them."""

    def close(self, project: Any) -> None:
        """Release the project."""


class OptdocAdapter:
    """optdoc: the original in, the prepared PDF out."""

    def __init__(self) -> None:
        import optdoc

        self.version = optdoc.__version__

    def open(self, source: Path, config: dict[str, Any] | None,
             settings: dict[str, Any], scratch: Path) -> Any:
        from optdoc.project import Options, Project

        options = Options(**{k: v for k, v in settings.items()
                             if k in Options.__dataclass_fields__})
        return Project.open(source, None if config else options, config)

    def config(self, project: Any) -> dict[str, Any]:
        return dict(project.config())

    def write(self, project: Any, folder: Path, stem: str,
              progress: Progress | None) -> dict[str, Path]:
        from optdoc import output

        prepared = project.build(progress)
        try:
            return output.write(prepared, folder, stem)
        finally:
            prepared.close()

    def dropped(self, project: Any) -> list[int]:
        return []  # optdoc always starts from the original

    def close(self, project: Any) -> None:
        project.close()


class OcrdocAdapter:
    """ocrdoc: optdoc's PDF in, the same pages with their text, the reading and Markdown
    out."""

    def __init__(self) -> None:
        import ocrdoc

        self.version = ocrdoc.__version__

    def open(self, source: Path, config: dict[str, Any] | None,
             settings: dict[str, Any], scratch: Path) -> Any:
        from ocrdoc.project import Options, Project

        options = Options(**{k: v for k, v in settings.items()
                             if k in Options.__dataclass_fields__})
        project = Project.open(source, None if config else options, config)
        project.scratch = scratch
        return project

    def config(self, project: Any) -> dict[str, Any]:
        return dict(project.config())

    def write(self, project: Any, folder: Path, stem: str,
              progress: Progress | None) -> dict[str, Path]:
        from ocrdoc import output

        reading = project.build(progress)
        try:
            return output.write(reading, folder, stem)
        finally:
            reading.close()

    def dropped(self, project: Any) -> list[int]:
        return list(project.dropped)

    def close(self, project: Any) -> None:
        project.close()


_BUILT_IN: dict[str, Callable[[], Adapter]] = {"optdoc": OptdocAdapter, "ocrdoc": OcrdocAdapter}


def adapter(step: Step) -> Adapter | None:
    """The adapter of a step where its tool is installed: docrepro's own for optdoc and
    ocrdoc, else the one the tool brings (entry point ``docrepro.steps``); None for a step
    that is not installed."""
    if step.name in _BUILT_IN:
        if importlib.util.find_spec(step.name) is None:
            return None
        return _BUILT_IN[step.name]()
    for entry in importlib.metadata.entry_points(group="docrepro.steps"):
        if entry.name == step.name:
            loaded = entry.load()  # an adapter, its class, or a function that makes one
            if isinstance(loaded, type) or (callable(loaded) and not hasattr(loaded, "open")):
                return loaded()
            return loaded
    return None


def installed() -> list[tuple[Step, Adapter]]:
    """The steps whose tools are installed, in their order, with their adapters."""
    found = []
    for step in sorted(STEPS, key=lambda s: s.order):
        made = adapter(step)
        if made is not None:
            found.append((step, made))
    return found


def by_name(name: str) -> Step | None:
    """The step of that name, installed or not."""
    return next((s for s in STEPS if s.name == name), None)
