"""A records app files docrepro's PDF: medRDS's reference library writes its metadata into
it (as an update appended to the file), the description tagdoc wrote stays beside them,
and from the filed PDF and the original every file comes again, byte for byte.  Needs
Node and the reference library of medRDS (``MEDRDS``, else ``../medRDS``)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from ocrdoc import ocr as ocrlib

from docrepro.chain import Chain, load_chain
from tests.synthetic import photo_of, table_report

MEDRDS = Path(os.environ.get("MEDRDS", Path(__file__).resolve().parents[2] / "medRDS"))
pytestmark = [
    pytest.mark.skipif(shutil.which("node") is None or not (MEDRDS / "lib").is_dir(),
                       reason="needs Node and the reference library of medRDS"),
    pytest.mark.skipif(not ocrlib.available_backends(), reason="no OCR engine"),
]

_FILE = """
import { readFileSync, writeFileSync } from 'node:fs';
import { readMetadata, writePdfMetadata } from '%(lib)s';
const schema = JSON.parse(readFileSync('%(schema)s', 'utf8'));
const bytes = new Uint8Array(readFileSync(process.argv.at(-2)));
const described = await readMetadata(bytes, 'pdf', schema);
const meta = { ...described, patient: 'K7Q4MX2PT', filed: '2026-11-26T22:00:00+01:00',
  filedBy: 'Dr. Erika Beispiel <mailto:beispiel@praxis.example>', origin: { channel: 'handover' },
  documentId: 'urn:uuid:11111111-2222-4333-8444-555555555555',
  instanceId: 'urn:uuid:66666666-7777-4888-9999-000000000000',
  metadataDate: '2026-11-26T22:00:00+01:00', conformsTo: 'https://medrds.org/spec/0.15' };
const filed = await writePdfMetadata(bytes, meta, schema);
writeFileSync(process.argv.at(-1), filed);
console.log(JSON.stringify({ described, filed: await readMetadata(filed, 'pdf', schema) }));
"""


def test_filed_by_a_records_app_and_made_again(tmp_path: Path) -> None:
    original = photo_of(table_report(tmp_path / "befund.pdf"), tmp_path / "foto.jpg")
    first = Chain.open(original).run(tmp_path / "a")
    script = _FILE % {"lib": (MEDRDS / "lib" / "index.mjs").as_posix(),
                      "schema": (MEDRDS / "schema" / "medrds.json").as_posix()}
    filed = tmp_path / "abgelegt.pdf"
    run = subprocess.run(["node", "--input-type=module", "-e", script, "--", first["pdf"],
                          str(filed)], capture_output=True, text=True, check=True)
    read = json.loads(run.stdout)
    assert read["described"]["kind"] == "lab" and read["described"]["date"] == "2026-03-12"
    assert read["described"]["creatorTool"].startswith("docrepro ")
    for key in ("kind", "date", "title", "creatorTool"):  # tagdoc's description stays
        assert read["filed"][key] == read["described"][key], key
    assert read["filed"]["patient"] == "K7Q4MX2PT"  # beside what the records app wrote
    assert filed.read_bytes().startswith(Path(first["pdf"]).read_bytes())  # appended, not rewritten
    again = Chain.open(original, chain=load_chain(filed)).run(tmp_path / "b")
    for key in ("pdf", "reading", "markdown", "config"):
        assert Path(again[key]).read_bytes() == Path(first[key]).read_bytes(), key
