"""Models a step may use: listed with where they come from, fetched on a person's request,
and never otherwise.

Some steps do better with a model (finding the areas of a page, telling handwriting, a page
that stands on its head).  A tool never needs one: every step works by its rules without,
and a model that is missing is no error.  The models are planned in so:

- **A tool lists the models it can use** in its own code (its catalogue of :class:`Model`):
  the address each is fetched from, its SHA-256, its size, its licence and where that is
  stated.  ``<tool> about`` and ``<tool> models list`` show the list.
- **One command goes on the network**, and only on a person's request:
  ``<tool> models fetch <name> --to <folder>`` (:func:`fetch`).  It writes the file into
  the folder under the name the catalogue gives and keeps it only when its SHA-256 is the
  one the catalogue names.  An application may fetch the file itself from the same list.
- **Work never goes on the network.**  ``run`` and ``edit`` take ``--models <folder>`` and
  use what lies there (:func:`present`: the file under its name, with the right SHA-256);
  what does not lie there is done without.
- **What a model found is kept** in the step's configuration document, like the words an
  OCR engine read, so that making the result again needs the model no more.

No request made here carries anything of a document or of the person: the address of the
model, and a client name that says "doccor".
"""

from __future__ import annotations

import contextlib
import hashlib
import http.client
import os
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from doccor import __version__, offline
from doccor.errors import DocError

CHUNK = 1 << 16
Opener = Callable[[str], BinaryIO]
Progress = Callable[[int, int], None]  # bytes fetched so far, and how many there are


@dataclass(frozen=True)
class Model:
    """One model a tool can use: its ``name`` on the command line, the ``file`` it is kept
    as in a models folder, the ``url`` it is fetched from (https), the ``sha256`` and
    ``size`` (bytes) of that file, the ``licence`` of its weights and the ``source`` page
    that states it, and what the step gains by it (``does``, in English and German)."""

    name: str
    file: str
    url: str
    sha256: str
    size: int
    licence: str
    source: str
    does: dict[str, str]

    def as_dict(self, folder: Path | None = None) -> dict[str, Any]:
        """The model for an answer; ``present`` says whether it lies in ``folder`` (None
        without a folder)."""
        return {"name": self.name, "file": self.file, "url": self.url, "sha256": self.sha256,
                "bytes": self.size, "licence": self.licence, "source": self.source,
                "does": dict(self.does),
                "present": None if folder is None else present(self, folder) is not None}


def find(catalogue: Sequence[Model], name: str, tool: str = "doccor") -> Model:
    """The model of that name in a tool's catalogue; raises "unknown-model"."""
    for model in catalogue:
        if model.name == name:
            return model
    raise DocError("unknown-model", tool=tool, name=name)


def digest(path: Path) -> str:
    """The SHA-256 of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


_checked: dict[tuple[str, int, int], str] = {}  # (path, size, time of change) -> SHA-256


def present(model: Model, folder: str | Path | None) -> Path | None:
    """The model's file in a models folder, where it lies there and is the file the
    catalogue names (its size and its SHA-256; hashed once while the file stays as it
    is); None otherwise, also without a folder."""
    if folder is None:
        return None
    path = Path(folder) / model.file
    try:
        stat = path.stat()
    except OSError:
        return None
    if stat.st_size != model.size:
        return None
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if key not in _checked:
        _checked[key] = digest(path)
    return path if _checked[key] == model.sha256 else None


def _open(url: str) -> BinaryIO:
    """Open the address of a model for reading; nothing of a document or a person goes
    with the request."""
    request = urllib.request.Request(url, headers={"User-Agent": f"doccor/{__version__}"})
    return urllib.request.urlopen(request, timeout=60)  # type: ignore[no-any-return]


def fetch(model: Model, folder: str | Path, progress: Progress | None = None,
          opener: Opener | None = None, tool: str = "doccor") -> Path:
    """Fetch a model's file into ``folder`` (made when missing) and return its path.  The
    file is written under a name of its own while it comes, and kept only when it is as
    long as the catalogue says and has its SHA-256; anything else is removed again.  A
    file that lies there already and is the right one is not fetched again.  This is the
    one place a tool goes on the network (:func:`doccor.offline.network_allowed`).
    Raises "model-unreachable" (the address is no https address, or did not answer),
    "model-checksum" (what came is not the file the catalogue names), "unwritable"."""
    folder = Path(folder)
    there = present(model, folder)
    if there is not None:
        return there
    if opener is None and not model.url.startswith("https://"):
        raise DocError("model-unreachable", tool=tool, name=model.name)
    target = folder / model.file
    part = folder / f"{model.file}.part"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DocError("unwritable", tool=tool) from e
    h = hashlib.sha256()
    done = 0
    try:
        try:
            out = part.open("wb")
        except OSError as e:
            raise DocError("unwritable", tool=tool) from e
        with out, offline.network_allowed():
            try:
                with (opener or _open)(model.url) as source:
                    while done <= model.size:  # never more than the catalogue says
                        block = source.read(CHUNK)
                        if not block:
                            break
                        h.update(block)
                        done += len(block)
                        _write(out, block, tool)
                        if progress is not None:
                            progress(min(done, model.size), model.size)
            except (OSError, http.client.HTTPException, ValueError) as e:  # URLError is one
                raise DocError("model-unreachable", tool=tool, name=model.name) from e
        if done != model.size or h.hexdigest() != model.sha256:
            raise DocError("model-checksum", tool=tool, name=model.name)
        try:
            os.replace(part, target)
        except OSError as e:
            raise DocError("unwritable", tool=tool) from e
    finally:
        with contextlib.suppress(OSError):
            part.unlink()
    return target


def _write(out: BinaryIO, block: bytes, tool: str) -> None:
    """Write a block of the file that is coming; "unwritable" where the folder takes no more."""
    try:
        out.write(block)
    except OSError as e:
        raise DocError("unwritable", tool=tool) from e


def listing(catalogue: Sequence[Model], folder: str | Path | None = None) -> list[dict[str, Any]]:
    """A tool's catalogue for an answer (``about``, ``models list``)."""
    return [model.as_dict(None if folder is None else Path(folder)) for model in catalogue]
