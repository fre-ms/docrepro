# Changelog

## 0.5.0 (2026-11-27)

Interface 3: one field renamed, in every tool of docrepro at once (typdoc 0.2.0, optdoc 0.9.0,
ocrdoc 0.3.0, tagdoc 0.2.0).

- **The answer names the document `document`**, no longer `pdf`: in `run` and `edit`, in every
  step's own answer, and between the steps (an adapter's `write` gives the file the next step is
  handed under that key). No step is to force a file type, so the document need not be a PDF, and
  a field called `pdf` would then point at a picture. The tools still write PDFs; that a picture
  stays a picture is to come. Callers read `document` where they read `pdf`.

## 0.4.0 (2026-11-27)

typdoc joins as step 5: the one step that changes a document's type. Interface 2 and
`docrepro-chain` version 2 stay.

- **typdoc** (0.1.0) binds a picture into a PDF as medRDS 9.5 says (the picture in it byte for
  byte) and hands that on. It is in use for pictures unless left out (`--without typdoc`, or its
  switch in the window); for a PDF it has nothing to do and is not in use. Without it a picture is
  handed to optdoc as it came, which makes a PDF of it as before.
- **optdoc can be left out for a picture** now: ocrdoc then reads the picture as typdoc bound
  it, unprepared. With typdoc and optdoc both left out, ocrdoc is handed the picture and answers
  `not-pdf` (ocrdoc and tagdoc do not read pictures yet).
- **The window** shows typdoc among the steps (no tab: it has nothing to decide). Of typdoc and
  optdoc, the one that alone makes a PDF of a picture cannot be switched off. Switching typdoc
  hands optdoc another file: optdoc starts anew, and the status line says so where a person's
  plans went.
- **attdoc**, the signing step to come (order 50), has its place in the list of steps.
- A step may say that it has no work for an original (`Step.has_work`).
- The standalone program has typdoc inside; its checks bind the photo through typdoc's own
  command line and through the chain.

## 0.3.0 (2026-11-27)

Every step is optional. Interface 2; `docrepro-chain` version 2.

- **`--without <step>`** for `run` and `edit` leaves a step out, as often as needed. A step that
  is not in use hands on what it got, untouched: ocrdoc reads the original where optdoc is off,
  tagdoc describes optdoc's PDF where ocrdoc is. OCR without preparation, preparation without
  OCR, a description alone are chains like any other, and the chain document makes each again,
  byte for byte. A photo or an image becomes a PDF through optdoc alone: without it ocrdoc
  answers `not-pdf` (`--no-clean-up` leaves the pages as they came instead).
- **The answer's `steps`** name every installed step and say whether it was in use (`used`).
- **The chain document is version 2**: every step says `used`. A step that is off may keep its
  configuration document, so that what a person decided in it is back when it is switched on
  again. A step the document does not name is not in use (it started fresh before: a step
  installed later then changed what an old document made). The entry of a step that is not
  installed and was not in use is carried along. Version 1 is no longer read.
- **The window** has the steps on its left, each with a switch and what became of it: off; in
  use, as suggested; in use, changed by hand; in use, to be made anew (a step before it changed).
  A filled circle marks a step in use and an empty one a step that is off, there and on the
  tabs; the tabs of a step that is off are closed. For a photo optdoc stays on. Where optdoc is
  switched off, ocrdoc reads the original and starts anew, and the status line says so.
- **Steps** may name the steps they cannot do without (`needs`: semdoc needs ocrdoc); a chain
  with a step in use whose need is not is refused (`step-needs`), one with no step in use too
  (`no-steps`).

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
