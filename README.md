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
| 5 | [typdoc](packages/typdoc) | changes the type, and nothing else: binds pictures into one PDF as medRDS says, each in it byte for byte | 0.3 |
| 10 | [optdoc](packages/optdoc) | makes the page faithful: upright, unwarped in its true proportions, evenly lit, in its colours; gives back the type it got | 0.12 |
| 20 | [ocrdoc](packages/ocrdoc) | recognises areas, text, tables and barcodes; lays the text over the page of a PDF, beside a picture | 0.5 |
| 40 | [tagdoc](packages/tagdoc) | describes the document: title, kind, date, authors, the people it names with copies of their cards, written as medRDS says (into the PDF or the picture, or a sidecar) | 0.4 |

**What docrepro is for, and what not.** docrepro brings a photographed or scanned document as near to
the original as it can: its pages, its text, what it says of itself. It goes no further. Understanding
what the text says (medical terms, identifying information) and signing the document are other tasks,
for other programs, which take what docrepro gives: ocrdoc's reading (`<name>.reading.json`) and the
finished document, which TimeAttest can time-stamp and sign. A signature
could not be made again from the original anyway, as every step of docrepro is.

What they share (configuration documents, the command line's manners, no network, the window's building
blocks) is [doccor](packages/doccor)'s. Why the work is divided so, and the contract every
step keeps: [docs/family-design.md](docs/family-design.md).

**Status: pre-alpha (0.11.0).**

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
  given more contrast in optdoc keeps the areas a person drew and the text they corrected in ocrdoc; so
  does a picture that typdoc binds or no longer binds, and a page optdoc is switched off for that it did
  not move; a page turned or unwarped otherwise loses them, and the answer names it. Every page knows
  where it came from (the original file and which of its pages), so two letters of the same size never
  share a person's decisions;
- **a step switched off keeps what a person decided in it**, for when it is switched on again.

## How a step joins

A step is put into the chain by installing it: docrepro brings the adapters of optdoc and ocrdoc, and
typdoc and tagdoc bring their own through the entry point `docrepro.steps`:

```toml
[project.entry-points."docrepro.steps"]
tagdoc = "tagdoc.docrepro:TagdocAdapter"
```

An adapter opens the step's project on its input (fresh, or as its configuration document says), gives its
configuration document, makes and writes its result, and says which pages lost a person's decisions
(`docrepro.steps.Adapter`). The window gets the step's tabs the same way (`tabs`, `panels`), and names no
step itself: it goes through the steps in use as the chain does. A chain document that names a step
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
docrepro run photo.heic --out results/ --without typdoc   # it stays a HEIC: prepared, read, described
docrepro run seite-1.jpg seite-2.jpg --out results/        # two photos, one document: one PDF
docrepro run seite-1.jpg seite-2.jpg --out results/ --each # each photo a PDF of its own
docrepro run foto.heic brief.pdf --out results/            # not one document: each by itself
docrepro run hautbefund.jpg --out results/ --camera-date first   # the photo's date is the clinical date
```

`run` writes the last step's files under the original's name (`<name>.pdf` with ocrdoc's text layer and
tagdoc's description, `<name>.reading.json`, `<name>.md`) and the chain document `<name>.docrepro.json`, and nothing anywhere else: what the steps make
on the way goes into a hidden folder inside the results and is removed at once. `--without <step>` leaves a
step out. A picture goes on as a PDF through typdoc; with typdoc left out it stays a picture through every
step: optdoc gives back the type it got, ocrdoc reads the picture and lays its reading beside it, tagdoc
writes its description into the picture (or beside it, for a type without a place for one). With optdoc
left out, ocrdoc reads what it is handed, unprepared: the picture as typdoc bound it, or the picture itself.
`edit`
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

## One repository, six packages

The tools live together here, each a package of its own in `packages/<tool>`, with its own version,
command line, interface, changelog and tests, and each usable without docrepro:

| package | folder |
|---|---|
| doccor, the core | [packages/doccor](packages/doccor) |
| typdoc | [packages/typdoc](packages/typdoc) |
| optdoc | [packages/optdoc](packages/optdoc) |
| ocrdoc | [packages/ocrdoc](packages/ocrdoc) |
| tagdoc | [packages/tagdoc](packages/tagdoc) |
| docrepro, which joins them | this folder |

They are a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): every package takes the
others as they stand beside it, and one tag (`v<docrepro's version>`) names one state of them all. A
package's version changes when the package changes, and only then: a tool that did not change writes the
same bytes as before, since its version is part of what it writes. Until 27 November 2026 each tool had a
repository of its own; their histories are here, under their folders.

## Install

Python 3.12 or later, with [uv](https://docs.astral.sh/uv/):

```
git clone https://github.com/fre-ms/docrepro
cd docrepro
uv sync --extra gui
```

`uv sync --all-packages --all-extras` installs every package with all it can use, as the tests need it;
each package's tests run in its folder (`cd packages/ocrdoc && uv run pytest`). A program that uses one tool
alone takes it from a tag of this repository, the core beside it:

```toml
[tool.uv.sources]
ocrdoc = { git = "https://github.com/fre-ms/docrepro", tag = "v0.11.0", subdirectory = "packages/ocrdoc" }
doccor = { git = "https://github.com/fre-ms/docrepro", tag = "v0.11.0", subdirectory = "packages/doccor" }
```

## Standalone program

`uv run python packaging/build.py` builds docrepro as one program with every step in it (Python, the OCR
models, Camelot, Qt and all), named the way Tauri wants a sidecar (`docrepro-aarch64-apple-darwin`), and
tries it out: the whole way on an invented photo with nothing left outside the results, the same files
again from the chain document, the window without a person, the steps one by one, everything once more
with the network closed by the system. 163 MB as one file (no more than optdoc 0.6.0 was on its own), or a
faster-starting folder with `--onedir`. See [docs/sidecar.md](docs/sidecar.md).

## Licence

GNU Affero General Public License 3.0 or later (see `LICENSE`).
