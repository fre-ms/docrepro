# Changelog

## 0.1.0 (2026-11-26)

The whole way in one: docrepro joins optdoc (the page made faithful), ocrdoc (what is on it
recognised) and tagdoc (the document described as medRDS says), with a place kept for semdoc.

- **The chain** (`docrepro.chain`): an original through every installed step in their order, each
  step's input the result of the one before; the results under the original's name, the PDF
  carrying every step's configuration document and the chain document. Nothing outside the results
  folder.
- **The chain document** `<stem>.docrepro.json`, format `docrepro-chain` version 1: the original's
  SHA-256 and every step's configuration document. The original and the document give every file
  again, byte for byte; a change in an earlier step keeps a person's decisions in the later ones
  where the page did not move, and names the pages where it did.
- **The steps** (`docrepro.steps`): optdoc (10), ocrdoc (20), semdoc (30, planned), tagdoc (40);
  adapters for optdoc and ocrdoc, any other step's through the entry point `docrepro.steps` (tagdoc's
  is its own). docrepro names itself as the program the document is made with, so that the
  description's `xmp:CreatorTool` and the PDF's creator agree. A chain document naming a step that is not installed is refused
  (`step-missing`).
- **The command line**: `about`, `run`, `edit`, and every step's own as `docrepro <step> …`;
  interface 1 (`docs/interface.md`).
- **The standalone program** (`packaging/`, `docs/sidecar.md`): one file or a folder with every
  step inside, built and tried out by `packaging/build.py` (from optdoc 0.6.0's build): 163 MB as
  one file; the whole way on a photographed page in 12 s as one file, 4 s as a folder. CI builds
  and checks it on macOS.
- **Filed by a records app**: medRDS's reference library writes its metadata into docrepro's PDF,
  tagdoc's description stays beside them, and the filed PDF with the original gives every file
  again (`tests/test_filed.py`).
- **The window**: one tab per step, optdoc's preparation, ocrdoc's filters, areas and text, and the
  panel a later step brings (tagdoc's description); a later tab after a change in optdoc gets
  optdoc's new PDF, a step after ocrdoc ocrdoc's result, and the status line says what became of
  the person's decisions.
