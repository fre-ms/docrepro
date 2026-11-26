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
from tests.synthetic import scan

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
    assert all(s["dropped"] == [] for s in first["steps"])
    assert first["not_installed"] == ["semdoc"]
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == [
        "scan.docrepro.json", "scan.md", "scan.pdf", "scan.reading.json"]
    chain = json.loads(Path(first["config"]).read_text(encoding="utf-8"))
    assert chain["format"] == "docrepro-chain" and chain["version"] == 1
    assert [s["tool"] for s in chain["steps"]] == ["optdoc", "ocrdoc", "tagdoc"]
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
    semdoc = {**document, "steps": [{"tool": "semdoc", "made_with": "semdoc 0.1.0",
                                     "config": {}}]}
    with pytest.raises(DocreproError) as caught:
        Chain.open(report, chain=semdoc)
    assert (caught.value.kind, caught.value.details) == ("step-missing", {"step": "semdoc"})
    for broken in ({**document, "steps": "alle"}, {**document, "original": None},
                   {**document, "steps": [{"tool": "optdoc"}]}):
        with pytest.raises(DocreproError) as caught:
            Chain.open(report, chain=broken)
        assert caught.value.kind == "bad-config"
    with pytest.raises(DocreproError) as caught:
        Chain.open(report).run(report.parent)
    assert caught.value.kind == "same-as-source"
    path = tmp_path / "x.docrepro.json"
    path.write_text(json.dumps({**document, "version": 9}), encoding="utf-8")
    with pytest.raises(DocreproError) as caught:
        load_chain(path)
    assert caught.value.details == {"reason": "format"}
