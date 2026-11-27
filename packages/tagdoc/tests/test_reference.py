"""The standard's own library, by what it wrote: for the pictures in ``tests/reference/``
the reference library of medRDS wrote a description into each, read it back, wrote less over
it, serialised the packet and embedded it (``tests/make_reference.py``); tagdoc gives the very
same bytes, here and on every platform, without the library at hand.  Where it is at hand,
the library is asked again, so that a library that changed what it writes is noticed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tagdoc import exif, formats, medrds
from tagdoc.formats import jpeg, png
from tests.conftest import MEDRDS, needs_medrds

FOLDER = Path(__file__).resolve().parent / "reference"
REFERENCE: dict[str, Any] = json.loads((FOLDER / "reference.json").read_text(encoding="utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _input(name: str) -> bytes:
    case = REFERENCE["written"][name]
    data = (FOLDER / f"{name}.{case['ending']}").read_bytes()
    assert _sha(data) == case["input"], f"{name}: not the picture the library was given"
    return data


@pytest.mark.parametrize("name", sorted(REFERENCE["written"]))
def test_the_same_bytes_as_the_library(name: str) -> None:
    """A description written into a picture of every type, in every layout, and written
    again with less: the very bytes the library wrote, in the same places; and what the
    library read back is the description."""
    case = REFERENCE["written"][name]
    ending, data, meta = case["ending"], _input(name), REFERENCE["meta"]
    names = "; ".join(medrds.parse_person(c)[0] or c for c in meta["creator"])
    once, done = formats.written(data, f".{ending}", medrds.merge_xmp(
        formats.held(data, f".{ending}").packet, meta),
        {exif.DESCRIPTION: meta["description"], exif.ARTIST: names})
    assert _sha(once) == case["once"] and list(done) == case["written"]
    twice, _ = formats.written(once, f".{ending}", medrds.merge_xmp(
        formats.held(once, f".{ending}").packet, {"title": "Neu", "kind": "lab"}),
        {exif.DESCRIPTION: None, exif.ARTIST: None})
    assert _sha(twice) == case["twice"]
    assert case["read"] == {k: v for k, v in meta.items() if k in case["read"]}
    assert case["read"]["title"] == "Laborbefund" and case["read"]["kind"] == "lab"


def test_the_same_packet_and_schema_as_the_library() -> None:
    """The packet as the library serialises it, every field of the standard in it; the
    schema tagdoc carries is the library's; and the packet put into a JPEG and a PNG as the
    library puts it."""
    assert medrds.serialise_xmp(REFERENCE["meta"]) == REFERENCE["packet"]
    assert medrds.serialise_xmp(REFERENCE["fields"]) == REFERENCE["fields_packet"]
    from tests.make_reference import schema_digest

    carried = Path(medrds.__file__).parent / "schema" / "medrds.json"
    assert schema_digest(carried.read_text(encoding="utf-8")) == REFERENCE["schema"]
    for name, expected in REFERENCE["embedded"].items():
        data = _input(name)
        put = jpeg.with_packet if name.startswith("jpg") else png.with_packet
        ours = put(data, REFERENCE["packet"])
        assert _sha(ours) == expected, name
        assert put(ours, REFERENCE["packet"]) == ours  # a packet in place of the one there


@needs_medrds
def test_the_reference_is_the_librarys_of_today(tmp_path: Path) -> None:
    """The library at hand writes and reads for these pictures what the reference says it
    did; where not, it changed, and ``tests/make_reference.py`` makes the reference again."""
    from tests.make_reference import reference

    cases = {name: (case["ending"], _input(name)) for name, case in REFERENCE["written"].items()}
    for name, (ending, data) in cases.items():
        (tmp_path / f"{name}.{ending}").write_bytes(data)
    today = reference(MEDRDS, tmp_path, cases)
    for key in ("schema", "packet", "fields_packet", "embedded", "written"):
        assert today[key] == REFERENCE[key], key
