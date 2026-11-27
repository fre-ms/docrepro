"""Where the pages of a file came from: for every page, the original file it shows (by its
SHA-256) and which of that file's pages it is (``index``, from 0).

A step that is handed another file than the one its configuration document was made on
compares origins page by page to know whether the new file shows the same pages of the
same document.  A picture and the PDF typdoc bound it into show the same pages and have the
same origins; two letters of the same size never do, however alike their pages lie.

- **A picture**: the file itself; its pages as :mod:`doccor.pictures` counts them (a JPEG
  is one picture, whatever else it holds; a TIFF has a page for each of its pictures).
- **A page of a PDF that names its source** (medRDS 9.5: a file associated with the page,
  ``/AF``, of the relationship ``/Source``): that file; its pages counted in the order the
  PDF shows them, so the second page of a TIFF bound into a PDF is the TIFF's index 1.
- **A page of a PDF that is one JPEG and nothing else** (a single image, filtered by
  ``/DCTDecode`` alone, covering the page, no text): that JPEG, whose bytes are the
  image's stream as it stands in the file.  So it is that a JPEG bound by medRDS 9.5 is
  the JPEG itself.
- **Any other page of a PDF**: the PDF and the page's number.

Every rule is exact: a page's origin is what its bytes say, nothing is guessed.  Where a
page does not say (another PDF), the PDF itself is the original, and a PDF is only ever the
same as itself.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pymupdf

from doccor import documents

COVER = 0.5  # points: an image covers its page where its sides are the page's, to this


def origin(sha256: str, index: int) -> dict[str, Any]:
    """An origin as configuration documents hold it."""
    return {"sha256": sha256, "index": index}


def of(path: str | Path, doc: pymupdf.Document | None = None) -> list[dict[str, Any]]:
    """The origin of every page of ``path``: a picture's or a PDF's (see the module).  For a
    PDF, ``doc`` may be the document already open on it."""
    from doccor import pictures

    path = Path(path)
    if pictures.is_picture(path):
        whole = documents.digest(path)
        return [origin(whole, k) for k in range(pictures.count(path))]
    if doc is not None:
        return _of_pdf(doc, documents.digest(path))
    with pymupdf.open(path) as opened:
        return _of_pdf(opened, documents.digest(path))


def _of_pdf(doc: pymupdf.Document, whole: str) -> list[dict[str, Any]]:
    """The origins of a PDF's pages: their source, else their one JPEG, else the PDF and
    the page's number."""
    seen: dict[int, int] = {}  # a source file's specification, and its pages so far
    found = []
    for n in range(len(doc)):
        page = doc[n]
        source = _source(doc, page)
        if source is not None:
            spec, digest = source
            seen[spec] = seen.get(spec, -1) + 1
            found.append(origin(digest, seen[spec]))
            continue
        jpeg = _one_jpeg(doc, page)
        found.append(origin(jpeg, 0) if jpeg is not None else origin(whole, n))
    return found


_REFERENCE = re.compile(r"(\d+)\s+0\s+R")


def _references(value: tuple[str, str]) -> list[int]:
    """The objects a PDF value refers to: one (``12 0 R``) or an array of them."""
    kind, text = value
    if kind not in ("xref", "array"):
        return []
    return [int(number) for number in _REFERENCE.findall(text)]


def _source(doc: pymupdf.Document, page: pymupdf.Page) -> tuple[int, str] | None:
    """The file a page names as its source (``/AF``, ``/AFRelationship /Source``): its
    specification's object number and the SHA-256 of its bytes; None where it names none."""
    for spec in _references(doc.xref_get_key(page.xref, "AF")):
        if doc.xref_get_key(spec, "AFRelationship") != ("name", "/Source"):
            continue
        files = _references(doc.xref_get_key(spec, "EF/F"))
        if files:
            return spec, hashlib.sha256(doc.xref_stream(files[0])).hexdigest()
    return None


def _one_jpeg(doc: pymupdf.Document, page: pymupdf.Page) -> str | None:
    """The SHA-256 of the JPEG a page is, where it is one JPEG and nothing else (see the
    module); None otherwise."""
    images = page.get_images(full=True)
    if len(images) != 1:
        return None
    xref, smask = images[0][0], images[0][1]
    if smask or doc.xref_get_key(xref, "Filter") != ("name", "/DCTDecode"):
        return None
    if page.get_text("text").strip():
        return None
    rects = page.get_image_rects(xref)
    if len(rects) != 1:
        return None
    drawn = sorted((rects[0].width, rects[0].height))
    sheet = sorted((page.rect.width, page.rect.height))
    if any(abs(a - b) > COVER for a, b in zip(drawn, sheet, strict=True)):
        return None
    return hashlib.sha256(doc.xref_stream_raw(xref)).hexdigest()


def same(a: Any, b: Any) -> bool:
    """True when two origins name the same page of the same file."""
    return (isinstance(a, dict) and isinstance(b, dict)
            and isinstance(a.get("sha256"), str) and a.get("sha256") == b.get("sha256")
            and isinstance(a.get("index"), int) and a.get("index") == b.get("index"))
