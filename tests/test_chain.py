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
from tests.synthetic import photo_of, scan

needs_engine = pytest.mark.skipif(not ocrlib.available_backends(), reason="no OCR engine")


def _files(answer: dict) -> dict[str, bytes]:
    return {k: Path(answer[k]).read_bytes() for k in ("pdf", "reading", "markdown", "config")}


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
    assert [s["tool"] for s in first["steps"]] == ["optdoc", "ocrdoc", "tagdoc"]
    assert all(s["used"] and s["dropped"] == [] for s in first["steps"])
    assert first["not_installed"] == ["semdoc"]
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == [
        "scan.docrepro.json", "scan.md", "scan.pdf", "scan.reading.json"]
    chain = json.loads(Path(first["config"]).read_text(encoding="utf-8"))
    assert chain["format"] == "docrepro-chain" and chain["version"] == 2
    assert [s["tool"] for s in chain["steps"]] == ["optdoc", "ocrdoc", "tagdoc"]
    assert all(s["used"] is True for s in chain["steps"])
    assert chain["steps"][0]["config"]["pages"][0]["plan"]["straighten"] is True
    with pymupdf.open(first["pdf"]) as doc:
        assert sorted(doc.embfile_names()) == [EMBEDDED, "ocrdoc.json", "optdoc.json",
                                               "tagdoc.json"]
        assert "Ramipril" in doc[0].get_text()
        # tagdoc's description, as medRDS 7.4 says, in step with the information dictionary
        packet = doc.get_xml_metadata()
        assert "<xmp:CreatorTool>docrepro " in packet and "<dc:type><rdf:Bag><rdf:li>" in packet
        assert doc.metadata["creator"].startswith("docrepro ")
    for given in (Path(first["config"]), Path(first["pdf"])):
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
    configs = {s["tool"]: s["config"] for s in chain["steps"]}
    optdoc_config, ocrdoc_config = configs["optdoc"], configs["ocrdoc"]
    # the person's correction, made in ocrdoc on optdoc's PDF as the chain made it
    work = tmp_path / "work"
    preparation = Preparation.open(original, config=optdoc_config)
    try:
        from optdoc import output

        prepared = preparation.build()
        try:
            pdf = output.write(prepared, work)["pdf"]
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
    assert [(s["tool"], s["used"]) for s in read["steps"]] == [
        ("optdoc", False), ("ocrdoc", True), ("tagdoc", True)]
    assert "dropped" not in read["steps"][0] and "made_with" not in read["steps"][0]
    assert _embedded(read["pdf"]) == [EMBEDDED, "ocrdoc.json", "tagdoc.json"]
    with pymupdf.open(read["pdf"]) as doc:
        assert "Ramipril" in doc[0].get_text()  # ocrdoc read the original as it came
    chain = load_chain(read["config"])
    assert chain["steps"][0] == {"tool": "optdoc", "used": False}
    again = Chain.open(original, chain=chain).run(tmp_path / "read-again")
    assert _files(again) == _files(read)

    prepared = Chain.open(original, without=("ocrdoc", "tagdoc")).run(tmp_path / "prepared")
    assert sorted(p.name for p in (tmp_path / "prepared").iterdir()) == [
        "scan.docrepro.json", "scan.pdf"]
    assert _embedded(prepared["pdf"]) == [EMBEDDED, "optdoc.json"]
    assert "reading" not in prepared and "markdown" not in prepared
    with pymupdf.open(prepared["pdf"]) as doc:
        assert doc[0].get_text().strip() == ""  # prepared, not read

    described = Chain.open(report, without=("optdoc", "ocrdoc")).run(tmp_path / "described")
    assert _embedded(described["pdf"]) == [EMBEDDED, "tagdoc.json"]
    with pymupdf.open(described["pdf"]) as doc:
        assert "<dc:type>" in doc.get_xml_metadata() and "Ramipril" in doc[0].get_text()
    for key in ("pdf", "config"):
        once_more = Chain.open(report, chain=load_chain(described["config"])).run(
            tmp_path / "described-again")
        assert Path(once_more[key]).read_bytes() == Path(described[key]).read_bytes(), key

    with pytest.raises(DocreproError) as caught:
        Chain.open(original, without=("optdoc", "ocrdoc", "tagdoc"))
    assert caught.value.kind == "no-steps"


def test_a_photo_needs_optdoc_to_become_a_pdf(tmp_path: Path, report: Path) -> None:
    """Where optdoc is off, ocrdoc gets the original; a photo it cannot take, and says so
    itself."""
    from ocrdoc.errors import OcrdocError

    photo = photo_of(report, tmp_path / "foto.jpg")
    with pytest.raises(OcrdocError) as caught:
        Chain.open(photo, without=("optdoc",), settings={"reader": "none"}).run(tmp_path / "out")
    assert caught.value.kind == "not-pdf"
    assert not (tmp_path / "out").exists()  # nothing written, nothing left


def test_a_step_switched_off_keeps_what_it_held(tmp_path: Path, report: Path) -> None:
    """A chain document may say that a step is off and still hold its configuration
    document: the step is passed by, and its document goes on into the next chain
    document, for when the step is switched on again.  So does the entry of a step that
    is not installed and was not in use."""
    first = Chain.open(report, settings={"reader": "none"}).run(tmp_path / "a")
    chain = load_chain(first["config"])
    held = chain["steps"][2]["config"]
    chain["steps"][2] = {"tool": "tagdoc", "used": False, "config": held}
    chain["steps"].append({"tool": "semdoc", "used": False, "config": {"kept": True}})
    second = Chain.open(report, chain=chain).run(tmp_path / "b")
    assert [(s["tool"], s["used"]) for s in second["steps"]] == [
        ("optdoc", True), ("ocrdoc", True), ("tagdoc", False)]
    assert _embedded(second["pdf"]) == [EMBEDDED, "ocrdoc.json", "optdoc.json"]
    written = load_chain(second["config"])
    assert [(s["tool"], s["used"]) for s in written["steps"]] == [
        ("optdoc", True), ("ocrdoc", True), ("semdoc", False), ("tagdoc", False)]
    assert written["steps"][3] == {"tool": "tagdoc", "used": False, "config": held}
    assert written["steps"][2] == {"tool": "semdoc", "used": False, "config": {"kept": True}}
    back = {**written, "steps": [*written["steps"][:2],  # without the entry carried along
                                 {"tool": "tagdoc", "used": True, "config": held}]}
    third = Chain.open(report, chain=back).run(tmp_path / "c")
    assert Path(third["pdf"]).read_bytes() == Path(first["pdf"]).read_bytes()
