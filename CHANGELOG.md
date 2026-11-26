# Changelog

## 0.2.0 (2026-11-26)

Models as an optional download, through every step. With optdoc 0.8.0, ocrdoc 0.2.0 and doccor
0.2.0. Interface 1 and `docrepro-chain` version 1 stay: everything here is added.

- **`docrepro models list [--models <folder>]`** names the models of every installed step, each
  with its step, the address it comes from, its SHA-256, size and licence, and whether it lies in
  the folder given; `about` lists them too.
- **`docrepro models fetch <name> --to <folder> [--progress]`** fetches one, whichever step lists
  it: the only command that goes on the network, and only when asked. The file is kept only when
  it is the one listed.
- **`--models <folder>`** for `run` and `edit` reaches every step that takes models. It is no
  setting: the chain document does not name it, and what a model found is in its step's
  configuration document, so the original and the chain document give every file again without
  any model (tested: a scan on its head set upright by optdoc's orientation model and read by
  ocrdoc, then made again from the chain document alone, byte for byte).
- **Steps** say which models they can use (`catalogue`) and take the folder
  (`use_models(project, folder)`) through their adapters; both are optional, as the panel is.
- **The standalone program** is tried out with `models list`, with `models fetch` under the
  network closed by the system (it must answer `model-unreachable` and keep nothing), and, where
  the build is given a folder with the model (`packaging/build.py --models`), with a scan on its
  head. The build fetches nothing.

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
