"""The chain: an original through optdoc and ocrdoc; every file again from the original and
the chain document, byte for byte; a change in optdoc that keeps a page's frame keeps a
person's decisions in ocrdoc, one that moves the page drops them and says so; documents
of another original, or naming a step not installed, are refused; nothing lands outside
the results."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pymupdf
import pytest
from ocrdoc import ocr as ocrlib

from docrepro.chain import EMBEDDED, Chain, load_chain
from docrepro.errors import DocreproError
from tests.synthetic import by_tool, in_use, photo_of, scan

needs_engine = pytest.mark.skipif(not ocrlib.available_backends(), reason="no OCR engine")


def _files(answer: dict) -> dict[str, bytes]:
    return {k: Path(answer[k]).read_bytes() for k in ("document", "reading", "markdown", "config")}


@needs_engine
def test_the_whole_way_again_from_the_chain_document(tmp_path: Path, report: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """A tilted scan through every step; then again from the chain document and from the
    PDF that carries it: every file the same, byte for byte, and nothing written to the
    temporary folder on the way."""
    original = scan(report, tmp_path / "scan.pdf", rotation=1.5)

    def refused(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("nothing may go to the temporary folder")

    for name in ("mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryFile",
                 "TemporaryDirectory", "SpooledTemporaryFile"):
        monkeypatch.setattr(tempfile, name, refused)
    first = Chain.open(original).run(tmp_path / "a")
    assert in_use(first) == [("typdoc", False), ("optdoc", True), ("ocrdoc", True),
                             ("tagdoc", True)]  # the original is a PDF: nothing to bind
    assert all(s["dropped"] == [] for s in first["steps"] if s["used"])
    assert first["not_installed"] == ["semdoc", "attdoc"]
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == [
        "scan.docrepro.json", "scan.md", "scan.pdf", "scan.reading.json"]
    chain = json.loads(Path(first["config"]).read_text(encoding="utf-8"))
    assert chain["format"] == "docrepro-chain" and chain["version"] == 2
    assert in_use(chain) == in_use(first)
    assert by_tool(chain)["typdoc"] == {"tool": "typdoc", "used": False}
    assert by_tool(chain)["optdoc"]["config"]["pages"][0]["plan"]["straighten"] is True
    with pymupdf.open(first["document"]) as doc:
        assert sorted(doc.embfile_names()) == [EMBEDDED, "ocrdoc.json", "optdoc.json",
                                               "tagdoc.json"]
        assert "Ramipril" in doc[0].get_text()
        # tagdoc's description, as medRDS 7.4 says, in step with the information dictionary
        packet = doc.get_xml_metadata()
        assert "<xmp:CreatorTool>docrepro " in packet and "<dc:type><rdf:Bag><rdf:li>" in packet
        assert doc.metadata["creator"].startswith("docrepro ")
    for given in (Path(first["config"]), Path(first["document"])):
        again = Chain.open(original, chain=load_chain(given)).run(tmp_path / given.suffix[1:])
        assert _files(again) == _files(first), given.name


@needs_engine
def test_a_change_in_optdoc_and_a_persons_work_in_ocrdoc(tmp_path: Path, report: Path) -> None:
    """A person corrects a word in ocrdoc.  More contrast in optdoc keeps it (the page did
    not move); straightening switched off moves the page, and the correction goes, with
    the page named."""
    from ocrdoc.project import Project as Reading
    from optdoc.project import Project as Preparation

    original = scan(report, tmp_path / "scan.pdf", rotation=1.5)
    first = Chain.open(original).run(tmp_path / "a")
    chain = load_chain(first["config"])
    configs = {s["tool"]: s["config"] for s in chain["steps"] if "config" in s}
    optdoc_config, ocrdoc_config = configs["optdoc"], configs["ocrdoc"]
    # the person's correction, made in ocrdoc on optdoc's PDF as the chain made it
    work = tmp_path / "work"
    preparation = Preparation.open(original, config=optdoc_config)
    try:
        from optdoc import output

        prepared = preparation.build()
        try:
            pdf = output.write(prepared, work)["document"]
        finally:
            prepared.close()
    finally:
        preparation.close()
    reading = Reading.open(pdf, config=ocrdoc_config)
    try:
        text = reading.text(0)
        reading.set_correction(0, text.replace("Ramipril", "Ramipril (ACE)", 1))
        corrected = reading.config()
    finally:
        reading.close()
    for change, kept in (({"contrast": True}, True), ({"straighten": False}, False)):
        changed = json.loads(json.dumps(optdoc_config))
        changed["pages"][0]["plan"].update(change)
        changed["pages"][0]["by"] = "person"
        made = Chain.open(original).run(tmp_path / f"b-{kept}", configs={
            "optdoc": changed, "ocrdoc": corrected})
        steps = {s["tool"]: s for s in made["steps"]}
        assert steps["ocrdoc"]["dropped"] == ([] if kept else [1])
        page = json.loads(Path(made["reading"]).read_text(encoding="utf-8"))["pages"][0]
        assert ("Ramipril (ACE)" in page["text"]) == kept


def test_refused_chain_documents(tmp_path: Path, report: Path) -> None:
    """A chain document of another original, one that names a step that is not installed,
    and one that makes no sense are refused, each by its kind; the PDF the chain would
    write may not be the original."""
    chain = Chain.open(report)
    document = chain.document({})
    other = tmp_path / "anders.pdf"
    other.write_bytes(report.read_bytes() + b"\n%")
    with pytest.raises(DocreproError) as caught:
        Chain.open(other, chain=document)
    assert caught.value.kind == "config-mismatch"
    semdoc = {**document, "steps": [{"tool": "semdoc", "used": True,
                                     "made_with": "semdoc 0.1.0", "config": {}}]}
    with pytest.raises(DocreproError) as caught:
        Chain.open(report, chain=semdoc)
    assert (caught.value.kind, caught.value.details) == ("step-missing", {"step": "semdoc"})
    for broken in ({**document, "steps": "alle"}, {**document, "original": None},
                   {**document, "steps": [{"tool": "optdoc"}]},
                   {**document, "steps": [{"tool": "optdoc", "used": True}]},
                   {**document, "steps": [{"tool": "optdoc", "used": "ja", "config": {}}]}):
        with pytest.raises(DocreproError) as caught:
            Chain.open(report, chain=broken)
        assert caught.value.kind == "bad-config"
    with pytest.raises(DocreproError) as caught:
        Chain.open(report).run(report.parent)
    assert caught.value.kind == "same-as-source"
    path = tmp_path / "x.docrepro.json"
    for version in (9, 1):  # one to come, and the one before: neither is read
        path.write_text(json.dumps({**document, "version": version}), encoding="utf-8")
        with pytest.raises(DocreproError) as caught:
            load_chain(path)
        assert caught.value.details == {"reason": "format"}


def _embedded(pdf: str) -> list[str]:
    with pymupdf.open(pdf) as doc:
        return sorted(doc.embfile_names())


@needs_engine
def test_every_step_is_optional(tmp_path: Path, report: Path) -> None:
    """OCR without preparation, preparation without OCR, a description alone: a step that
    is off hands on what it got, the answer and the chain document say which steps were
    in use, and the chain document makes the same files again."""
    original = scan(report, tmp_path / "scan.pdf")
    read = Chain.open(original, without=("optdoc",)).run(tmp_path / "read")
    assert in_use(read) == [("typdoc", False), ("optdoc", False), ("ocrdoc", True),
                            ("tagdoc", True)]
    assert by_tool(read)["optdoc"] == {"tool": "optdoc", "used": False}
    assert _embedded(read["document"]) == [EMBEDDED, "ocrdoc.json", "tagdoc.json"]
    with pymupdf.open(read["document"]) as doc:
        assert "Ramipril" in doc[0].get_text()  # ocrdoc read the original as it came
    chain = load_chain(read["config"])
    assert by_tool(chain)["optdoc"] == {"tool": "optdoc", "used": False}
    again = Chain.open(original, chain=chain).run(tmp_path / "read-again")
    assert _files(again) == _files(read)

    prepared = Chain.open(original, without=("ocrdoc", "tagdoc")).run(tmp_path / "prepared")
    assert in_use(prepared)[:2] == [("typdoc", False), ("optdoc", True)]
    assert sorted(p.name for p in (tmp_path / "prepared").iterdir()) == [
        "scan.docrepro.json", "scan.pdf"]
    assert _embedded(prepared["document"]) == [EMBEDDED, "optdoc.json"]
    assert "reading" not in prepared and "markdown" not in prepared
    with pymupdf.open(prepared["document"]) as doc:
        assert doc[0].get_text().strip() == ""  # prepared, not read

    described = Chain.open(report, without=("optdoc", "ocrdoc")).run(tmp_path / "described")
    assert _embedded(described["document"]) == [EMBEDDED, "tagdoc.json"]
    with pymupdf.open(described["document"]) as doc:
        assert "<dc:type>" in doc.get_xml_metadata() and "Ramipril" in doc[0].get_text()
    for key in ("document", "config"):
        once_more = Chain.open(report, chain=load_chain(described["config"])).run(
            tmp_path / "described-again")
        assert Path(once_more[key]).read_bytes() == Path(described[key]).read_bytes(), key

    with pytest.raises(DocreproError) as caught:
        Chain.open(original, without=("optdoc", "ocrdoc", "tagdoc"))
    assert caught.value.kind == "no-steps"


def test_a_picture_goes_on_as_a_pdf_or_stays_a_picture(tmp_path: Path, report: Path) -> None:
    """typdoc binds a picture into a PDF, as medRDS says, and the steps after it take
    that.  Without typdoc a picture stays a picture: optdoc gives back the type it got,
    and the result is that picture with the chain document beside it.  The chain
    document makes the same files again."""
    photo = photo_of(report, tmp_path / "foto.jpg")
    bound = Chain.open(photo, settings={"reader": "none"}).run(tmp_path / "bound")
    assert in_use(bound) == [("typdoc", True), ("optdoc", True), ("ocrdoc", True),
                             ("tagdoc", True)]
    chain = load_chain(bound["config"])
    held = by_tool(chain)["typdoc"]["config"]
    assert held["format"] == "typdoc-config" and held["input"]["pictures"][0]["suffix"] == ".jpg"
    # optdoc was handed typdoc's PDF, not the picture
    assert by_tool(chain)["optdoc"]["config"]["input"]["suffix"] == ".pdf"
    again = Chain.open(photo, chain=chain).run(tmp_path / "bound-again")
    assert _files(again) == _files(bound)
    read = Chain.open(photo, settings={"reader": "none"}, without=("optdoc",)).run(
        tmp_path / "read")  # typdoc alone makes the PDF the later steps take
    assert in_use(read)[:2] == [("typdoc", True), ("optdoc", False)]
    assert _embedded(read["document"]) == [EMBEDDED, "ocrdoc.json", "tagdoc.json"]
    with pymupdf.open(read["document"]) as doc:  # the photo itself is in it, byte for byte
        assert photo.read_bytes() in doc.xref_stream_raw(doc[0].get_images()[0][0])
    # a picture stays a picture: optdoc alone, the type as it came
    kept = Chain.open(photo, without=("typdoc", "ocrdoc", "tagdoc")).run(tmp_path / "kept")
    assert in_use(kept) == [("typdoc", False), ("optdoc", True), ("ocrdoc", False),
                            ("tagdoc", False)]
    assert sorted(p.name for p in (tmp_path / "kept").iterdir()) == [
        "foto.docrepro.json", "foto.jpg"]
    assert Path(kept["document"]).name == "foto.jpg" and kept["pages"] == 1
    assert Path(kept["document"]).read_bytes()[:3] == b"\xff\xd8\xff"  # a JPEG
    held = by_tool(load_chain(kept["config"]))["optdoc"]["config"]
    assert held["input"]["suffix"] == ".jpg" and held["version"] == 3
    once_more = Chain.open(photo, chain=load_chain(kept["config"])).run(tmp_path / "kept-again")
    for key in ("document", "config"):
        assert Path(once_more[key]).read_bytes() == Path(kept[key]).read_bytes(), key
    with pytest.raises(DocreproError) as caught:  # it would replace the picture itself
        Chain.open(photo, without=("typdoc", "ocrdoc", "tagdoc")).run(tmp_path)
    assert caught.value.kind == "same-as-source"


@needs_engine
def test_a_picture_through_every_step_stays_a_picture(tmp_path: Path, report: Path) -> None:
    """With typdoc left out and every other step in use, a picture is prepared, read and
    described as a picture: the description stands in the picture itself (tagdoc writes
    it into the place the format has), what it suggests comes from the reading ocrdoc
    laid beside the picture, and the picture's own data are those optdoc wrote.  The
    chain document makes the same files again; no step needs a PDF."""
    from PIL import Image
    from tagdoc import formats, medrds

    photo = photo_of(report, tmp_path / "foto.jpg")
    whole = Chain.open(photo, without=("typdoc",)).run(tmp_path / "whole")
    assert in_use(whole) == [("typdoc", False), ("optdoc", True), ("ocrdoc", True),
                             ("tagdoc", True)]
    assert sorted(p.name for p in (tmp_path / "whole").iterdir()) == [
        "foto.docrepro.json", "foto.jpg", "foto.md", "foto.reading.json"]
    described = Path(whole["document"]).read_bytes()
    said, standard = medrds.parse_xmp(formats.held(described, ".jpg").packet)
    assert standard and said["creatorTool"].startswith("docrepro ")
    assert said["kind"] == "letter" and said["language"] == ["de"]  # read off the reading
    prepared = Chain.open(photo, without=("typdoc", "ocrdoc", "tagdoc")).run(tmp_path / "kept")
    with Image.open(whole["document"]) as a, Image.open(prepared["document"]) as b:
        assert a.size == b.size and a.tobytes() == b.tobytes()  # the picture optdoc wrote
    page = json.loads(Path(whole["reading"]).read_text(encoding="utf-8"))["pages"][0]
    assert page["unit"] == "px" and "Ramipril" in page["text"]
    chain = load_chain(whole["config"])
    assert by_tool(chain)["tagdoc"]["config"]["input"]["suffix"] == ".jpg"
    again = Chain.open(photo, chain=chain).run(tmp_path / "again")
    assert _files(again) == _files(whole)
    # every step alone, and any of them left out, on the picture itself
    for without in (("typdoc", "optdoc"), ("typdoc", "ocrdoc"), ("typdoc", "optdoc", "ocrdoc")):
        made = Chain.open(photo, without=without, settings={"reader": "none"}).run(
            tmp_path / "-".join(without))
        assert Path(made["document"]).suffix == ".jpg", without
        assert b"<x:xmpmeta" in Path(made["document"]).read_bytes(), without


@needs_engine
def test_a_picture_is_read_as_a_picture(tmp_path: Path, report: Path) -> None:
    """Without typdoc a picture stays a picture through ocrdoc as well: ocrdoc hands on
    the picture optdoc wrote, as it is, and its reading and the Markdown lie beside it,
    the boxes in the picture's pixels.  The chain document makes the same files again.
    What a person corrected in ocrdoc stays when optdoc changes the picture's light and
    goes when it moves the page: ocrdoc finds optdoc's frames in the document beside the
    picture.  With optdoc left out too, ocrdoc reads the picture that came and hands on
    that."""
    from ocrdoc.project import Project as Reading
    from optdoc import output
    from optdoc.project import Project as Preparation
    from PIL import Image

    photo = photo_of(report, tmp_path / "foto.jpg")
    left_out = ("typdoc", "tagdoc")
    read = Chain.open(photo, without=left_out).run(tmp_path / "read")
    assert in_use(read) == [("typdoc", False), ("optdoc", True), ("ocrdoc", True),
                            ("tagdoc", False)]
    assert sorted(p.name for p in (tmp_path / "read").iterdir()) == [
        "foto.docrepro.json", "foto.jpg", "foto.md", "foto.reading.json"]
    kept = Chain.open(photo, without=("typdoc", "ocrdoc", "tagdoc")).run(tmp_path / "kept")
    assert Path(read["document"]).read_bytes() == Path(kept["document"]).read_bytes()
    page = json.loads(Path(read["reading"]).read_text(encoding="utf-8"))["pages"][0]
    with Image.open(read["document"]) as picture:
        assert (page["unit"], page["width"], page["height"]) == ("px", *picture.size)
    assert "Ramipril" in page["text"] and read["pages"] == 1
    chain = load_chain(read["config"])
    again = Chain.open(photo, chain=chain).run(tmp_path / "again")
    assert _files(again) == _files(read)

    configs = {s["tool"]: s["config"] for s in chain["steps"] if "config" in s}
    preparation = Preparation.open(photo, config=configs["optdoc"])
    try:
        prepared = preparation.build()
        try:  # optdoc's picture as the chain made it, its document beside it
            picture_made = output.write(prepared, tmp_path / "work")["document"]
        finally:
            prepared.close()
    finally:
        preparation.close()
    reading = Reading.open(picture_made, config=configs["ocrdoc"])
    try:
        reading.set_correction(0, reading.text(0).replace("Ramipril", "Ramipril (ACE)", 1))
        corrected = reading.config()
    finally:
        reading.close()
    for change, stays in (({"contrast": True}, True), ({"straighten": False}, False)):
        changed = json.loads(json.dumps(configs["optdoc"]))
        changed["pages"][0]["plan"].update(change)
        changed["pages"][0]["by"] = "person"
        made = Chain.open(photo, without=left_out).run(tmp_path / f"b-{stays}", configs={
            "optdoc": changed, "ocrdoc": corrected})
        steps = {s["tool"]: s for s in made["steps"]}
        assert steps["ocrdoc"]["dropped"] == ([] if stays else [1])
        page = json.loads(Path(made["reading"]).read_text(encoding="utf-8"))["pages"][0]
        assert ("Ramipril (ACE)" in page["text"]) == stays

    alone = Chain.open(photo, without=("typdoc", "optdoc", "tagdoc"),
                       settings={"reader": "none"}).run(tmp_path / "alone")
    assert Path(alone["document"]).read_bytes() == photo.read_bytes()
    assert load_chain(alone["config"])["original"]["suffix"] == ".jpg"


def test_a_step_switched_off_keeps_what_it_held(tmp_path: Path, report: Path) -> None:
    """A chain document may say that a step is off and still hold its configuration
    document: the step is passed by, and its document goes on into the next chain
    document, for when the step is switched on again.  So does the entry of a step that
    is not installed and was not in use."""
    first = Chain.open(report, settings={"reader": "none"}).run(tmp_path / "a")
    chain = load_chain(first["config"])
    held = by_tool(chain)["tagdoc"]["config"]
    chain["steps"] = [*(s for s in chain["steps"] if s["tool"] != "tagdoc"),
                      {"tool": "tagdoc", "used": False, "config": held},
                      {"tool": "semdoc", "used": False, "config": {"kept": True}}]
    second = Chain.open(report, chain=chain).run(tmp_path / "b")
    assert in_use(second) == [("typdoc", False), ("optdoc", True), ("ocrdoc", True),
                              ("tagdoc", False)]
    assert _embedded(second["document"]) == [EMBEDDED, "ocrdoc.json", "optdoc.json"]
    written = load_chain(second["config"])
    assert in_use(written) == [("typdoc", False), ("optdoc", True), ("ocrdoc", True),
                               ("semdoc", False), ("tagdoc", False)]
    assert by_tool(written)["tagdoc"] == {"tool": "tagdoc", "used": False, "config": held}
    assert by_tool(written)["semdoc"] == {"tool": "semdoc", "used": False,
                                          "config": {"kept": True}}
    back = {**written, "steps": [*(s for s in written["steps"]  # without the entry carried
                                   if s["tool"] in ("typdoc", "optdoc", "ocrdoc")),
                                 {"tool": "tagdoc", "used": True, "config": held}]}
    third = Chain.open(report, chain=back).run(tmp_path / "c")
    assert Path(third["document"]).read_bytes() == Path(first["document"]).read_bytes()
