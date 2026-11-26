"""The chain: an original through every installed step, and the document that makes it
again.

``docrepro run <original>`` takes the original (a photo, a scan, any PDF) through the steps
in their order (:mod:`docrepro.steps`): optdoc prepares its pages, ocrdoc reads optdoc's
PDF, and the steps to come (semdoc, tagdoc) take what the one before gave.  Each step
works as on its own, with its own configuration document.  The chain document
(``<stem>.docrepro.json``, format ``docrepro-chain``) holds the original's SHA-256 and the
configuration document of every step, nothing else (no paths, no times), so that

- the original and the chain document give every file again, byte for byte (each step
  reproduces its result, and each step's input is the reproduced result of the one
  before);
- the window (``docrepro edit``) saves it and goes on from it where the person stopped;
- when a person changes an earlier step, a later step keeps what the person decided on a
  page as long as the page's frame stays the same (the steps' own rule); the answer names
  the pages that lost their decisions, per step.

The results are the last step's files under the original's stem, with the PDF carrying
every step's configuration document and the chain document (``docrepro.json``).  What the
steps make on the way is written into a hidden folder inside the results folder and
removed at once: nothing of a document lands anywhere else.
"""

from __future__ import annotations

import contextlib
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pymupdf
from doccor import documents
from doccor.errors import DocError

from docrepro import __version__
from docrepro.errors import DocreproError
from docrepro.steps import STEPS, Adapter, Step, installed

FORMAT = "docrepro-chain"
FORMAT_VERSION = 1
SUFFIX = ".docrepro.json"
EMBEDDED = "docrepro.json"  # the chain document inside the final PDF
WORK = ".docrepro-work"  # the hidden folder inside the results for what the steps make

StepProgress = Callable[[str, int, int], None]  # step, page (from 1), number of pages


def load_chain(path: str | Path) -> dict[str, Any]:
    """A chain document from its file, or from the PDF docrepro wrote, which carries it.
    Raises "missing", or "bad-config" (reason "json" or "format")."""
    try:
        return documents.load_document(path, FORMAT, FORMAT_VERSION, EMBEDDED, "docrepro")
    except DocError as e:  # docrepro's own, so that callers catch one kind of error
        reason = e.details.get("reason")
        raise (DocreproError(e.kind, reason=reason) if reason is not None
               else DocreproError(e.kind)) from e


def _step_configs(chain: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The configuration document of every step a chain document names, by step."""
    steps = chain.get("steps")
    if not isinstance(steps, list):
        raise DocreproError("bad-config", reason="field")
    found: dict[str, dict[str, Any]] = {}
    for entry in steps:
        if not (isinstance(entry, dict) and isinstance(entry.get("tool"), str)
                and isinstance(entry.get("config"), dict)):
            raise DocreproError("bad-config", reason="field")
        found[entry["tool"]] = entry["config"]
    return found


def _per_step(progress: StepProgress | None, step: str) -> Callable[[int, int], None] | None:
    """A step's progress (page, of how many) as the chain's (step, page, of how many)."""
    if progress is None:
        return None
    report = progress

    def each(page: int, of: int) -> None:
        report(step, page, of)

    return each


class Chain:
    """An original and how it goes through the steps: as the chain document given says,
    else fresh with the settings of the steps (``settings``, each step takes those it
    knows: ``paper``, ``photo``, ``colour_pages`` … for optdoc, ``reader``, ``languages``,
    ``cells`` … for ocrdoc)."""

    def __init__(self, original: Path, sha256: str, size: int,
                 configs: dict[str, dict[str, Any]], settings: dict[str, Any]) -> None:
        self.original = original
        self.sha256 = sha256
        self.size = size
        self.configs = configs
        # the program the document is made with, as the steps that describe it name it
        self.settings = {"creator_tool": f"docrepro {__version__}", **settings}
        self.steps: list[tuple[Step, Adapter]] = installed()

    @classmethod
    def open(cls, original: str | Path, chain: dict[str, Any] | None = None,
             settings: dict[str, Any] | None = None) -> Chain:
        """The chain on ``original``.  Raises "missing", "config-mismatch" when the chain
        document belongs to another original, "step-missing" when it names a step that is
        not installed, "bad-config" for a document that makes no sense."""
        original = Path(original)
        if not original.is_file():
            raise DocreproError("missing")
        sha256 = documents.digest(original)
        configs: dict[str, dict[str, Any]] = {}
        if chain is not None:
            named = chain.get("original")
            if not isinstance(named, dict):
                raise DocreproError("bad-config", reason="field")
            if named.get("sha256") != sha256:
                raise DocreproError("config-mismatch")
            configs = _step_configs(chain)
        made = cls(original, sha256, original.stat().st_size, configs, dict(settings or {}))
        known = {step.name for step, _adapter in made.steps}
        for name in configs:
            if name not in known:
                raise DocreproError("step-missing", step=name)
        return made

    # -- the chain document --------------------------------------------------------------------
    def document(self, configs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """The chain document of the given configuration documents, by step, in the
        order of the steps."""
        steps = [{"tool": step.name, "made_with": f"{step.name} {made.version}",
                  "config": configs[step.name]}
                 for step, made in self.steps if step.name in configs]
        return {"format": FORMAT, "version": FORMAT_VERSION,
                "made_with": f"docrepro {__version__}",
                "original": {"sha256": self.sha256, "bytes": self.size,
                             "suffix": self.original.suffix.lower()},
                "steps": steps}

    def save(self, configs: dict[str, dict[str, Any]], path: Path) -> Path:
        """Write the chain document of the given configuration documents; raises
        "unwritable"."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(documents.document_bytes(self.document(configs)))
        except OSError as e:
            raise DocreproError("unwritable") from e
        return path

    # -- making the result ---------------------------------------------------------------------
    @contextlib.contextmanager
    def working(self, out: Path) -> Any:
        """The hidden folder inside the results for what the steps make on the way; it is
        removed afterwards, whatever happened, and so is the results folder when it was
        made for it and stays empty."""
        made = not out.exists()
        work = out / WORK
        try:
            work.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise DocreproError("unwritable") from e
        try:
            yield work
        finally:
            shutil.rmtree(work, ignore_errors=True)
            if made:
                with contextlib.suppress(OSError):
                    out.rmdir()  # only when nothing else is in it

    def run(self, out: str | Path, progress: StepProgress | None = None,
            configs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
        """Take the original through every installed step and write the results into
        ``out``: the last step's files under the original's stem (the PDF carrying every
        configuration document and the chain document), and the chain document.  The
        steps start from ``configs`` (by step) where given, else from the chain document
        the chain was opened with, else fresh.  Returns the answer of the command line."""
        out = Path(out)
        stem = self.original.stem
        if (out / f"{stem}.pdf").resolve() == self.original.resolve():
            raise DocreproError("same-as-source")
        start = dict(self.configs if configs is None else configs)
        made: dict[str, dict[str, Any]] = {}
        report: list[dict[str, Any]] = []
        files: dict[str, Path] = {}
        with self.working(out) as work:
            source = self.original
            for step, adapter in self.steps:
                folder = work / step.name
                project = adapter.open(source, start.get(step.name), self.settings, folder)
                try:
                    paths = adapter.write(project, folder, stem, _per_step(progress, step.name))
                    made[step.name] = adapter.config(project)
                    report.append({"tool": step.name, "made_with": f"{step.name} {adapter.version}",
                                   "dropped": [n + 1 for n in adapter.dropped(project)]})
                finally:
                    adapter.close(project)
                files.update({k: v for k, v in paths.items() if k not in ("pdf", "config")})
                source = paths["pdf"]
            chain = documents.document_bytes(self.document(made))
            written = self._write(out, stem, source, chain, files)
        with pymupdf.open(written["pdf"]) as finished:
            pages = len(finished)
        return {**{k: str(v) for k, v in written.items()}, "pages": pages, "steps": report,
                "not_installed": [s.name for s in STEPS
                                  if s.name not in {t.name for t, _a in self.steps}]}

    def _write(self, out: Path, stem: str, pdf: Path, chain: bytes,
               files: dict[str, Path]) -> dict[str, Path]:
        """The results: the last step's PDF with the chain document inside, the steps'
        other files (the reading, Markdown …) under the original's stem, the chain
        document."""
        doc = pymupdf.open(pdf)
        try:
            carried = [doc.embfile_get(name) for name in sorted(doc.embfile_names())
                       if name.endswith(".json") and name != EMBEDDED]
            if EMBEDDED in doc.embfile_names():
                doc.embfile_del(EMBEDDED)
            documents.embed(doc, EMBEDDED, chain,
                            "docrepro chain: makes this document again from the original")
            finished = documents.finished_pdf(doc, [*carried, chain], f"docrepro {__version__}")
        finally:
            doc.close()
        written = {"pdf": out / f"{stem}.pdf", "config": out / f"{stem}{SUFFIX}"}
        try:
            written["pdf"].write_bytes(finished)
            written["config"].write_bytes(chain)
            for kind, path in files.items():
                target = out / path.name
                shutil.copyfile(path, target)
                written[kind] = target
        except OSError as e:
            raise DocreproError("unwritable") from e
        return written


__all__ = ["EMBEDDED", "FORMAT", "FORMAT_VERSION", "SUFFIX", "Chain", "load_chain"]
