"""The steps of docrepro: one tool for one step, in a fixed order.

=========  =====  ==========================================  ===========================
tool       order  its one step                                takes
=========  =====  ==========================================  ===========================
typdoc     5      change the type: bind pictures into a PDF   the original, a picture
optdoc     10     make the page faithful                      typdoc's PDF, or the original
ocrdoc     20     recognise: areas, text, tables, barcodes    what optdoc gave, PDF or picture
semdoc     30     understand: medical terms, identifying      ocrdoc's reading
                  information (lexterm, lexident); planned
tagdoc     40     describe: title, kind, date, authors (the   what ocrdoc gave (and, once
                  metadata of medRDS)                         there, semdoc's annotations)
attdoc     50     sign: a time stamp, a person's signature    the document as the steps
                  (resting on TimeAttest); planned            before left it
=========  =====  ==========================================  ===========================

Every step keeps the same contract (``docs/family-design.md`` in optdoc): it has a
configuration document of its own (``<stem>.<tool>.json``), from which it makes its
result again byte for byte, and which the PDF it writes carries.  docrepro reaches each
step through an :class:`Adapter`.  optdoc's and ocrdoc's are here; any other step brings
its own through the entry-point group ``docrepro.steps``, named after the step (typdoc
and tagdoc do; semdoc and attdoc are to)::

    [project.entry-points."docrepro.steps"]
    semdoc = "semdoc.docrepro:ADAPTER"

so that installing it is all it takes to put it into the chain and the window.  A step
that is not installed is left out; a chain document that used one is refused
("step-missing"), since without it the result cannot be made again.

**Every step is optional.**  A document goes through the steps that are in use for it and
past the others: a step that is switched off hands on what it got, untouched.  OCR without
preparation, preparation without OCR, a description alone: each is a chain.  What a step
cannot do without another it says itself (``needs``: semdoc needs ocrdoc's reading), and a
step that gets what it cannot take says so with its own error.

**No step forces a file type.**  Only typdoc changes a document's type: it binds pictures
into a PDF as medRDS says, and has nothing to do for an original that is a PDF (it is in
use for pictures alone, unless it is left out).  The steps after it take what they are
handed, typdoc's PDF or the original.  optdoc gives back the type it got: a picture stays
a picture.  ocrdoc reads a picture and hands it on as it came, with its reading beside it.
tagdoc writes its description into the picture where the picture's format has a place for
one, and beside it where it has none.  So a picture goes through every step as a picture
when typdoc is left out, and as a PDF when it is not.

**Models.**  A step may do better with a model, an optional download (:mod:`doccor.models`).
An adapter says so with two members docrepro looks for and does not demand: ``catalogue``,
the models its step can use, and ``use_models(project, folder)``, which hands the step's
project the folder whose models it may use.  docrepro lists the models of every step
(``docrepro models list``), fetches one on request, and gives every step the folder of
``--models``; what a model found is in the step's configuration document, so the chain
document makes the results again without any.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from doccor.models import Model

Progress = Callable[[int, int], None]  # page (from 1) about to be done, and how many


@dataclass(frozen=True)
class Step:
    """One step of the chain: its tool, its place, what it takes and gives, what it does
    (in English and German), whether it is still to come, and the steps it cannot do
    without (``needs``: they must be in use where it is)."""

    name: str
    order: int
    takes: str
    gives: str
    does: dict[str, str]
    planned: bool = False
    needs: tuple[str, ...] = ()

    def has_work(self, original: Path) -> bool:
        """False where the step has nothing to do for an original of that type: the step
        that binds pictures, for a PDF."""
        return not (self.takes == "pictures" and original.suffix.lower() == ".pdf")


STEPS: tuple[Step, ...] = (
    Step("typdoc", 5, "pictures", "pdf",
         {"en": "changes the type: binds pictures into one PDF, each in it byte for byte",
          "de": "ändert den Typ: bindet Bilder zu einem PDF, jedes Byte für Byte darin"}),
    Step("optdoc", 10, "document", "document of the same type",
         {"en": "makes the page faithful: upright, unwarped, evenly lit, in its colours",
          "de": "macht die Seite getreu: aufrecht, entzerrt, gleichmäßig hell, in ihren Farben"}),
    Step("ocrdoc", 20, "document", "document of the same type, reading",
         {"en": "recognises areas, text, tables and barcodes; lays the text over the page of a "
                "PDF, beside a picture",
          "de": "erkennt Bereiche, Text, Tabellen und Barcodes; legt den Text über die Seite "
                "eines PDFs, neben ein Bild"}),
    Step("semdoc", 30, "reading", "annotations",
         {"en": "understands the text: medical terms and identifying information",
          "de": "versteht den Text: medizinische Begriffe und identifizierende Angaben"},
         planned=True, needs=("ocrdoc",)),
    Step("tagdoc", 40, "document", "the document described (medRDS 7), or a sidecar beside it",
         {"en": "describes the document: title, kind, date, authors, the people it names",
          "de": "beschreibt das Dokument: Titel, Art, Datum, Autoren, die Personen darin"}),
    Step("attdoc", 50, "document", "the document signed, or its signature beside it",
         {"en": "signs the document: a time stamp, a person's signature",
          "de": "signiert das Dokument: ein Zeitstempel, die Signatur einer Person"},
         planned=True),
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
        """Make the result and write it into ``folder``; its files by kind: "document",
        the file the next step is handed, and what else the step writes."""

    def dropped(self, project: Any) -> list[int]:
        """The pages (from 0) whose decisions went, since the input changed under them."""

    def close(self, project: Any) -> None:
        """Release the project."""


def by_person(made: Adapter, project: Any) -> bool:
    """True when a person decided something in the step's project: as the adapter says
    (``by_person(project)``, where it has that), else as the step's configuration
    document shows it (an entry decided ``"by": "person"``, a correction)."""
    own = getattr(made, "by_person", None)
    if own is not None:
        return bool(own(project))
    return decided_by_person(made.config(project))


def decided_by_person(config: Any) -> bool:
    """True when a configuration document holds a person's decision: somewhere in it an
    entry ``"by": "person"``, or a correction."""
    if isinstance(config, dict):
        if config.get("by") == "person" or config.get("correction") is not None:
            return True
        return any(decided_by_person(value) for value in config.values())
    if isinstance(config, list):
        return any(decided_by_person(value) for value in config)
    return False


def catalogue(made: Adapter) -> tuple[Model, ...]:
    """The models a step can use, as its adapter lists them; none where it lists none."""
    return tuple(getattr(made, "catalogue", ()))


def opened(made: Adapter, source: Path, config: dict[str, Any] | None,
           settings: dict[str, Any], scratch: Path, models: Path | None) -> Any:
    """A step's project on ``source`` (:meth:`Adapter.open`), with the folder of models it
    may use handed over where the step takes one."""
    project = made.open(source, config, settings, scratch)
    use = getattr(made, "use_models", None)
    if use is not None:
        use(project, models)
    return project


class OptdocAdapter:
    """optdoc: the original in, the prepared PDF out."""

    def __init__(self) -> None:
        import optdoc
        from optdoc.models import CATALOGUE

        self.version = optdoc.__version__
        self.catalogue = CATALOGUE

    def use_models(self, project: Any, folder: Path | None) -> None:
        project.models = folder

    def by_person(self, project: Any) -> bool:
        return bool(project.decided_by_person)

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
    """ocrdoc: what optdoc gave in (a PDF, or a picture); the same pages with their text
    (a picture as it came), the reading and Markdown out."""

    def __init__(self) -> None:
        import ocrdoc
        from ocrdoc.models import CATALOGUE

        self.version = ocrdoc.__version__
        self.catalogue = CATALOGUE

    def use_models(self, project: Any, folder: Path | None) -> None:
        project.models = folder

    def by_person(self, project: Any) -> bool:
        return bool(project.corrected) or any(
            page.filters_by_person or page.regions_by_person for page in project.pages)

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
