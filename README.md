# docrepro

docrepro reproduces photographed and scanned documents as real digital documents: a phone photo of a
laboratory report, a scanned letter, a stack of bound photos become a PDF with upright, unwarped pages in
their own colours, a text layer that a reader can search and a program can take apart, a reading with
every word, area, table cell and barcode, and Markdown. Every step can be made again from the original,
byte for byte, and taken up again where a person stopped. Everything runs on your own computer; nothing
is sent anywhere.

It joins a family of tools, one tool for one step, each usable on its own:

| order | tool | its step | status |
|---|---|---|---|
| 5 | [typdoc](https://github.com/fre-ms/typdoc) | changes the type, and nothing else: binds pictures into one PDF as medRDS says, each in it byte for byte | 0.2 |
| 10 | [optdoc](https://github.com/fre-ms/optdoc) | makes the page faithful: upright, unwarped in its true proportions, evenly lit, in its colours; gives back the type it got | 0.10 |
| 20 | [ocrdoc](https://github.com/fre-ms/ocrdoc) | recognises areas, text, tables and barcodes, and lays the text over the page | 0.3 |
| 30 | semdoc | understands the text: medical terms and identifying information (through lexterm and lexident) | planned |
| 40 | [tagdoc](https://github.com/fre-ms/tagdoc) | describes the document: title, kind, date, authors, the people it names with copies of their cards, written as medRDS says (XMP and the information dictionary, or a sidecar) | 0.2 |
| 50 | attdoc | signs the document: a time stamp, a person's signature, resting on TimeAttest | planned |

What they share (configuration documents, the command line's manners, no network, the window's building
blocks) is [doccor](https://github.com/fre-ms/doccor)'s. Why the work is divided so, and the contract every
step keeps: `docs/family-design.md` in optdoc.

**Status: pre-alpha (0.6.0).**

## The chain and its document

`docrepro run <original>` takes the original through the steps in their order; each step's input is the
result of the one before. **Every step is optional**: a step that is left out (`--without ocrdoc`, or its
switch in the window) hands on what it got, untouched. OCR without preparation, preparation without OCR, a
description alone: each is a chain. The **chain document** (`<name>.docrepro.json`, also inside the PDF)
holds the original's SHA-256, which steps were in use, and every step's configuration document, nothing
else. With it:

- **the original gives every file again, byte for byte**: each step reproduces its result, and so each
  step's input is the same again;
- **the work is resumed** where a person stopped (`docrepro edit --config`);
- **a change in an earlier step costs no work in the later ones** where it does not move the page: a page
  given more contrast in optdoc keeps the areas a person drew and the text they corrected in ocrdoc; a page
  turned or unwarped otherwise loses them, and the answer names it;
- **a step switched off keeps what a person decided in it**, for when it is switched on again.

## Steps to come, and how a step joins

semdoc has its place in the chain from the start (order 30, between ocrdoc and tagdoc; it takes the reading
and gives annotations, format `semdoc-annotations`; `docrepro about` lists it as planned). A step is put into
the chain by installing it: docrepro brings the adapters of optdoc and ocrdoc, and any other step brings its
own through the entry point `docrepro.steps`, as tagdoc does:

```toml
[project.entry-points."docrepro.steps"]
tagdoc = "tagdoc.docrepro:TagdocAdapter"
```

An adapter opens the step's project on its input (fresh, or as its configuration document says), gives its
configuration document, makes and writes its result, and says which pages lost a person's decisions
(`docrepro.steps.Adapter`). The window gets the step's tab the same way. A chain document that names a step
which is not installed is refused (`step-missing`): without it, the result cannot be made again.

## Command line

```
docrepro about
docrepro run photo.heic --out results/
docrepro run photo.heic --out results/ --config results/photo.docrepro.json
docrepro edit photo.heic --out results/ --language en
docrepro optdoc run photo.heic --out step1/      # every step's own command line
docrepro ocrdoc run step1/photo.pdf --out step2/
docrepro models list                             # the models the steps can use
docrepro models fetch page-orientation --to models/
docrepro run scan.pdf --out results/ --models models/
docrepro run scan.pdf --out results/ --without optdoc      # read the scan as it came
docrepro run photo.heic --out results/ --without ocrdoc --without tagdoc   # prepare only
docrepro run photo.heic --out results/ --without typdoc --without tagdoc   # it stays a HEIC, read
```

`run` writes the last step's files under the original's name (`<name>.pdf` with ocrdoc's text layer and
tagdoc's description, `<name>.reading.json`, `<name>.md`) and the chain document `<name>.docrepro.json`, and nothing anywhere else: what the steps make
on the way goes into a hidden folder inside the results and is removed at once. `--without <step>` leaves a
step out. A picture goes on as a PDF through typdoc; with typdoc left out it stays a picture: optdoc gives
back the type it got, and ocrdoc reads the picture and lays its reading beside it. tagdoc reads PDFs only,
as it stands, and is left out with typdoc. With optdoc left out, ocrdoc reads what it is handed, unprepared:
the picture as typdoc bound it, or the picture itself. `edit`
opens one window with a tab for every panel of the steps (optdoc's preparation, ocrdoc's filters, areas and
text, tagdoc's description) and, on the left, the steps themselves: each with a switch and what became of it
(off; in use as suggested; changed by hand; to be made anew), a filled or an empty circle on its tabs.
*Apply* writes the same files as `run`, *Save and continue later* the chain document, *Cancel* nothing. Every command answers with one JSON
object, a failure too, with its kind and its message in English and German. The settings of the steps can be
given with `run` and `edit`: `--photo`/`--scan`, `--no-clean-up`, `--colour-pages` (optdoc),
`--reader`, `--languages`, `--no-cells`, `--no-areas` (ocrdoc). `--progress` writes
`{"step": "ocrdoc", "page": 1, "of": 2}` per step and page on standard error.

**Models are an optional download.** No step needs one, and docrepro never goes on the network while it
works. `models list` shows the models the steps can use, each with its step, the address it comes from, its
SHA-256, size and licence; `models fetch <name> --to <folder>` fetches one, the only command that goes on the
network, and keeps the file only when it is the one listed; `--models <folder>` lets the steps use what lies
there. A model is listed only after it did better, measured, than the rules it adds to. So far that is one:
`page-orientation` (6.8 MB, Apache-2.0), with which optdoc sets a page upright that stands on its head or on
its side. What a model found is kept in its step's configuration document, so the original and the chain
document give every file again without any model.

## Install

Python 3.12 or later, with [uv](https://docs.astral.sh/uv/); the steps and the core come from their released
tags:

```
uv sync --extra gui
```

## Standalone program

`uv run python packaging/build.py` builds docrepro as one program with every step in it (Python, the OCR
models, Camelot, Qt and all), named the way Tauri wants a sidecar (`docrepro-aarch64-apple-darwin`), and
tries it out: the whole way on an invented photo with nothing left outside the results, the same files
again from the chain document, the window without a person, the steps one by one, everything once more
with the network closed by the system. 163 MB as one file (no more than optdoc 0.6.0 was on its own), or a
faster-starting folder with `--onedir`. See [docs/sidecar.md](docs/sidecar.md).

## Planned

- semdoc, once lexcor has its annotation document and its window for a person's review.
- **attdoc**, a signing step as the last (order 50): a time stamp and a person's signature (the qualified
  one with the electronic health professional card, or an advanced one with a software certificate),
  resting on TimeAttest. It will be off unless a person asks for it, and cannot be made again, only
  verified: the steps before it are made again byte for byte and compared with what was signed.
- **The file keeps its type.** No step is to force PDF: a picture will go through every step as a picture
  (optdoc writes the prepared picture in the format it came in, ocrdoc lays its reading beside it, tagdoc
  writes into the picture or a sidecar as medRDS says for the format). typdoc, the one step that changes
  the type, is there, and optdoc and ocrdoc keep the type they are handed; tagdoc still reads PDFs only,
  and until it does not, the window keeps typdoc on for a picture. The design: `docs/family-design.md` in
  optdoc.
- Several pictures of one document through the whole chain (typdoc binds several on its own already).

## Licence

GNU Affero General Public License 3.0 or later (see `LICENSE`).
