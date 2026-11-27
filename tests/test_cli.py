"""The command line: what is installed, the whole way with one answer and progress per
step, every step's own command line under docrepro's, failures by kind without paths,
and the window's self-test giving what run gives."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from ocrdoc import ocr as ocrlib

from docrepro import __version__
from docrepro.cli import INTERFACE, main
from tests.synthetic import scan

needs_engine = pytest.mark.skipif(not ocrlib.available_backends(), reason="no OCR engine")
HEAD = {"interface", "made_with"}
PATIENT = "Mustermann,Erika_1964-08-12_K7Q4MX"  # a file name as records have them


def _answer(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, dict, str]:
    status = main(argv)
    captured = capsys.readouterr()
    return status, json.loads(captured.out), captured.err


def _run(argv: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    """``python -m docrepro`` with ``argv``."""
    return subprocess.run([sys.executable, "-m", "docrepro", *argv], capture_output=True,
                          text=True, check=False, **kwargs)


def test_about(capsys: pytest.CaptureFixture[str]) -> None:
    status, answer, _ = _answer(capsys, ["about"])
    assert status == 0 and answer["interface"] == INTERFACE
    assert answer["made_with"] == f"docrepro {__version__}"
    steps = {s["tool"]: s for s in answer["steps"]}
    assert list(steps) == ["typdoc", "optdoc", "ocrdoc", "tagdoc"]
    assert all(s["installed"] and s["version"] for s in steps.values())
    assert steps["typdoc"]["order"] == 5 and "planned" not in steps["tagdoc"]
    assert set(steps["tagdoc"]["does"]) == {"en", "de"}


def test_every_steps_own_command_line(capsys: pytest.CaptureFixture[str]) -> None:
    """``docrepro optdoc …`` is optdoc's command line, ``docrepro ocrdoc …`` ocrdoc's; what is
    no step of docrepro is no command of it."""
    status, answer, _ = _answer(capsys, ["optdoc", "about"])
    assert status == 0 and answer["made_with"].startswith("optdoc ")
    status, answer, _ = _answer(capsys, ["ocrdoc", "about"])
    assert status == 0 and answer["made_with"].startswith("ocrdoc ")
    status, answer, _ = _answer(capsys, ["tagdoc", "about"])
    assert status == 0 and answer["made_with"].startswith("tagdoc ")
    status, answer, _ = _answer(capsys, ["typdoc", "about"])
    assert status == 0 and answer["made_with"].startswith("typdoc ")
    for other in ("semdoc", "attdoc"):
        status, answer, _ = _answer(capsys, [other, "run", "x.pdf"])
        assert status == 2 and answer["error"] == "usage", other


def test_failures_without_paths(tmp_path: Path, report: Path,
                                capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / PATIENT
    folder.mkdir()
    good = folder / f"{PATIENT}.pdf"
    good.write_bytes(report.read_bytes())
    chain = folder / f"{PATIENT}.docrepro.json"
    chain.write_text("{kaputt", encoding="utf-8")
    cases = {
        "missing": ["run", str(folder / "fehlt.jpg")],
        "usage": ["run", str(good), "--config", str(chain), "--reader", "none"],
        "no-steps": ["run", str(good), "--without", "optdoc", "--without", "ocrdoc",
                     "--without", "tagdoc"],
        "bad-config": ["run", str(good), "--config", str(chain)],
        "same-as-source": ["run", str(good), "--out", str(folder)],
    }
    for kind, argv in cases.items():
        status, answer, err = _answer(capsys, argv)
        assert status == 2 and answer["error"] == kind, kind
        said = json.dumps(answer, ensure_ascii=False) + err
        assert PATIENT not in said and str(tmp_path) not in said, kind
    # an option that is gone (optdoc places no picture on paper any more) is no option
    status, answer, err = _answer(capsys, ["run", str(good), "--paper", "a4"])
    assert status == 2 and answer["error"] == "usage"
    assert PATIENT not in json.dumps(answer, ensure_ascii=False) + err


@needs_engine
def test_run_on_the_command_line(tmp_path: Path, report: Path) -> None:
    """``python -m docrepro run`` with progress per step and page, the results and nothing
    else in the folder, nothing in the temporary, home or cache folder."""
    original = scan(report, tmp_path / "scan.pdf", rotation=1.5)
    elsewhere = {name: tmp_path / name for name in ("tmp", "home", "cache")}
    for folder in elsewhere.values():
        folder.mkdir()
    env = {**os.environ, "TMPDIR": str(elsewhere["tmp"]), "TEMP": str(elsewhere["tmp"]),
           "TMP": str(elsewhere["tmp"]), "HOME": str(elsewhere["home"]),
           "USERPROFILE": str(elsewhere["home"]), "XDG_CACHE_HOME": str(elsewhere["cache"]),
           "PYTHONDONTWRITEBYTECODE": "1", "QT_QPA_PLATFORM": "offscreen"}
    run = _run(["run", str(original), "--out", str(tmp_path / "out"), "--progress"], env=env)
    assert run.returncode == 0, run.stdout
    answer = json.loads(run.stdout)
    assert [(s["tool"], s["used"]) for s in answer["steps"]] == [
        ("typdoc", False), ("optdoc", True), ("ocrdoc", True), ("tagdoc", True)]
    assert answer["pages"] == 2
    lines = [json.loads(z) for z in run.stderr.splitlines()]
    assert lines == [*({"step": s, "page": n, "of": 2} for s in ("optdoc", "ocrdoc")
                       for n in (1, 2)), {"step": "tagdoc", "page": 1, "of": 1}]
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "scan.docrepro.json", "scan.md", "scan.pdf", "scan.reading.json"]
    for name, folder in elsewhere.items():
        assert not any(folder.rglob("*")), name
    # steps left out: the answer says which were in use; beside --config that is a usage
    only = _run(["run", str(original), "--out", str(tmp_path / "only"), "--without", "optdoc",
                 "--without", "tagdoc", "--progress"], env=env)
    assert only.returncode == 0, only.stdout
    assert [(s["tool"], s["used"]) for s in json.loads(only.stdout)["steps"]] == [
        ("typdoc", False), ("optdoc", False), ("ocrdoc", True), ("tagdoc", False)]
    assert {json.loads(z)["step"] for z in only.stderr.splitlines()} == {"ocrdoc"}
    refused = _run(["run", str(original), "--out", str(tmp_path / "x"), "--config",
                    answer["config"], "--without", "tagdoc"], env=env)
    assert refused.returncode == 2 and json.loads(refused.stdout)["error"] == "usage"
    if importlib.util.find_spec("PySide6") is None:
        return
    edit = _run(["edit", str(original), "--out", str(tmp_path / "e"), "--self-test",
                 "--language", "de"], env=env)
    assert edit.returncode == 0, edit.stdout
    edited = json.loads(edit.stdout)
    assert edited["finished"] is True
    for key in ("document", "reading", "markdown", "config"):
        assert Path(edited[key]).read_bytes() == Path(answer[key]).read_bytes(), key
    for name, folder in elsewhere.items():
        assert not any(folder.rglob("*")), name



def test_several_pictures_on_the_command_line(tmp_path: Path, report: Path,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    from tests.synthetic import photo_of

    first = photo_of(report, tmp_path / "eins.jpg")
    second = photo_of(report, tmp_path / "zwei.jpg", rotation=-1.0)
    status, answer, _ = _answer(capsys, ["run", str(first), str(second), "--out",
                                         str(tmp_path / "out"), "--reader", "none"])
    assert status == 0 and answer["pages"] == 2 and answer["interface"] == INTERFACE == 7
    assert Path(answer["document"]).name == "eins.pdf"
    done = _run(["run", str(first), str(second), "--out", str(tmp_path / "each"), "--without",
                 "typdoc", "--without", "ocrdoc", "--without", "tagdoc", "--progress"])
    answer = json.loads(done.stdout)
    assert done.returncode == 0 and [Path(d["document"]).name for d in answer["documents"]] == [
        "eins.jpg", "zwei.jpg"]  # not bound: each a document of its own, a picture still
    lines = [json.loads(line) for line in done.stderr.splitlines()]
    assert {line["document"] for line in lines} == {1, 2} and lines[0]["step"] == "optdoc"
    status, answer, _ = _answer(capsys, ["run", str(first), str(report), "--out",
                                         str(tmp_path / "mixed"), "--reader", "none"])
    assert status == 0 and [Path(d["document"]).name for d in answer["documents"]] == [
        "eins.pdf", "befund.pdf"]  # a PDF among them: typdoc binds none, each by itself
    first_steps = [(s["tool"], s["used"]) for s in answer["documents"][0]["steps"]]
    assert first_steps[0] == ("typdoc", True)  # the picture became a PDF of its own
    assert answer["documents"][1]["steps"][0] == {"tool": "typdoc", "used": False}
    status, answer, _ = _answer(capsys, ["run", str(first), str(second), "--each", "--out",
                                         str(tmp_path / "pdfs"), "--reader", "none"])
    assert status == 0 and [Path(d["document"]).name for d in answer["documents"]] == [
        "eins.pdf", "zwei.pdf"]  # asked for: each picture a PDF of its own
    assert all(d["pages"] == 1 for d in answer["documents"])
    twin = tmp_path / "andere" / "eins.png"
    twin.parent.mkdir()
    twin.write_bytes(b"\x89PNG")
    for argv, kind in (([str(first), str(twin), "--without", "typdoc"], "same-stem"),
                       ([str(first), str(second), "--each", "--config", str(tmp_path / "x.json")],
                        "usage"),
                       ([str(first), "--each"], "usage")):
        status, answer, _ = _answer(capsys, ["run", *argv, "--out", str(tmp_path / "no")])
        assert status == 2 and answer["error"] == kind, argv
    assert not (tmp_path / "no").exists()
    status, answer, _ = _answer(capsys, ["edit", str(first), str(second), "--without", "typdoc"])
    assert status == 2 and answer["error"] == "several-originals"  # the window: one document
