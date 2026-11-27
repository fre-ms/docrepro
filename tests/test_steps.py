"""The steps: optdoc and ocrdoc installed, semdoc and tagdoc planned; a step to come joins
the chain in its place by installing it (its adapter through the entry point
``docrepro.steps``)."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Any

import pytest

from docrepro import steps
from docrepro.chain import Chain
from docrepro.errors import DocreproError


def test_the_steps_and_their_order() -> None:
    assert [s.name for s in steps.STEPS] == ["typdoc", "optdoc", "ocrdoc", "semdoc", "tagdoc",
                                             "attdoc"]
    assert [s.order for s in steps.STEPS] == sorted(s.order for s in steps.STEPS)
    assert [s.name for s in steps.STEPS if s.planned] == ["semdoc", "attdoc"]
    assert [s.name for s, _a in steps.installed()] == ["typdoc", "optdoc", "ocrdoc", "tagdoc"]
    typdoc = steps.by_name("typdoc")
    assert typdoc is not None  # the one step that changes the type: no work for a PDF
    assert typdoc.has_work(Path("foto.HEIC")) and not typdoc.has_work(Path("scan.pdf"))
    assert all(s.has_work(Path("scan.pdf")) for s in steps.STEPS if s.name != "typdoc")
    for step in steps.STEPS:
        assert set(step.does) == {"en", "de"}


class _Annotations:
    """A stand-in for semdoc: it takes ocrdoc's PDF and writes it on unchanged, with a
    configuration document of its own."""

    version = "0.0.1"

    def open(self, source: Path, config: dict[str, Any] | None, settings: dict[str, Any],
             scratch: Path) -> Any:
        return {"source": source, "config": config or {"format": "semdoc-annotations"}}

    def config(self, project: Any) -> dict[str, Any]:
        return dict(project["config"])

    def write(self, project: Any, folder: Path, stem: str, progress: Any) -> dict[str, Path]:
        folder.mkdir(parents=True, exist_ok=True)
        pdf = folder / f"{stem}.pdf"
        pdf.write_bytes(project["source"].read_bytes())
        notes = folder / f"{stem}.annotations.json"
        notes.write_text("[]", encoding="utf-8")
        return {"document": pdf, "annotations": notes}

    def dropped(self, project: Any) -> list[int]:
        return []

    def close(self, project: Any) -> None:
        pass


def test_a_step_to_come_joins_by_its_entry_point(tmp_path: Path, report: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """semdoc, once installed, takes its place between ocrdoc and tagdoc, writes its file
    beside the others, and its configuration document goes into the chain document."""
    point = importlib.metadata.EntryPoint("semdoc", "tests.test_steps:_Annotations",
                                          "docrepro.steps")
    real = importlib.metadata.entry_points

    def entry_points(**kwargs: Any) -> Any:
        if kwargs.get("group") == "docrepro.steps":
            return [*real(**kwargs), point]
        return real(**kwargs)

    monkeypatch.setattr(importlib.metadata, "entry_points", entry_points)
    assert [s.name for s, _a in steps.installed()] == ["typdoc", "optdoc", "ocrdoc", "semdoc",
                                                       "tagdoc"]
    answer = Chain.open(report, settings={"reader": "none"}).run(tmp_path / "out")
    assert [s["tool"] for s in answer["steps"] if s["used"]] == ["optdoc", "ocrdoc", "semdoc",
                                                                 "tagdoc"]
    assert answer["not_installed"] == ["attdoc"]
    assert Path(answer["annotations"]).name == "befund.annotations.json"
    chain = Path(answer["config"]).read_text(encoding="utf-8")
    assert '"semdoc-annotations"' in chain and '"semdoc 0.0.1"' in chain
    # semdoc works on ocrdoc's reading: without ocrdoc it cannot be in use
    with pytest.raises(DocreproError) as caught:
        Chain.open(report, settings={"reader": "none"}, without=("ocrdoc",))
    assert (caught.value.kind, caught.value.details) == (
        "step-needs", {"step": "semdoc", "needs": "ocrdoc"})
    fewer = Chain.open(report, without=("ocrdoc", "semdoc")).run(tmp_path / "fewer")
    assert [(s["tool"], s["used"]) for s in fewer["steps"]] == [
        ("typdoc", False), ("optdoc", True), ("ocrdoc", False), ("semdoc", False),
        ("tagdoc", True)]


def test_a_persons_decisions_in_a_configuration_document() -> None:
    """Whether a person decided something in a step, read from its configuration
    document, whatever the step."""
    assert not steps.decided_by_person(None)
    assert not steps.decided_by_person({"pages": [{"plan": {}, "by": "auto"}]})
    assert steps.decided_by_person({"pages": [{"by": "auto"}, {"by": "person"}]})
    assert steps.decided_by_person({"fields": {"title": {"value": "x", "by": "person"}}})
    assert steps.decided_by_person({"pages": [{"correction": "Text", "layout": {"by": "auto"}}]})
    assert not steps.decided_by_person({"pages": [{"correction": None}]})
