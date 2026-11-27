"""The steps of docrepro, in their order, all four installed: typdoc and tagdoc through their
entry points (``docrepro.steps``), optdoc and ocrdoc through docrepro's own adapters.  What
goes beyond bringing a document near its original (understanding its text, signing it) is
no step of docrepro."""

from __future__ import annotations

from pathlib import Path

from docrepro import steps


def test_the_steps_and_their_order() -> None:
    assert [s.name for s in steps.STEPS] == ["typdoc", "optdoc", "ocrdoc", "tagdoc"]
    assert [s.order for s in steps.STEPS] == sorted(s.order for s in steps.STEPS)
    assert [s.name for s, _a in steps.installed()] == ["typdoc", "optdoc", "ocrdoc", "tagdoc"]
    typdoc = steps.by_name("typdoc")
    assert typdoc is not None  # the one step that changes the type: no work for a PDF
    assert typdoc.has_work([Path("foto.HEIC")]) and not typdoc.has_work([Path("scan.pdf")])
    assert typdoc.has_work([Path("1.jpg"), Path("2.jpg")])
    assert all(s.has_work([Path("scan.pdf")]) for s in steps.STEPS if s.name != "typdoc")
    for step in steps.STEPS:
        assert set(step.does) == {"en", "de"}


def test_a_persons_decisions_in_a_configuration_document() -> None:
    """Whether a person decided something in a step, read from its configuration
    document, whatever the step."""
    assert not steps.decided_by_person(None)
    assert not steps.decided_by_person({"pages": [{"plan": {}, "by": "auto"}]})
    assert steps.decided_by_person({"pages": [{"by": "auto"}, {"by": "person"}]})
    assert steps.decided_by_person({"fields": {"title": {"value": "x", "by": "person"}}})
    assert steps.decided_by_person({"pages": [{"correction": "Text", "layout": {"by": "auto"}}]})
    assert not steps.decided_by_person({"pages": [{"correction": None}]})
