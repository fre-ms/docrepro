"""Build docrepro as one executable file with every step inside, and try it out.

    uv sync --extra gui --group build
    uv run python packaging/build.py [--identity "Developer ID Application: …"] [--no-check]
        [--models <folder>]

writes ``dist/docrepro-<target>`` (the name Tauri expects of a sidecar, ``<target>`` being
the Rust target triple of this computer: ``aarch64-apple-darwin`` on a Mac with Apple
silicon), ``dist/docrepro-<target>.sha256`` and ``dist/docrepro-<target>.licences.json``
(the packages inside and their licences).  With ``--onedir`` a folder
``docrepro-<target>-onedir`` instead, with the program ``docrepro`` in it.  Then it runs
the program the way an application will: ``about`` (every step installed, the window
there) and each step's own ``about``; ``run`` on an invented photographed laboratory
report with the temporary, home and cache folders pointed at empty folders, which must
stay empty; ``run --config`` with the chain document it wrote (the same files, byte for
byte); ``edit --self-test`` (the window without a person, off screen); the steps one by
one through their own command lines; a failure, which must answer with its kind; ``run``
with steps left out (prepared only); the
models the steps list (``models list``); on macOS once more with the network closed by the
system (``sandbox-exec``), where that is allowed, and there ``models fetch``, which must
answer that it could not reach the address and keep nothing.  With ``--models <folder>``
(a folder the orientation model was fetched into) also a scan on its head, which must come
out upright and read.  The build itself fetches nothing.
It ends with a summary in JSON: file, size, checksum, timings, checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # the invented documents of the tests

NO_NETWORK = "(version 1)(allow default)(deny network*)"
RESULTS = ["foto.docrepro.json", "foto.md", "foto.pdf", "foto.reading.json"]
STEPS = ["typdoc", "optdoc", "ocrdoc", "tagdoc"]


def target_triple() -> str:
    """The Rust target triple of this computer, which Tauri appends to a sidecar's name."""
    rustc = shutil.which("rustc")
    if rustc:
        out = subprocess.run([rustc, "-vV"], capture_output=True, text=True, check=False).stdout
        for line in out.splitlines():
            if line.startswith("host: "):
                return line.removeprefix("host: ").strip()
    machine = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64",
               "aarch64": "aarch64"}[platform.machine().lower()]
    system = {"darwin": "apple-darwin", "linux": "unknown-linux-gnu",
              "win32": "pc-windows-msvc"}[sys.platform]
    return f"{machine}-{system}"


def build(name: str, identity: str | None, onedir: bool = False) -> Path:
    """Run PyInstaller on the specification; returns the program.  PyInstaller loads ONNX
    Runtime to collect it, which would start its telemetry (see doccor.offline)."""
    env = {**os.environ, "DOCREPRO_BINARY_NAME": name, "ORT_DISABLE_TELEMETRY": "1"}
    if identity:
        env["DOCREPRO_CODESIGN_IDENTITY"] = identity
    if onedir:
        env["DOCREPRO_ONEDIR"] = "1"
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"),
                    str(ROOT / "packaging" / "docrepro.spec")], check=True, env=env, cwd=ROOT)
    suffix = ".exe" if sys.platform == "win32" else ""
    if onedir:
        return ROOT / "dist" / name / f"docrepro{suffix}"
    return ROOT / "dist" / f"{name}{suffix}"


def licences() -> list[dict[str, str]]:
    """The Python distributions the program carries (docrepro with its extra "gui", its
    steps with theirs, and what they need), each with its version and licence as its
    metadata states it."""
    from importlib import metadata

    from packaging.requirements import Requirement

    found: dict[str, dict[str, str]] = {}
    seen: dict[str, set[str]] = {}  # the extras each distribution was walked with
    queue: list[tuple[str, set[str]]] = [("docrepro", {"gui"})]
    while queue:
        name, extras = queue.pop()
        key = name.lower().replace("_", "-")
        new = (extras | {""}) - seen.get(key, set())
        if not new:
            continue
        seen.setdefault(key, set()).update(new)
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        meta = dist.metadata
        licence = (meta.get("License-Expression") or next(
            (c.split(" :: ")[-1] for c in meta.get_all("Classifier") or []
             if c.startswith("License ::")), None) or (meta.get("License") or "").split("\n")[0])
        found[key] = {"name": meta["Name"], "version": dist.version, "licence": licence}
        for text in dist.requires or []:
            requirement = Requirement(text)
            if requirement.marker is None or any(
                    requirement.marker.evaluate({"extra": e}) for e in new):
                queue.append((requirement.name, set(requirement.extras)))
    return sorted(found.values(), key=lambda d: d["name"].lower())


def _run(argv: list[str], env: dict[str, str] | None = None) -> tuple[int, dict, str, float]:
    """Run the program; its status, its answer, its standard error and the seconds taken."""
    start = time.monotonic()
    run = subprocess.run(argv, capture_output=True, text=True, check=False, env=env,
                         timeout=1200)
    seconds = round(time.monotonic() - start, 2)
    return run.returncode, json.loads(run.stdout), run.stderr, seconds


def _left(work: Path, empty: dict[str, Path]) -> list[str]:
    """What lies in the folders that must stay empty."""
    return [str(p.relative_to(work)) for f in empty.values() for p in f.rglob("*")]


def check(program: Path, models: Path | None = None) -> dict[str, object]:
    """Try the program out; raises AssertionError at the first thing that is wrong."""
    from tests.synthetic import on_its_head, photo_of, table_report

    timings: dict[str, float] = {}
    checks: dict[str, str] = {}
    status, answer, _, timings["about"] = _run([str(program), "about"])
    steps = {s["tool"]: s for s in answer["steps"]}
    assert status == 0 and all(steps[name]["installed"] for name in STEPS), answer
    assert answer["window"] and answer["interface"] >= 1, answer
    checks["about"] = answer["made_with"] + ", steps " + ", ".join(
        f"{name} {steps[name]['version']}" for name in STEPS)
    status, typdoc, _, _ = _run([str(program), "typdoc", "about"])
    assert status == 0 and "heic" in typdoc["pictures"] and typdoc["to"] == ["pdf"], typdoc
    status, optdoc, _, _ = _run([str(program), "optdoc", "about"])
    assert status == 0 and optdoc["clean_up"] and optdoc["heic"] and optdoc["window"] \
        and optdoc["upside_down"], optdoc
    status, ocrdoc, _, _ = _run([str(program), "ocrdoc", "about"])
    assert status == 0 and "rapidocr" in ocrdoc["readers"] and ocrdoc["filters"] \
        and ocrdoc["tables"] and ocrdoc["barcodes"] and ocrdoc["window"] \
        and ocrdoc["heic"], ocrdoc
    status, tagdoc, _, _ = _run([str(program), "tagdoc", "about"])
    assert status == 0 and "lab" in tagdoc["kinds"] and tagdoc["window"] and tagdoc["heic"] \
        and tagdoc["places"]["jpg"] == ["xmp", "exif"], tagdoc
    checks["steps"] = (f"typdoc: {typdoc['standard']}; "
                       f"optdoc: clean-up, HEIC, window, upside down; ocrdoc: readers "
                       f"{ocrdoc['readers']}, filters, tables, barcodes, HEIC, window; tagdoc: "
                       f"{tagdoc['standard']}, window")
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        (work / "in").mkdir()
        photo = photo_of(table_report(work / "in" / "befund.pdf"), work / "in" / "foto.jpg")
        empty = {name: work / name for name in ("tmp", "home", "cache")}
        for path in empty.values():
            path.mkdir()
        env = {**os.environ, "TMPDIR": str(empty["tmp"]), "TEMP": str(empty["tmp"]),
               "TMP": str(empty["tmp"]), "HOME": str(empty["home"]),
               "USERPROFILE": str(empty["home"]), "XDG_CACHE_HOME": str(empty["cache"])}
        status, answer, err, timings["run"] = _run(
            [str(program), "run", str(photo), "--out", str(work / "out"), "--progress"], env)
        assert status == 0 and [s["tool"] for s in answer["steps"]] == STEPS, answer
        assert [json.loads(z) for z in err.splitlines()] == [
            {"step": name, "page": 1, "of": 1} for name in STEPS], err
        assert sorted(p.name for p in (work / "out").iterdir()) == RESULTS
        page = json.loads(Path(answer["reading"]).read_text(encoding="utf-8"))["pages"][0]
        assert page["source"] == "ocr" and "Kalium" in page["text"], page["text"][:200]
        assert page["tables"] and len(page["tables"][0]["rows"]) >= 5, page["tables"]
        chain = json.loads(Path(answer["config"]).read_text(encoding="utf-8"))
        described = {s["tool"]: s["config"] for s in chain["steps"]}["tagdoc"]["fields"]
        assert described["kind"]["value"] == "lab", described["kind"]
        assert described["date"]["value"] == "2026-03-12", described["date"]
        assert not _left(work, empty), _left(work, empty)
        checks["run"] = ("photo prepared, read (its table with its rows) and described (kind "
                         "and date), four files, nothing left in tmp, home or cache")
        status, again, _, timings["run --config"] = _run(
            [str(program), "run", str(photo), "--out", str(work / "again"), "--config",
             answer["config"]], env)
        assert status == 0, again
        for key in ("document", "reading", "markdown", "config"):
            assert Path(again[key]).read_bytes() == Path(answer[key]).read_bytes(), key
        checks["reproduced"] = "the same four files again from the chain document, byte for byte"
        status, edited, _, timings["edit --self-test"] = _run(
            [str(program), "edit", str(photo), "--out", str(work / "edited"), "--self-test"],
            {**env, "QT_QPA_PLATFORM": "offscreen"})
        assert status == 0 and edited["finished"], edited
        assert Path(edited["document"]).read_bytes() == Path(answer["document"]).read_bytes()
        assert not _left(work, empty), _left(work, empty)
        checks["window"] = ("opened without a screen, every tab shown, applied, the same PDF, "
                            "nothing left behind")
        second = photo_of(table_report(work / "in" / "befund-2.pdf"), work / "in" / "foto-2.jpg")
        status, several, _, timings["run, two pictures"] = _run(
            [str(program), "run", str(photo), str(second), "--out", str(work / "several")], env)
        assert status == 0 and several["pages"] == 2 and Path(several["document"]).name == \
            "foto.pdf", several
        chain = json.loads(Path(several["config"]).read_text(encoding="utf-8"))
        assert [o["suffix"] for o in chain["originals"]] == [".jpg", ".jpg"], chain["originals"]
        assert not _left(work, empty), _left(work, empty)
        status, each, _, _ = _run(
            [str(program), "run", str(photo), str(second), "--out", str(work / "each"),
             "--without", "typdoc", "--without", "ocrdoc", "--without", "tagdoc"], env)
        assert status == 0 and [Path(d["document"]).name for d in each["documents"]] == [
            "foto.jpg", "foto-2.jpg"], each
        assert not _left(work, empty), _left(work, empty)
        checks["several pictures"] = ("two photos of one document bound into one PDF of two "
                                      "pages; without typdoc each a document of its own")
        status, zero, _, timings["typdoc run"] = _run(
            [str(program), "typdoc", "run", str(photo), "--out", str(work / "s0")], env)
        assert status == 0 and zero["pages"] == 1 and zero["bound"][0]["attached"] is False, zero
        assert photo.read_bytes() in Path(zero["document"]).read_bytes()  # byte for byte
        status, one, _, timings["optdoc run"] = _run(
            [str(program), "optdoc", "run", zero["document"], "--out", str(work / "s1")], env)
        assert status == 0 and one["cleaned_up"] == [1] and one["document"].endswith(".pdf"), one
        status, two, _, timings["ocrdoc run"] = _run(
            [str(program), "ocrdoc", "run", one["document"], "--out", str(work / "s2")], env)
        assert status == 0 and two["ocr_pages"] == [1] and two["carried"] == ["optdoc.json"], two
        status, three, _, timings["tagdoc run"] = _run(
            [str(program), "tagdoc", "run", two["document"], "--out", str(work / "s3")], env)
        assert status == 0 and three["problems"] == [], three
        status, kept, _, _ = _run(  # optdoc on the photo itself: the photo stays a photo
            [str(program), "optdoc", "run", str(photo), "--out", str(work / "s1-kept")], env)
        assert status == 0 and kept["document"].endswith("foto.jpg"), kept
        checks["steps one by one"] = ("typdoc, optdoc, ocrdoc and tagdoc through their own "
                                      "command lines")
        status, answer, _, _ = _run([str(program), "run", str(work / "fehlt.jpg")])
        assert status == 2 and answer["error"] == "missing", answer
        checks["failure"] = "answers with its kind"
        status, answer, _, timings["run --without"] = _run(
            [str(program), "run", str(photo), "--out", str(work / "prepared"), "--without",
             "ocrdoc", "--without", "tagdoc"], env)
        assert status == 0 and [(s["tool"], s["used"]) for s in answer["steps"]] == [
            ("typdoc", True), ("optdoc", True), ("ocrdoc", False), ("tagdoc", False)], answer
        assert sorted(p.name for p in (work / "prepared").iterdir()) == [
            "foto.docrepro.json", "foto.pdf"], list((work / "prepared").iterdir())
        assert not _left(work, empty), _left(work, empty)
        checks["steps left out"] = "prepared only: the PDF and the chain document, nothing else"
        status, answer, _, timings["run, a picture kept"] = _run(
            [str(program), "run", str(photo), "--out", str(work / "kept"), "--without",
             "typdoc"], env)
        assert status == 0 and Path(answer["document"]).name == "foto.jpg", answer
        assert [(s["tool"], s["used"]) for s in answer["steps"]] == [
            ("typdoc", False), ("optdoc", True), ("ocrdoc", True), ("tagdoc", True)], answer
        kept = Path(answer["document"]).read_bytes()
        assert kept[:3] == b"\xff\xd8\xff", "no JPEG"
        assert b"<x:xmpmeta" in kept and b"<dc:type>" in kept, "no description in the picture"
        assert sorted(p.name for p in (work / "kept").iterdir()) == [
            "foto.docrepro.json", "foto.jpg", "foto.md", "foto.reading.json"], \
            list((work / "kept").iterdir())
        read = json.loads(Path(answer["reading"]).read_text(encoding="utf-8"))["pages"][0]
        assert read["unit"] == "px" and read["words"], "the picture was not read in its pixels"
        status, again, _, _ = _run(
            [str(program), "run", str(photo), "--out", str(work / "kept-again"), "--config",
             answer["config"]], env)
        assert status == 0 and Path(again["document"]).read_bytes() == kept, again
        assert not _left(work, empty), _left(work, empty)
        checks["a picture kept"] = ("without typdoc the photo stays a JPEG through every step: "
                                    "prepared, read (the reading beside it) and described (in "
                                    "the picture); the same picture again from the chain "
                                    "document")
        status, answer, _, _ = _run([str(program), "models", "list", "--models",
                                     str(work / "none")], env)
        listed = {m["name"]: m for m in answer.get("models", [])}
        assert status == 0 and listed["page-orientation"]["step"] == "optdoc" \
            and listed["page-orientation"]["present"] is False, answer
        checks["models"] = "listed with their steps: " + ", ".join(
            f"{m['name']} ({m['step']})" for m in listed.values())
        if models is not None:
            status, answer, _, _ = _run([str(program), "models", "list", "--models",
                                         str(models)], env)
            assert status == 0 and any(m["name"] == "page-orientation" and m["present"]
                                       for m in answer["models"]), answer
            turned = on_its_head(work / "in" / "befund.pdf", work / "in" / "kopf.pdf")
            status, answer, _, timings["run --models"] = _run(
                [str(program), "run", str(turned), "--out", str(work / "upright"),
                 "--models", str(models)], env)
            assert status == 0, answer
            chain = json.loads(Path(answer["config"]).read_text(encoding="utf-8"))
            page = {s["tool"]: s for s in chain["steps"]}["optdoc"]["config"]["pages"][0]
            assert page["plan"]["rotation"] == 180 and page["models"] == ["page-orientation"], page
            text = json.loads(Path(answer["reading"]).read_text(encoding="utf-8"))["pages"][0]
            assert "Kalium" in text["text"], text["text"][:200]
            status, again, _, _ = _run(
                [str(program), "run", str(turned), "--out", str(work / "upright-again"),
                 "--config", answer["config"]], env)
            assert status == 0, again
            for key in ("document", "reading", "markdown", "config"):
                assert Path(again[key]).read_bytes() == Path(answer[key]).read_bytes(), key
            assert not _left(work, empty), _left(work, empty)
            checks["models, used"] = ("a scan on its head set upright by the orientation model "
                                      "and read; the same files again without the model")
        checks["network"] = _check_offline(program, photo, work / "offline")
        checks["network, window"] = _check_offline(program, photo, work / "offline-edit",
                                                   window=True)
        checks["network, models fetch"] = _check_no_fetch(program, work / "fetched")
    return {"timings_s": timings, "checks": checks}


def _check_no_fetch(program: Path, folder: Path) -> str:
    """``models fetch`` with the network closed by the system (macOS only): it answers that
    the address could not be reached, and keeps nothing."""
    sandbox = shutil.which("sandbox-exec")
    if sys.platform != "darwin" or sandbox is None:
        return "not checked by the system (no sandbox-exec)"
    run = subprocess.run([sandbox, "-p", NO_NETWORK, str(program), "models", "fetch",
                          "page-orientation", "--to", str(folder)],
                         capture_output=True, text=True, check=False, timeout=300)
    if run.returncode != 0 and not run.stdout.strip():
        return f"not checked by the system (sandbox-exec refused: {run.stderr.strip()[:80]})"
    answer = json.loads(run.stdout)
    assert run.returncode == 2 and answer["error"] == "model-unreachable", answer
    assert not folder.exists() or not list(folder.iterdir()), list(folder.iterdir())
    return "with the network closed it answers model-unreachable and keeps nothing"


def _check_offline(program: Path, photo: Path, out: Path, window: bool = False) -> str:
    """``run`` (or the window's self-test) once more with the network closed by the system
    (macOS only)."""
    sandbox = shutil.which("sandbox-exec")
    if sys.platform != "darwin" or sandbox is None:
        return "not checked by the system (no sandbox-exec)"
    command = ["edit", str(photo), "--out", str(out), "--self-test"] if window else [
        "run", str(photo), "--out", str(out)]
    run = subprocess.run([sandbox, "-p", NO_NETWORK, str(program), *command],
                         capture_output=True, text=True, check=False, timeout=1200,
                         env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    if run.returncode != 0 and not run.stdout.strip():
        return f"not checked by the system (sandbox-exec refused: {run.stderr.strip()[:80]})"
    answer = json.loads(run.stdout)
    assert run.returncode == 0 and [s["tool"] for s in answer["steps"]] == STEPS, answer
    return "the whole way with the network closed by sandbox-exec"


def main() -> int:
    """Build, check, sum up."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--identity", help="macOS signing identity (Developer ID)")
    parser.add_argument("--onedir", action="store_true",
                        help="a folder instead of one file: starts faster (docs/sidecar.md)")
    parser.add_argument("--no-check", action="store_true", help="build only")
    parser.add_argument("--check-only", action="store_true",
                        help="try out the program built before")
    parser.add_argument("--models", type=Path,
                        help="a folder with the orientation model: check that the program "
                             "uses it (the build fetches nothing itself)")
    args = parser.parse_args()
    triple = target_triple()
    name = f"docrepro-{triple}" + ("-onedir" if args.onedir else "")
    if args.check_only:
        suffix = ".exe" if sys.platform == "win32" else ""
        program = (ROOT / "dist" / name / f"docrepro{suffix}" if args.onedir
                   else ROOT / "dist" / f"{name}{suffix}")
    else:
        program = build(name, args.identity, args.onedir)
    digest = hashlib.sha256(program.read_bytes()).hexdigest()
    program.with_name(program.name + ".sha256").write_text(f"{digest}  {program.name}\n",
                                                          encoding="utf-8")
    carried = program.parent / f"docrepro-{triple}.licences.json"
    carried.write_text(json.dumps({
        "python": licences(),
        "note": "Native libraries inside these packages carry their own licences: OpenCV "
                "brings FFmpeg (LGPL), pillow-heif brings libheif and libde265 (LGPL) and x265 "
                "(GPL 2.0 or later), pypdfium2 brings pdfium (Apache 2.0 and BSD), PySide6 "
                "brings Qt (LGPL 3.0); see each package's licence files. tagdoc carries a copy "
                "of the schema of medRDS (MIT).",
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    files = [p for p in program.parent.rglob("*") if p.is_file()] if args.onedir else [program]
    summary: dict[str, object] = {
        "program": str(program.relative_to(ROOT)), "target": triple,
        "size_mb": round(sum(p.stat().st_size for p in files) / 1e6, 1), "sha256": digest,
        "signed": args.identity or "ad hoc" if sys.platform == "darwin" else None,
    }
    if not args.no_check:
        summary.update(check(program, args.models))
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
