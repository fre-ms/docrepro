"""The standard's own library, by what it made: for the pictures in ``tests/reference/`` the
reference library of medRDS bound a PDF of each document, named what it bound, and took every
picture out of it again (``tests/make_reference.py``); typdoc binds the very same PDF, here
and on every platform, without the library at hand.  Where it is at hand, the library is
asked again, so that a library that changed what it writes is noticed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import MEDRDS, needs_medrds
from typdoc import medrds

FOLDER = Path(__file__).resolve().parent / "reference"
REFERENCE: dict[str, Any] = json.loads((FOLDER / "reference.json").read_text(encoding="utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _picture(entry: dict[str, Any]) -> medrds.Picture:
    """A picture as the reference names it, with what is shown of it."""
    shown = entry["shown"]
    given: bytes | list[bytes] | None
    if isinstance(shown, list):
        given = [(FOLDER / one).read_bytes() for one in shown]
    else:
        given = None if shown is None else (FOLDER / shown).read_bytes()
    return medrds.Picture(entry["name"], (FOLDER / entry["file"]).read_bytes(), given)


@pytest.mark.parametrize("k", range(len(REFERENCE["documents"])))
def test_the_same_pdf_as_the_library(k: int) -> None:
    """The pictures of a document bound as the library bound them: the same PDF, byte for
    byte, the same pictures named as bound; and the library took every one of them out of
    that PDF as it went in."""
    document = REFERENCE["documents"][k]
    given = [_picture(entry) for entry in document["pictures"]]
    pdf, bound = medrds.bind(given)
    assert _sha(pdf) == document["pdf"]
    assert bound == document["bound"]
    assert document["unbound"] == [entry["sha256"] for entry in bound]
    assert [entry["sha256"] for entry in bound] == [_sha(p.data) for p in given]


def test_the_standard_named() -> None:
    assert REFERENCE["library"]["version"].startswith(medrds.STANDARD)


@needs_medrds
def test_the_reference_is_the_librarys_of_today() -> None:
    """The library at hand binds these pictures as the reference says it did; where not, it
    changed, and ``tests/make_reference.py`` makes the reference again."""
    from tests.make_reference import reference

    assert medrds.STANDARD in (MEDRDS / "schema" / "medrds.json").read_text(encoding="utf-8")[:200]
    documents = [document["pictures"] for document in REFERENCE["documents"]]
    assert reference(MEDRDS, FOLDER, documents) == REFERENCE["documents"]
