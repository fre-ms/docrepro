"""Make the reference of the standard's library again: the pictures typdoc's tests bind in
``tests/reference/`` (with the JPEG a page shows of each picture that is none, which the
caller gives both implementations), and in ``tests/reference/reference.json`` what the
reference library of medRDS made of them, by SHA-256: the PDF it binds, what it names as
bound, and what it takes out of the PDF again.  The tests compare typdoc's PDF with these
everywhere, without the library; where it is at hand, one test also asks it again.

Run where Node and the library are (``MEDRDS``, else ``medRDS`` beside this repository),
whenever the library changes what it writes, in this package's folder::

    uv run python -m tests.make_reference

The pictures are invented and small, and made once: they are kept as files, since another
version of Pillow or libheif would make other bytes of the same letter.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

FOLDER = Path(__file__).resolve().parent / "reference"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cases() -> list[list[tuple[str, bytes, bytes | list[bytes] | None]]]:
    """The documents bound: a photo; pictures of three formats; a photo held in each of the
    eight ways; grey, CMYK, wide, odd sizes, a TIFF and a file without an ending; a TIFF and
    a HEIC of several pictures each beside a photo."""
    from tests.conftest import encoded, letter, several, with_orientation
    from typdoc import pictures

    jpeg = encoded(letter(105, 148), "JPEG", quality=85)
    png = encoded(letter(105, 148, mode="RGBA"), "PNG")
    heic = encoded(letter(105, 148), "HEIF", quality=80)
    grey_tiff = encoded(letter(105, 148, mode="L"), "TIFF")
    pages = several(letter(105, 148, mode="L"), letter(75, 50), letter(105, 148), form="TIFF")
    two = several(letter(105, 148), letter(125, 88), form="HEIF")
    return [
        [("picture-1.jpg", jpeg, None)],
        [("IMG_1.jpeg", jpeg, None), ("Seite 2 – Anlage.png", png, pictures.shown(png)),
         ("picture-3.heic", heic, pictures.shown(heic))],
        [(f"turned-{n}.jpg", with_orientation(jpeg, n), None) for n in range(1, 9)],
        [("grey.jpg", encoded(letter(105, 148, mode="L"), "JPEG"), None),
         ("cmyk.jpg", encoded(letter(105, 148).convert("CMYK"), "JPEG"), None),
         ("wide.jpg", encoded(letter(225, 75), "JPEG"), None),
         ("odd.jpg", encoded(letter(83, 129), "JPEG"), None),
         ("scan.tiff", grey_tiff, pictures.shown(grey_tiff)),
         ("ohne-endung", png, pictures.shown(png))],
        [("seiten.tiff", pages, pictures.shown(pages)), ("foto.jpg", jpeg, None),
         ("zwei.heic", two, pictures.shown(two))],
    ]


def kept(folder: Path, number: int, case: list[tuple[str, bytes, Any]]) -> list[dict[str, Any]]:
    """Write a document's pictures, and what is shown of them, into ``folder``; how they
    are named there."""
    listed = []
    for n, (name, data, shown) in enumerate(case):
        stem = f"{number}-{n}"
        (folder / f"{stem}.picture").write_bytes(data)
        given: list[str] | str | None = None
        if isinstance(shown, list):
            given = []
            for k, one in enumerate(shown):
                (folder / f"{stem}-{k}.shown.jpg").write_bytes(one)
                given.append(f"{stem}-{k}.shown.jpg")
        elif shown is not None:
            (folder / f"{stem}.shown.jpg").write_bytes(shown)
            given = f"{stem}.shown.jpg"
        listed.append({"name": name, "file": f"{stem}.picture", "shown": given})
    return listed


def reference(medrds: Path, folder: Path, documents: list[list[dict[str, Any]]]
              ) -> list[dict[str, Any]]:
    """What the library makes of the documents whose pictures lie in ``folder``."""
    script = (
        "import { readFileSync } from 'node:fs';"
        f"import * as lib from '{(medrds / 'lib' / 'index.mjs').as_posix()}';"
        "const { folder, documents } = JSON.parse(readFileSync(0, 'utf8'));"
        "const read = (file) => new Uint8Array(readFileSync(`${folder}/${file}`));"
        "const out = [];"
        "for (const listed of documents) {"
        "  const pictures = listed.map((p) => ({ name: p.name, bytes: read(p.file),"
        "    ...(p.shown ? { shown: Array.isArray(p.shown) ? p.shown.map(read) : read(p.shown) }"
        "    : {}) }));"
        "  const { bytes, bound } = await lib.bindPictures(pictures);"
        "  const taken = await lib.boundFiles(bytes);"
        "  out.push({ pictures: listed, pdf: await lib.sha256(bytes), bound,"
        "    unbound: await Promise.all(taken.map((b) => (b ? lib.sha256(b) : null))) });"
        "}"
        "console.log(JSON.stringify(out));")
    run = subprocess.run(["node", "--input-type=module", "-e", script],
                         input=json.dumps({"folder": folder.as_posix(), "documents": documents}),
                         capture_output=True, text=True, check=True)
    return list(json.loads(run.stdout))


def main() -> int:
    from tests.conftest import MEDRDS

    if not (MEDRDS / "lib").is_dir():
        print(f"The reference library is not at {MEDRDS} (set MEDRDS).", file=sys.stderr)
        return 1
    if FOLDER.exists():
        shutil.rmtree(FOLDER)
    FOLDER.mkdir()
    documents = [kept(FOLDER, k, case) for k, case in enumerate(cases())]
    found = reference(MEDRDS, FOLDER, documents)
    head = subprocess.run(["git", "-C", str(MEDRDS), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    version = json.loads((MEDRDS / "package.json").read_text(encoding="utf-8"))["version"]
    whole = {"library": {"version": version, "commit": head or None}, "documents": found}
    (FOLDER / "reference.json").write_text(json.dumps(whole, ensure_ascii=True, indent=1,
                                                      sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(found)} documents, medRDS {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
