"""The configuration document: what every tool writes for every input, so that its step is
made again, byte for byte, and can be resumed.

A tool's document (``<stem>.<tool>.json``) holds everything that decides the step's result
and nothing else: the settings, what a person decided, and the results of everything that
is not deterministic (what an OCR engine read, what a finder found), so that a
reproduction never runs it again.  No paths, no times.  Its head names the format, its
version, the tool and its version (``made_with``) and the input by its SHA-256.

The same document gives the same bytes (:func:`document_bytes`); a PDF a tool writes
carries the documents of every step that made it, as embedded files without dates
(:func:`embed`), and its file identifier is made from them (:func:`finished_pdf`), so that
the same documents give the same PDF.  :func:`load_document` reads a document from its
file or from such a PDF.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pymupdf

from doccor.errors import DocError


def digest(path: str | Path) -> str:
    """The SHA-256 of a file, as a configuration document names its input."""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def document_bytes(document: dict[str, Any]) -> bytes:
    """A configuration document as the tools write it: JSON, the same bytes for the same
    content."""
    return (json.dumps(document, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def load_document(path: str | Path, format_: str, version: int, embedded: str,
                  tool: str) -> dict[str, Any]:
    """A configuration document of ``format_`` and ``version`` from its file, or from a PDF
    a tool wrote, which carries it as the embedded file ``embedded``.  Raises "missing", or
    "bad-config" (reason "json" or "format") for a file that holds none of them; the
    errors name ``tool``."""
    path = Path(path)
    if not path.is_file():
        raise DocError("missing", tool=tool)
    try:
        if path.suffix.lower() == ".pdf":
            with pymupdf.open(path) as doc:
                if embedded not in doc.embfile_names():
                    raise DocError("bad-config", tool=tool, reason="format")
                raw = doc.embfile_get(embedded)
        else:
            raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except DocError:
        raise
    except Exception as e:
        raise DocError("bad-config", tool=tool, reason="json") from e
    if not isinstance(document, dict) or document.get("format") != format_:
        raise DocError("bad-config", tool=tool, reason="format")
    if document.get("version") != version:
        raise DocError("bad-config", tool=tool, reason="format")
    return document


def embed(doc: pymupdf.Document, name: str, data: bytes, description: str) -> None:
    """Put a configuration document into a PDF as the embedded file ``name``, without the
    dates MuPDF would give it (they would make every run different)."""
    # PyMuPDF returns the xref of the file specification; its type hints say nothing.
    xref: int = doc.embfile_add(  # type: ignore[func-returns-value, assignment]
        name, data, filename=name, desc=description)
    kind, value = doc.xref_get_key(xref, "EF/F")
    stream = int(value.split()[0]) if kind == "xref" else xref
    for key in ("Params/CreationDate", "Params/ModDate"):
        doc.xref_set_key(stream, key, "null")


def finished_pdf(doc: pymupdf.Document, documents: list[bytes], made_with: str) -> bytes:
    """A PDF's bytes, the same for the same configuration documents: the tool named as
    producer and creator, no time in it, and a file identifier made from the documents and
    the tool (``made_with``, "optdoc 0.7.0")."""
    doc.set_metadata({"producer": made_with, "creator": made_with})
    ident = hashlib.sha256(b"".join(documents) + made_with.encode()).hexdigest()[:32].upper()
    doc.xref_set_key(-1, "ID", f"[<{ident}><{ident}>]")
    return doc.tobytes(garbage=3, deflate=True, no_new_id=True)
