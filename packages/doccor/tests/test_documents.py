"""The configuration document: the same bytes for the same content, read from its file or
from a PDF that carries it, refused when it is broken or another; a PDF that carries
documents is the same for the same documents."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from doccor import documents
from doccor.errors import DocError

DOC = {"format": "sometool-config", "version": 1, "made_with": "sometool 1.0",
       "input": {"sha256": "ab" * 32}, "pages": [{"page": 1, "words": ["Kalium", 5.8]}]}


def _pdf(path: Path, docs: list[bytes]) -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Befund")
    for k, data in enumerate(docs):
        documents.embed(doc, f"step{k}.json", data, "how this PDF was made")
    out = documents.finished_pdf(doc, docs, "sometool 1.0")
    doc.close()
    path.write_bytes(out)
    return out


def test_same_content_same_bytes(tmp_path: Path) -> None:
    """A document's bytes depend on its content only; the SHA-256 is the file's."""
    assert documents.document_bytes(DOC) == documents.document_bytes(json.loads(json.dumps(DOC)))
    assert documents.document_bytes(DOC).endswith(b"\n") and "ä" in documents.document_bytes(
        {"x": "ä"}).decode("utf-8")
    f = tmp_path / "f.bin"
    f.write_bytes(b"x" * 3_000_000)
    assert documents.digest(f) == hashlib.sha256(b"x" * 3_000_000).hexdigest()


def test_read_from_its_file_or_its_pdf(tmp_path: Path) -> None:
    """The document comes back from its own file and from a PDF that carries it."""
    data = documents.document_bytes(DOC)
    (tmp_path / "a.sometool.json").write_bytes(data)
    assert documents.load_document(tmp_path / "a.sometool.json", "sometool-config", 1,
                                   "step0.json", "sometool") == DOC
    _pdf(tmp_path / "a.pdf", [data])
    assert documents.load_document(tmp_path / "a.pdf", "sometool-config", 1, "step0.json",
                                   "sometool") == DOC


def test_a_pdf_is_the_same_for_the_same_documents(tmp_path: Path) -> None:
    """Made twice, a PDF that carries documents is the same to the byte; its embedded
    files carry no dates; its identifier follows the documents."""
    data = documents.document_bytes(DOC)
    first = _pdf(tmp_path / "1.pdf", [data])
    assert _pdf(tmp_path / "2.pdf", [data]) == first
    other = _pdf(tmp_path / "3.pdf", [documents.document_bytes({**DOC, "version": 2})])
    with pymupdf.open(tmp_path / "1.pdf") as d, pymupdf.open(tmp_path / "3.pdf") as e:
        assert d.xref_get_key(-1, "ID") != e.xref_get_key(-1, "ID")
        info = d.embfile_info("step0.json")
        assert not info.get("creationDate") and not info.get("modDate")
    assert first != other


def test_broken_or_missing_documents(tmp_path: Path) -> None:
    """Each refusal says why, naming the tool."""
    def kind(path: Path) -> tuple[str, dict]:
        with pytest.raises(DocError) as caught:
            documents.load_document(path, "sometool-config", 1, "step0.json", "sometool")
        assert caught.value.tool == "sometool"
        return caught.value.kind, caught.value.details

    assert kind(tmp_path / "none.json") == ("missing", {})
    for content, reason in (("{broken", "json"), ("[1]", "format"),
                            (json.dumps({**DOC, "format": "other"}), "format"),
                            (json.dumps({**DOC, "version": 9}), "format")):
        (tmp_path / "x.json").write_text(content, encoding="utf-8")
        assert kind(tmp_path / "x.json") == ("bad-config", {"reason": reason})
    _pdf(tmp_path / "plain.pdf", [])
    assert kind(tmp_path / "plain.pdf") == ("bad-config", {"reason": "format"})
