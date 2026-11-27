"""Models: docrepro lists those of every step, hands every step the folder of ``--models``,
and never needs one; with the orientation model (``DOCREPRO_MODELS=<folder>``, after
``docrepro models fetch page-orientation --to <folder>``) a scan on its head comes out
upright and read, and the chain document makes it again without the model."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pymupdf
import pytest
from ocrdoc import ocr as ocrlib
from optdoc import models as optdoc_models

from docrepro.chain import Chain, load_chain
from docrepro.cli import main
from tests.synthetic import by_tool, on_its_head

MODELS = Path(os.environ["DOCREPRO_MODELS"]) if os.environ.get("DOCREPRO_MODELS") else None
needs_model = pytest.mark.skipif(
    optdoc_models.orientation(MODELS) is None or not ocrlib.available_backends(),
    reason="needs the orientation model (DOCREPRO_MODELS=<folder>) and an OCR engine")


def _answer(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, dict]:
    status = main(argv)
    return status, json.loads(capsys.readouterr().out)


def test_the_models_of_every_step(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``models list`` names every step's models with the step, where each comes from and
    whether it lies in the folder given; ``about`` lists them too; a name no step lists is
    "unknown-model", said by docrepro."""
    status, answer = _answer(capsys, ["models", "list"])
    assert status == 0
    listed = {m["name"]: m for m in answer["models"]}
    assert listed["page-orientation"]["step"] == "optdoc"
    assert listed["page-orientation"]["url"].startswith("https://")
    assert listed["page-orientation"]["present"] is None
    status, answer = _answer(capsys, ["models", "list", "--models", str(tmp_path)])
    assert status == 0 and all(m["present"] is False for m in answer["models"])
    status, about = _answer(capsys, ["about"])
    assert [(m["step"], m["name"]) for m in about["models"]] == [
        (m["step"], m["name"]) for m in answer["models"]]
    status, answer = _answer(capsys, ["models", "fetch", "nothing", "--to", str(tmp_path)])
    assert status == 2 and answer["error"] == "unknown-model"
    assert "docrepro" in answer["message"]["en"] and list(tmp_path.iterdir()) == []
    status, own = _answer(capsys, ["optdoc", "models", "list"])  # the step's own, as ever
    assert status == 0 and [m["name"] for m in own["models"]] == ["page-orientation"]


def test_every_step_gets_the_folder(tmp_path: Path, report: Path) -> None:
    """The folder of models reaches the steps that take one (optdoc, ocrdoc); a step that
    takes none (tagdoc) is opened as before; the chain document does not name the folder,
    and an empty folder changes nothing of the result."""
    folder = tmp_path / "models"
    folder.mkdir()
    chain = Chain.open(report, settings={"reader": "none"})
    chain.models = folder
    seen = {}
    for step, adapter in chain.steps:
        if step.name not in chain.used:
            continue
        project = chain.opened(adapter, report, None, tmp_path / "work" / step.name)
        try:
            seen[step.name] = getattr(project, "models", "takes none")
        finally:
            adapter.close(project)
    assert seen == {"optdoc": folder, "ocrdoc": folder, "tagdoc": "takes none"}
    assert "typdoc" not in chain.used  # a PDF: nothing to bind
    with_folder = chain.run(tmp_path / "a")
    without = Chain.open(report, settings={"reader": "none"}).run(tmp_path / "b")
    for key in ("document", "config"):
        assert Path(with_folder[key]).read_bytes() == Path(without[key]).read_bytes(), key
    assert "models" not in Path(with_folder["config"]).read_text(encoding="utf-8")


@needs_model
def test_a_scan_on_its_head_comes_out_upright_and_read(
        tmp_path: Path, report: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With the model: optdoc turns the pages, ocrdoc reads them; the chain document says
    the model took part, and makes every file again without it."""
    original = on_its_head(report, tmp_path / "kopf.pdf")
    status, first = _answer(capsys, ["run", str(original), "--out", str(tmp_path / "a"),
                                     "--models", str(MODELS)])
    assert status == 0
    chain = load_chain(first["config"])
    pages = by_tool(chain)["optdoc"]["config"]["pages"]
    assert all(p["plan"]["rotation"] == 180 and p["models"] == ["page-orientation"]
               for p in pages)
    with pymupdf.open(first["document"]) as doc:
        assert "Ramipril" in doc[0].get_text()
    status, again = _answer(capsys, ["run", str(original), "--out", str(tmp_path / "b"),
                                     "--config", first["config"]])
    assert status == 0
    for key in ("document", "reading", "markdown", "config"):
        assert Path(first[key]).read_bytes() == Path(again[key]).read_bytes(), key
