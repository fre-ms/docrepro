# Changelog

## 0.10.0 (2026-11-27)

docrepro brings a document as near to its original as it can, and goes no further (the user, 27
November 2026). Interface 6; `docrepro-chain` version 3 stays.

### Removed

- **semdoc and attdoc are no steps of docrepro.** Understanding what the text says (medical terms,
  identifying information) goes beyond reproducing the document; signing it is TimeAttest's, and a
  signature could not be made again from the original, as every step of docrepro is. Both take what
  docrepro gives: ocrdoc's reading, and the finished document. `about` no longer lists them,
  `not_installed` no longer names them, `docrepro semdoc …` and `docrepro attdoc …` are no commands.
- With them went what only semdoc needed: a step's `planned` in `about`, the steps one needs
  (`needs`), and the kind of error `step-needs`.

## 0.9.0 (2026-11-27)

Several pictures of one document, and the camera's date as a choice. Interface 5;
`docrepro-chain` version 3.

- **Several pictures go through the chain as one document**: `run` and `edit` take several
  files, in their order; typdoc (0.3.0) binds them into one PDF, a page for each picture (a TIFF of
  several pages a page for each of them), and every step after it works on that one document. The
  results are named after the first picture. In the window typdoc stays on for several pictures.
- **Files that typdoc does not bind are each a document of its own** (the user's decision): with
  typdoc left out, a PDF among them, or `--each`, `run` takes each through the chain by itself into
  the one folder, and the answer lists them (`documents`; progress names the `document`). Two files
  with the same name before their ending are refused (`same-stem`). The window and a chain
  document work on one document (`several-originals`).
- **The chain document is version 3**: `originals`, a list in their order, in place of
  `original`. A chain document of the same pictures in another order is another document
  (`config-mismatch`). Version 2 is no longer read.
- **`--camera-date never|missing|first`** (tagdoc 0.4.0): whether the date a camera gives is
  suggested as the clinical date. tagdoc reads it from the originals the chain began with, since
  optdoc's prepared page carries no camera data.
- The standalone program is tried out with two photos bound into one document.

## 0.8.0 (2026-11-27)

A picture goes through every step as a picture, with tagdoc 0.3.0. Interface 4 and
`docrepro-chain` version 2 stay.

- **`--without typdoc` alone keeps a picture a picture**: optdoc prepares it, ocrdoc reads it,
  and tagdoc writes its description into it, in the place the picture's format has (XMP, and the
  EXIF texts in step, in JPEG, PNG, TIFF, WebP and HEIC; XMP in GIF), or into a sidecar beside it
  (BMP, PNM). What tagdoc suggests for a picture comes from the reading ocrdoc laid beside it. The
  chain document makes the same picture again, byte for byte.
- **No step needs a PDF any more**: `step-needs` no longer arises for a picture.
- **The window lets typdoc be switched for a picture**: on, the picture goes on as a PDF; off, it
  stays a picture through every tab. Switching it hands optdoc another file that shows the very
  same pages: optdoc takes along what a person planned (optdoc 0.11.0, `same_document`), and
  ocrdoc, which finds the same frames, keeps what a person decided. Where optdoc is off, ocrdoc
  has no frames to go by and starts anew; the status line says so.
- The standalone program is tried out with a photo that stays a photo through every step.

## 0.7.0 (2026-11-27)

A picture is read as a picture, with ocrdoc 0.4.0. Interface 4; `docrepro-chain` version 2 stays.

- **With typdoc left out, a picture stays a picture through ocrdoc as well.** ocrdoc reads the
  picture optdoc wrote (or, with optdoc left out too, the picture that came) and hands it on as
  it is, byte for byte; its reading and the Markdown lie beside it, with the chain document. The
  chain document makes the same files again. What a person decided in ocrdoc stays when optdoc
  changes the picture's light and not where things lie on it, as with a PDF.
- **The reading is `ocrdoc-reading` version 2**: every page says the `unit` of its boxes, points
  for a page of a PDF (as before), the picture's own pixels for a picture.
- **Only tagdoc still needs typdoc before it for a picture** (`step-needs`), and the window keeps
  typdoc on for a picture until tagdoc takes one as well.
- **`--paper` is gone.** optdoc places no picture on a sheet of paper since 0.10.0; docrepro 0.6.0
  still took the option and did nothing with it, which was a fault. A caller that passes it gets
  `usage` now: hence interface 4.
- **Every step names doccor 0.3.0** (typdoc 0.2.1, optdoc 0.10.1, ocrdoc 0.4.0, tagdoc 0.2.1): how
  a picture is looked at is written once there, and is the same in every step. A phone's JPEG
  that carries a second image beside the photo (a gain map) is one page; a TIFF stored on its
  side is read upright; typdoc binds a PNM as well.
- The standalone program is tried out with a photo that stays a photo and is read.

## 0.6.0 (2026-11-27)

A picture can stay a picture, with optdoc 0.10.0. Interface 3 and `docrepro-chain` version 2 stay.

- **With typdoc left out, a picture stays a picture.** optdoc gives back the type it was handed
  (a JPEG a JPEG, a HEIC a HEIC), and the result is that picture, as optdoc wrote it, with the
  chain document beside it (a picture has no place for it). Until now optdoc made a PDF of a
  picture it was handed.
- **A step that reads PDFs only needs typdoc before it for a picture**, and the chain says so
  before it does anything (`step-needs`: ocrdoc and tagdoc, as they stand). They are to learn to
  take a picture.
- **The window** works on PDFs: for a picture typdoc stays on there. optdoc can be switched
  freely. A picture that is to stay one is prepared with `run`, or in optdoc's own window.
- The standalone program is tried out with a photo that stays a photo.

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
