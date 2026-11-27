# docrepro's command line as an interface

**Interface 7**, since docrepro 0.11.0. This is what a program may rely on
when it calls docrepro, a records app above all, which ships one program instead of one per step.

docrepro brings a photographed or scanned document as near to the original as it can, and goes no
further: its steps are typdoc, optdoc, ocrdoc and tagdoc. Understanding what the text says and signing
the document are tasks for other programs, which take what docrepro gives (ocrdoc's reading, the finished
document; TimeAttest signs it).

Every answer carries `interface`; it goes up when something a caller relies on changes in a way that breaks
it. Within one interface, new fields, options and kinds of error may come; a caller ignores what it does
not know. The steps' own command lines (`docrepro optdoc …`, `docrepro ocrdoc …`) keep their own interfaces
(typdoc's 3, optdoc's 6, ocrdoc's 4, tagdoc's 3), described in their packages
(`packages/<tool>/docs/interface.md`).

**From interface 6:** the steps' documents are of new versions (optdoc 0.12.0: `optdoc-config`
4; ocrdoc 0.5.0: `ocrdoc-config` 2), and a chain document that holds the older ones is no longer
read (`bad-config`). Every page of them names where it came from, so that what a person decided
stays with the page wherever the page goes: when typdoc is switched, when optdoc is switched off
for a page it did not move, and in the window and on the command line alike. The answer is as in
interface 6.

**From interface 5:** semdoc and attdoc are no steps of docrepro any more (the user, 27 November 2026):
`about` no longer lists them, `not_installed` no longer names them, and `docrepro semdoc …` or `docrepro
attdoc …` is a `usage` error. With them went what only semdoc needed: a step's `planned` in `about`, and
the kind of error `step-needs` (no step needs another). Everything else is as in interface 5.

**Added within interface 4 (docrepro 0.8.0):** a picture goes through *every* step as a picture. tagdoc
(0.3.0) describes a picture and writes the description into it where its format has a place (XMP, and the
EXIF texts in step, in JPEG, PNG, TIFF, WebP and HEIC; XMP in GIF), else into a sidecar beside it. So
`--without typdoc` alone keeps a picture a picture.

**From interface 3:** two things a caller may rely on changed. **The reading is `ocrdoc-reading`
version 2**: every page says the `unit` of its boxes, points for a page of a PDF (as before) and the
picture's own pixels for a picture, which ocrdoc (0.4.0) now reads and hands on as it came. **`--paper` is
gone**: optdoc places no picture on a sheet of paper any more (since 0.10.0; docrepro 0.6.0 still took
the option and did nothing with it). With them: a picture can stay a picture through ocrdoc as well, its
reading and the Markdown beside it.

**From interface 2 (docrepro 0.5.0):** the answer names the document `document`, no longer `pdf`, here and
in every step's own answer. No step is to force a file type, so the document need not be a PDF.

**From interface 1 (docrepro 0.3.0):** every step is optional. `--without <step>` leaves a step out; the
answer's `steps` name every installed step and say whether it was in use (`used`); the chain document is
version 2 (each step says `used`; version 1 is no longer read: `bad-config`, reason `format`); a step the
chain document does not name is not in use (it started fresh before); new kind of error `no-steps`. Models as an optional download came within interface 1 (docrepro 0.2.0) and stay as they are.

**Added within interface 3 (docrepro 0.6.0), and kept:** a picture can stay a picture. With typdoc left
out, optdoc (0.10.0) gives back the type it was handed; `document` in the answer then names a picture, with
the chain document beside it.

**Added within interface 2 (docrepro 0.4.0), and kept:** typdoc as step 5, the one step that changes a
document's type. It binds a picture into a PDF as medRDS says and is in use for pictures unless left out
(`--without typdoc`); for a PDF it has nothing to do. The answer's `steps`, `about` and the chain document
name it like every step.

**From interface 4:** `run` and `edit` take **several files**. Pictures of one document go through the
chain as one: typdoc binds them into one PDF (a page for each, a file of several pictures a page for each
of them). Files that typdoc does not bind (typdoc left out, a PDF among them, or `--each`) go through
`run` each as a document of its own, and the answer lists them (`documents`). The chain document is
**version 3**: it names the originals as a list, `originals`, in their order (one for a single
original), in place of `original`; version 2 is no longer read. New kinds of error: `several-originals`,
`same-stem`. New setting: `--camera-date` (tagdoc 0.4.0).

## Calling

```
docrepro about
docrepro run  <original>… --out <folder> [--config <chain>] [--without <step>]… [settings] [--progress]
docrepro edit <original>… --out <folder> [--config <chain>] [--without <step>]… [settings] [--language de|en]
docrepro models list [--models <folder>]
docrepro models fetch <name> --to <folder> [--progress]
docrepro <step> …                      the step's own command line (typdoc, optdoc, ocrdoc, tagdoc)
docrepro --version
```

Every command writes **exactly one JSON object to standard output**, whether it succeeds or not, and ends
with exit status **0** on success and **2** on failure. Standard error is free for `--progress` and the usage
line of an invalid command line. No answer and no message quotes the content of a document or a path given
to docrepro. docrepro never goes on the network while it works; the one command that goes out is
`models fetch`, on request, for one file from the address listed (below).

| field | example | meaning |
|---|---|---|
| `interface` | `3` | the version of this description |
| `made_with` | `"docrepro 0.6.0"` | the program and its version |

## `about`

```json
{"interface": 6, "made_with": "docrepro 0.10.0", "version": "0.10.0", "window": true,
 "steps": [{"tool": "typdoc", "order": 5, "takes": "pictures", "gives": "pdf",
            "does": {"en": "…", "de": "…"}, "installed": true, "version": "0.3.0"},
           {"tool": "optdoc", "order": 10, "…": "…"},
           {"tool": "ocrdoc", "order": 20, "…": "…"},
           {"tool": "tagdoc", "order": 40, "…": "…"}],
 "models": [{"step": "optdoc", "name": "page-orientation", "…": "…", "present": null}]}
```

`models` are the models the installed steps can use, as `models list` gives them.

## `run`: the whole way

`<original>` is a photo, an image or a PDF; docrepro never changes it and always starts from it. It takes it
through the steps in use, in their order; each step's input is the result of the one before. Into
`<folder>` (made when missing; default `<original>.docrepro` beside it) it writes the files of the last step
in use under the original's stem, and **nothing anywhere else** (what the steps make on the way goes into
the hidden folder `.docrepro-work` inside `<folder>` and is removed at once). With every step in use:

| file | what it is |
|---|---|
| `<stem>.pdf` | the document: optdoc's prepared pages with ocrdoc's text layer and tagdoc's description (medRDS 7: XMP and the information dictionary), carrying every step's configuration document (`optdoc.json`, `ocrdoc.json`, `tagdoc.json`) and the chain document (`docrepro.json`) |
| `<stem>.<ending>` | in its place, where a picture stays a picture (typdoc left out): the picture optdoc prepared, in the format it came in, with tagdoc's description inside (its XMP, and its EXIF in step, where the format has a place). A picture carries no configuration documents: the chain document beside it holds them all |
| `<stem>.reading.json` | ocrdoc's reading (`ocrdoc-reading` 2: every page says the `unit` of its boxes, `"pt"` for a page of a PDF, `"px"` for a picture) |
| `<stem>.md` | the text as Markdown |
| `<stem>.docrepro.json` | the chain document (below) |

tagdoc adds the sidecar `<file name>.xmp` (`<stem>.pdf.xmp`, `<stem>.bmp.xmp`) where the description goes
into one: a signed PDF, a picture of a type without a place for it (BMP, PNM), or a file tagdoc cannot
write into without risk.

**Every step is optional.** In use are all installed steps that have work for the original, but those left
out: `--without typdoc`, `--without optdoc`, `--without ocrdoc`, `--without tagdoc`, as often as needed. A
step that is not in use hands on what it got, untouched, and writes nothing:

| left out | what happens |
|---|---|
| typdoc | **A picture stays a picture, through every step.** optdoc gives back the type it got, ocrdoc reads the picture and hands it on as it is, tagdoc writes its description into it: the result is `<stem>.<ending>`, the prepared picture in the format it came in, described, with the reading (its boxes in the picture's pixels), the Markdown and the chain document beside it (a picture has no place for them). For a PDF typdoc is never in use: it has nothing to do. |
| optdoc | ocrdoc reads what typdoc gave (the picture bound into a PDF, as it came: a photo read without preparing it), or the original, a PDF or, with typdoc left out as well, the picture itself. |
| ocrdoc | No text layer, no reading, no Markdown; tagdoc describes what optdoc gave (and finds less to suggest where there is no text to read: a PDF without a text layer, a picture without a reading beside it). |
| tagdoc | The document has no description; it is ocrdoc's. |
| all | The error `no-steps`. |

**No step is to force a file type.** typdoc is the one step that changes a document's type; the steps after
it take what they are handed. optdoc keeps the type it is handed (from 0.10.0); so does ocrdoc (from
0.4.0), which lays its reading beside a picture; so does tagdoc (from 0.3.0), which writes its description
into the picture where the picture's format has a place for one (`docs/family-design.md` has the
design).

**Several files.** Pictures of one document (`docrepro run seite-1.jpg seite-2.jpg …`) are bound by typdoc
into one PDF, in the order given, as medRDS 9.5 says (each picture in it byte for byte; a TIFF of several
pages a page for each), and every step after it works on that one document. The results are named after
the first picture (`seite-1.pdf`), and the answer is that of one document, as above.

Several files are one document only so bound. **Where typdoc does not bind them** (it is left out, a PDF
is among them, or `--each` asks for it), `run` takes each file through the chain as a document of its own,
one after another, into the one folder, each under its own name; the steps in use and the settings are the
same for all. A picture then goes on as a PDF of its own where typdoc is in use (`--each`, or beside a PDF)
and stays a picture where it is not. The answer lists the answer of each document, in the order of the
files; with `--progress` every line also names the `document` (from 1):

```json
{"interface": 6, "made_with": "docrepro 0.10.0",
 "documents": [{"document": "<folder>/seite-1.jpg", "config": "<folder>/seite-1.docrepro.json",
                "pages": 1, "steps": [{"tool": "typdoc", "used": false}, "…"]},
               {"document": "<folder>/brief.pdf", "…": "…"}],
 "not_installed": []}
```

Two files whose names are the same before their ending would overwrite each other's results: `same-stem`,
before anything is done. Where one document fails, the error says so, and the results of those before it
stay. A chain document is of one document: `--config` beside several files that are not one is a `usage`
error, and so is `--each` beside one file. The window, too, works on one document: `edit` with several files
that are not one answers `several-originals`.
The PDF carries the configuration documents of the steps that ran, and the chain document says for every
step whether it was in use. With `--config` the chain document decides which steps are in use; `--without`
beside it is a `usage` error.

**Settings** of the steps, each taken by the step that knows it: `--photo` or `--scan`,
`--no-clean-up`, `--colour-pages jpeg|png` (optdoc); `--reader`, `--languages`, `--no-cells`, `--no-areas`
(ocrdoc); `--camera-date never|missing|first` (tagdoc: whether the date a camera gives, when the photo was
taken, is suggested as the clinical date; tagdoc reads it from the originals, since optdoc's prepared page
carries no camera data). With `--config` the chain document decides; a setting beside it is a `usage` error.

**Models.** `--models <folder>` (for `run` and `edit`) is the folder whose models the steps may use; every
step that takes models gets it, and what does not lie there is done without. It is no setting: the chain
document does not name it, and it may stand beside `--config`.

**Progress** with `--progress`: a line per step and page on standard error,
`{"step": "optdoc", "page": 1, "of": 2}`.

The answer:

```json
{"interface": 6, "made_with": "docrepro 0.10.0",
 "document": "<folder>/<stem>.pdf", "config": "<folder>/<stem>.docrepro.json",
 "reading": "<folder>/<stem>.reading.json", "markdown": "<folder>/<stem>.md",
 "pages": 2,
 "steps": [{"tool": "optdoc", "used": true, "made_with": "optdoc 0.10.1", "dropped": []},
           {"tool": "ocrdoc", "used": true, "made_with": "ocrdoc 0.4.0", "dropped": [2]},
           {"tool": "tagdoc", "used": false}],
 "not_installed": []}
```

`steps` names every installed step in the chain's order and says whether it was in use (`used`). For a
step in use, `dropped` names the pages (from 1) whose decisions a person had made in that step and that
went, because an earlier step moved the page (turned, unwarped or straightened it otherwise). `reading` and
`markdown` are there where ocrdoc was in use.

## `edit`: one window for the whole way

Opens a window with a tab for every panel of the installed steps, in their order: optdoc's preparation (1),
ocrdoc's filters for OCR (2), areas (3) and text (4), tagdoc's description (5); a step to come brings its tab.

On the left stand the steps, each with a switch and what became of it: **off**; **in use, as suggested**;
**in use, changed by hand** (a person decided something in it); **in use, to be made anew** (a step before
it changed since). A filled circle marks a step in use, an empty one a step that is off, in the list and on
its tabs; the tabs of a step that is off are closed. The window starts with the steps the chain document
or `--without` say. typdoc has no tab (it has nothing to decide); for a PDF it says "nothing to do". For a
picture it is on unless the person switches it off: then the picture stays a picture through every tab.
Switching typdoc hands the steps after it another file (the picture, or the PDF of it) that shows the
very same pages, every page of the same origin: optdoc takes along what a person planned, and ocrdoc keeps
what a person decided in it, with optdoc in use or not. Switching optdoc off hands ocrdoc what optdoc was
handed: what a person decided in ocrdoc stays on every page optdoc had not moved, and goes on the others;
the status line says which. What a person decided in a step that is switched off is kept, in the chain
document too, and is back when the step is switched on again.

When the
person turns to tab 5, ocrdoc writes its result as it stands (reading the pages not read yet) and tagdoc
describes it; a person's fields stay whatever changed before. When the person turns from
optdoc's tab to a later one after changing a page, optdoc's PDF is made anew and ocrdoc keeps what the person
decided there where the page did not move; the status line says so, or names the pages where it went.
**Apply** writes what `run` writes (with the window's configuration documents) and answers as `run` with
`"finished": true`; **Save and continue later** writes the chain document alone
(`{"config": …, "finished": false}`); **Cancel** writes nothing (the error `cancelled`).

## `models`: optional downloads

```
docrepro models list [--models <folder>]
docrepro models fetch <name> --to <folder> [--progress]
```

No step needs a model; a step lists one only after it did better, measured, than the rules it adds to.
docrepro lists the models of every installed step, each with its step:

```json
{"interface": 6, "made_with": "docrepro 0.10.0",
 "models": [{"step": "optdoc", "name": "page-orientation", "file": "pp-lcnet-x1-0-doc-ori.onnx",
             "url": "https://huggingface.co/PaddlePaddle/PP-LCNet_x1_0_doc_ori_onnx/resolve/…/inference.onnx",
             "sha256": "af9a0a4f…", "bytes": 6788069, "licence": "Apache-2.0",
             "source": "https://huggingface.co/PaddlePaddle/PP-LCNet_x1_0_doc_ori_onnx",
             "does": {"en": "tells which way up a page stands, …", "de": "…"}, "present": false}]}
```

`url` is where the file comes from (https, a fixed revision), `sha256` and `bytes` what it must be, `licence`
the licence of the weights and `source` the page that states it; `present` says whether the file lies in the
folder of `--models` under the name `file` with that SHA-256 (`null` without `--models`).

`models fetch <name> --to <folder>` is **the only command that goes on the network**, and only when asked:
it fetches that one file, never more bytes than listed, and keeps it only when size and SHA-256 are the
ones listed. The request carries the address and a client name ("doccor" and its version), nothing of a
document or a person. The answer: `{"step": "optdoc", "model": "page-orientation", "file":
"<folder>/pp-lcnet-x1-0-doc-ori.onnx", "bytes": 6788069, "sha256": "…", "licence": "Apache-2.0"}`; with
`--progress`, lines `{"bytes": n, "of": m}` on standard error. A file that is there and right is not
fetched again. Failures: `unknown-model` (no step lists the name), `model-unreachable` (the address did not
answer; so also wherever the network is closed), `model-checksum` (what came is not the file listed;
nothing was kept), `unwritable`.

An application that runs docrepro with the network closed (`sandbox-exec … (deny network*)`) runs this one
command outside that fence, or fetches the file itself from `url`, checks the SHA-256 and puts it into the
folder under the name `file`: both give the same folder.

What a model found is kept in its step's configuration document (optdoc: the page's turn in its plan, and
`"models": ["page-orientation"]` on the page), so **the original and the chain document give every file
again without any model**.

| model | step | size | what it does |
|---|---|---|---|
| `page-orientation` | optdoc | 6.8 MB | Sets a page upright that stands on its head or lies on its side, so that ocrdoc can read it. It answers only where it is sure. On optdoc's bench (57 images of invented pages, each shown the four ways up) it named the turn in 223 of 228 cases, left the page as it came in the other five, and turned none wrongly. |

ocrdoc lists none yet: the layout model measured so far did worse than its rules on the invented letters of
its bench (ocrdoc's `docs/interface.md`).

## The chain document: `docrepro-chain`, version 3

```json
{"format": "docrepro-chain", "version": 3, "made_with": "docrepro 0.10.0",
 "originals": [{"sha256": "…", "bytes": 245678, "suffix": ".jpg"},
               {"sha256": "…", "bytes": 231004, "suffix": ".jpg"}],
 "steps": [{"tool": "typdoc", "used": true, "made_with": "typdoc 0.2.0",
            "config": {"format": "typdoc-config", "…": "…"}},
           {"tool": "optdoc", "used": true, "made_with": "optdoc 0.10.1",
            "config": {"format": "optdoc-config", "…": "…"}},
           {"tool": "ocrdoc", "used": true, "made_with": "ocrdoc 0.3.0",
            "config": {"format": "ocrdoc-config", "…": "…"}},
           {"tool": "tagdoc", "used": false, "config": {"format": "tagdoc-config", "…": "…"}}]}
```

The originals by their SHA-256, in their order (one for a single original), and for every step whether it was in use (`used`) and its configuration
document as the step wrote it; no paths, no times. A step in use has `made_with` and `config`. A step that
is off may keep a `config`: what a person decided in it before it was switched off, kept for when it is
switched on again (it takes no part in the result). **The original and the chain document give every file
again, byte for byte**, on the same versions of the steps; `--config` takes the chain document or the PDF
docrepro wrote. A chain document of other originals, or of the same in another order, is refused (`config-mismatch`), one that used a step
which is not installed too (`step-missing`): without it, the result cannot be made again. A step the
document does not name is not in use, so that a step installed later changes nothing of what the document
makes; in the window a person can switch it on. The entry of a step that is not installed and was not in
use is carried along as it is. Versions 1 and 2 (docrepro 0.1 to 0.8) are no longer read.

## Failures

As every tool of docrepro: `error`, `details`, `message` in English and German. docrepro's own kind:

| `error` | when | `details` |
|---|---|---|
| `step-missing` | the chain document used a step that is not installed (a step of a later docrepro, or one left out of this program), or `docrepro <step>` for a step that is not installed | `step` |
| `several-originals` | the window, or a chain document, is given several files that are not one document (typdoc does not bind them) | |
| `same-stem` | several files taken each by itself, two of them with the same name before their ending | |
| `no-steps` | no step is in use: nothing to do | |

and the common ones (`missing`, `bad-config`, `config-mismatch`, `same-as-source`, `unwritable`, `cancelled`,
`no-gui`, `network`, `usage`, `internal`, and of `models fetch`: `unknown-model`, `model-unreachable`,
`model-checksum`). A step's own failure comes with the step's kind (optdoc's `unsupported`, ocrdoc's
`no-reader` …).

## Steps to come

A step joins the chain by being installed: docrepro brings the adapters of optdoc and ocrdoc; any other step
brings its own through the entry-point group `docrepro.steps`, named after the step. An adapter opens the
step's project on its input (fresh with the settings, or as its configuration document says), gives the
configuration document, makes and writes the result (a PDF for the next step, and its own files), and names
the pages whose decisions went (`docrepro.steps.Adapter`), and may bring a panel for the window
(`panel(project, words)`), the models its step can use (`catalogue`) and a way to hand its project the
folder of models (`use_models(project, folder)`), and the originals the chain began with
(`use_originals(project, files)`). typdoc (order 5) and tagdoc (order 40) join so.

## Licence

docrepro is free software under the GNU Affero General Public License 3.0 or later.
