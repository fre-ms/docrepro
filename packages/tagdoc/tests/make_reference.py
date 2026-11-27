"""Make the reference of the standard's library again: the pictures tagdoc's tests compare
in ``tests/reference/``, and in ``tests/reference/reference.json`` what the reference library
of medRDS writes and reads for them, by SHA-256.  The tests compare tagdoc's bytes with these
everywhere, without the library; where it is at hand, one test also asks it again.

Run where Node and the library are (``MEDRDS``, else ``medRDS`` beside this repository),
whenever the library changes what it writes, in this package's folder::

    uv run python -m tests.make_reference

The pictures are invented and small, and made once: they are kept as files, since another
version of Pillow or libheif would make other bytes of the same drawing.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

FOLDER = Path(__file__).resolve().parent / "reference"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schema_digest(text: str) -> str:
    """The SHA-256 of a schema's content, whatever its line endings (git writes text with
    CRLF on Windows): of its JSON, written in one way."""
    canonical = json.dumps(json.loads(text), ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return sha(canonical.encode("utf-8"))


def pictures() -> dict[str, tuple[str, bytes]]:
    """The pictures compared: every type with and without a camera's EXIF, a WebP in its
    simple format, and a HEIC in each of the layouts other programs write."""
    from tests.test_formats import SAVE, _heic_as, drawing, picture

    small = drawing(64, 48)
    cases: dict[str, tuple[str, bytes]] = {}
    for ending in SAVE:
        for with_exif in (True, False):
            cases[f"{ending}-{'exif' if with_exif else 'plain'}"] = (
                ending, picture(ending, with_exif, small))
    cases["webp-simple"] = ("webp", picture("webp", False, small, lossless=True))
    layouts: dict[str, dict[str, Any]] = {
        "v1": {"version": 1}, "v2-8": {"version": 2, "offset_size": 8},
        "no-base": {"version": 1, "base_size": 0}, "meta-last": {"meta_last": True},
        "open": {"open_ended": True}, "idat": {"version": 1, "in_list": True}}
    heic = picture("heic", True, small)
    for name, layout in layouts.items():
        cases[f"heic-{name}"] = ("heic", _heic_as(heic, **layout))
    return cases


def library(medrds: Path, script: str, given: Any) -> Any:
    """Run ``script`` (a module; ``lib`` and ``schema`` stand for the library's index and
    its schema, ``given`` for what is handed in) and return what it prints, as JSON."""
    prelude = (
        "import { readFileSync, writeFileSync } from 'node:fs';"
        f"import * as lib from '{(medrds / 'lib' / 'index.mjs').as_posix()}';"
        "const schema = JSON.parse(readFileSync("
        f"'{(medrds / 'schema' / 'medrds.json').as_posix()}', 'utf8'));"
        "const given = JSON.parse(readFileSync(0, 'utf8'));")
    run = subprocess.run(["node", "--input-type=module", "-e", prelude + script],
                         input=json.dumps(given), capture_output=True, text=True, check=True)
    return json.loads(run.stdout)


def reference(medrds: Path, folder: Path, cases: dict[str, tuple[str, bytes]]) -> dict[str, Any]:
    """What the library writes and reads for the pictures in ``folder`` (named as ``cases``
    names them), the packet it writes, and its schema."""
    from tests.test_formats import META
    from tests.test_medrds import META as FIELDS

    files = {name: str(folder / f"{name}.{ending}") for name, (ending, _d) in cases.items()}
    written = library(medrds, (
        "const out = {};"
        "const hash = (b) => lib.sha256(b);"
        "for (const [name, [ext, file]] of Object.entries(given.files)) {"
        "  const data = new Uint8Array(readFileSync(file));"
        "  const once = lib.writePicture(data, ext, given.meta, schema);"
        "  const twice = lib.writePicture(once.bytes, ext, { title: 'Neu', kind: 'lab' }, schema);"
        "  out[name] = { ending: ext, input: await hash(data), once: await hash(once.bytes),"
        "    written: once.written, twice: await hash(twice.bytes),"
        "    read: await lib.readMetadata(once.bytes, ext, schema) };"
        "}"
        "const packet = lib.serialiseXmp(given.meta, schema);"
        "const embedded = {};"
        "for (const [name, [ext, file]] of Object.entries(given.files)) {"
        "  if (ext !== 'jpg' && ext !== 'png') continue;"
        "  const data = new Uint8Array(readFileSync(file));"
        "  const put = ext === 'jpg' ? lib.embedXmpJpeg(data, packet)"
        "    : lib.embedXmpPng(data, packet);"
        "  embedded[name] = await hash(put);"
        "}"
        "console.log(JSON.stringify({ written: out, embedded, packet,"
        "  fields: lib.serialiseXmp(given.fields, schema) }));"),
        {"files": {n: [cases[n][0], f] for n, f in files.items()}, "meta": META,
         "fields": FIELDS})
    schema = schema_digest((medrds / "schema" / "medrds.json").read_text(encoding="utf-8"))
    head = subprocess.run(["git", "-C", str(medrds), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    version = json.loads((medrds / "package.json").read_text(encoding="utf-8"))["version"]
    return {"library": {"version": version, "commit": head or None},
            "schema": schema, "meta": META, "packet": written["packet"],
            "fields": FIELDS, "fields_packet": written["fields"],
            "embedded": written["embedded"], "written": written["written"]}


def main() -> int:
    from tests.conftest import MEDRDS

    if not (MEDRDS / "lib").is_dir():
        print(f"The reference library is not at {MEDRDS} (set MEDRDS).", file=sys.stderr)
        return 1
    FOLDER.mkdir(exist_ok=True)
    cases = pictures()
    for old in FOLDER.iterdir():
        if old.name != "reference.json":
            old.unlink()
    for name, (ending, data) in cases.items():
        (FOLDER / f"{name}.{ending}").write_bytes(data)
    found = reference(MEDRDS, FOLDER, cases)
    # escaped: the packet begins with the byte-order mark XMP asks for, which is not to stand raw
    (FOLDER / "reference.json").write_text(json.dumps(found, ensure_ascii=True, indent=1,
                                                      sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(cases)} pictures, medRDS {found['library']['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
