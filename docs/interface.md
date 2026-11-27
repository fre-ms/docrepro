# docrepro's command line as an interface

**Interface 3**, since docrepro 0.5.0. This is what a program may rely on when it calls docrepro, a records
app above all, which ships one program instead of one per step.

Every answer carries `interface`; it goes up when something a caller relies on changes in a way that breaks
it. Within one interface, new fields, options and kinds of error may come; a caller ignores what it does not
know. The steps' own command lines (`docrepro optdoc …`, `docrepro ocrdoc …`) keep their own interfaces
(typdoc's 2, optdoc's 4, ocrdoc's 2, tagdoc's 2), described in their repositories.

**From interface 2:** the answer names the document `document`, no longer `pdf`, here and in every step's
own answer. No step is to force a file type, so the document need not be a PDF, and a field called `pdf`
would then point at a picture. A caller reads `document` where it read `pdf`; nothing else changed.

**From interface 1 (docrepro 0.3.0):** every step is optional. `--without <step>` leaves a step out; the
answer's `steps` name every installed step and say whether it was in use (`used`); the chain document is
version 2 (each step says `used`; version 1 is no longer read: `bad-config`, reason `format`); a step the
chain document does not name is not in use (it started fresh before); new kinds of error `step-needs` and
`no-steps`. Models as an optional download came within interface 1 (docrepro 0.2.0) and stay as they are.

**Added within interface 2 (docrepro 0.4.0), and kept:** typdoc as step 5, the one step that changes a
document's type. It binds a picture into a PDF as medRDS says and is in use for pictures unless left out
(`--without typdoc`); for a PDF it has nothing to do. The answer's `steps`, `about` and the chain document
name it like every step. attdoc, the signing step to come (order 50), is named in `about`.

## Calling

```
docrepro about
docrepro run  <original> --out <folder> [--config <chain>] [--without <step>]… [settings] [--progress]
docrepro edit <original> --out <folder> [--config <chain>] [--without <step>]… [settings] [--language de|en]
docrepro models list [--models <folder>]
docrepro models fetch <name> --to <folder> [--progress]
docrepro <step> …                      the step's own command line (typdoc, optdoc, ocrdoc, tagdoc; semdoc, attdoc once there)
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
| `made_with` | `"docrepro 0.5.0"` | the program and its version |

## `about`

```json
{"interface": 3, "made_with": "docrepro 0.5.0", "version": "0.5.0", "window": true,
 "steps": [{"tool": "optdoc", "order": 10, "takes": "original", "gives": "pdf",
            "does": {"en": "…", "de": "…"}, "planned": false, "installed": true, "version": "0.9.0"},
           {"tool": "typdoc", "order": 5, "…": "…"},
           {"tool": "ocrdoc", "order": 20, "…": "…"},
           {"tool": "semdoc", "order": 30, "takes": "reading", "gives": "annotations",
            "planned": true, "installed": false, "version": null},
           {"tool": "tagdoc", "order": 40, "…": "…"},
           {"tool": "attdoc", "order": 50, "planned": true, "installed": false, "version": null}],
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
| `<stem>.reading.json` | ocrdoc's reading (`ocrdoc-reading` 1) |
| `<stem>.md` | the text as Markdown |
| `<stem>.docrepro.json` | the chain document (below) |

tagdoc adds `<stem>.pdf.xmp` where the description goes into a sidecar; a step to come adds its own files
(semdoc its annotations).

**Every step is optional.** In use are all installed steps that have work for the original, but those left
out: `--without typdoc`, `--without optdoc`, `--without ocrdoc`, `--without tagdoc`, as often as needed. A
step that is not in use hands on what it got, untouched, and writes nothing:

| left out | what happens |
|---|---|
| typdoc | A picture is handed on as it came. As the tools stand, optdoc then makes a PDF of it itself (on a sheet of A4, as before docrepro 0.4). For a PDF typdoc is never in use: it has nothing to do. |
| optdoc | ocrdoc reads what typdoc gave (the picture bound into a PDF, as it came: a photo read without preparing it), or the original where that is a PDF. |
| typdoc and optdoc | For a picture: ocrdoc is handed the picture and answers `not-pdf`. |
| ocrdoc | No text layer, no reading, no Markdown; tagdoc describes optdoc's PDF (and finds less to suggest where the pages have no text). |
| tagdoc | The PDF has no description; it is ocrdoc's. |
| all | The error `no-steps`. |

**No step is to force a file type.** typdoc is the one step that changes a document's type; the steps after
it take what they are handed. So far that holds for the chain, not yet for every tool: optdoc still makes a
PDF of a picture, and ocrdoc and tagdoc read PDFs only. They are to learn to keep a picture a picture (the
prepared picture in the format it came in, the reading and the description beside it or in it as medRDS
says for the format); `docs/family-design.md` in optdoc has the plan.

A step that cannot do without another says so (`step-needs`: semdoc, once there, needs ocrdoc's reading).
The PDF carries the configuration documents of the steps that ran, and the chain document says for every
step whether it was in use. With `--config` the chain document decides which steps are in use; `--without`
beside it is a `usage` error.

**Settings** of the steps, each taken by the step that knows it: `--paper`, `--photo` or `--scan`,
`--no-clean-up`, `--colour-pages jpeg|png` (optdoc); `--reader`, `--languages`, `--no-cells`, `--no-areas`
(ocrdoc). With `--config` the chain document decides; a setting beside it is a `usage` error.

**Models.** `--models <folder>` (for `run` and `edit`) is the folder whose models the steps may use; every
step that takes models gets it, and what does not lie there is done without. It is no setting: the chain
document does not name it, and it may stand beside `--config`.

**Progress** with `--progress`: a line per step and page on standard error,
`{"step": "optdoc", "page": 1, "of": 2}`.

The answer:

```json
{"interface": 3, "made_with": "docrepro 0.5.0",
 "document": "<folder>/<stem>.pdf", "config": "<folder>/<stem>.docrepro.json",
 "reading": "<folder>/<stem>.reading.json", "markdown": "<folder>/<stem>.md",
 "pages": 2,
 "steps": [{"tool": "optdoc", "used": true, "made_with": "optdoc 0.9.0", "dropped": []},
           {"tool": "ocrdoc", "used": true, "made_with": "ocrdoc 0.3.0", "dropped": [2]},
           {"tool": "tagdoc", "used": false}],
 "not_installed": ["semdoc"]}
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
or `--without` say. typdoc has no tab (it has nothing to decide); for a PDF it says "nothing to do". A
picture goes on as a PDF through typdoc or through optdoc: of the two, the one that is on alone cannot be
switched off. Switching typdoc hands optdoc another file, so optdoc starts anew (the status line says so
where a person's plans went). A step that needs one which is off is off as well. What a person decided in a step that is
switched off is kept, in the chain document too, and is back when the step is switched on again; one
case apart: where optdoc is switched off, ocrdoc reads the original, a different file, and starts anew
(the status line says so).

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
{"interface": 3, "made_with": "docrepro 0.5.0",
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

## The chain document: `docrepro-chain`, version 2

```json
{"format": "docrepro-chain", "version": 2, "made_with": "docrepro 0.5.0",
 "original": {"sha256": "…", "bytes": 245678, "suffix": ".jpg"},
 "steps": [{"tool": "typdoc", "used": true, "made_with": "typdoc 0.2.0",
            "config": {"format": "typdoc-config", "…": "…"}},
           {"tool": "optdoc", "used": true, "made_with": "optdoc 0.9.0",
            "config": {"format": "optdoc-config", "…": "…"}},
           {"tool": "ocrdoc", "used": true, "made_with": "ocrdoc 0.3.0",
            "config": {"format": "ocrdoc-config", "…": "…"}},
           {"tool": "tagdoc", "used": false, "config": {"format": "tagdoc-config", "…": "…"}}]}
```

The original by its SHA-256, and for every step whether it was in use (`used`) and its configuration
document as the step wrote it; no paths, no times. A step in use has `made_with` and `config`. A step that
is off may keep a `config`: what a person decided in it before it was switched off, kept for when it is
switched on again (it takes no part in the result). **The original and the chain document give every file
again, byte for byte**, on the same versions of the steps; `--config` takes the chain document or the PDF
docrepro wrote. A chain document of another original is refused (`config-mismatch`), one that used a step
which is not installed too (`step-missing`): without it, the result cannot be made again. A step the
document does not name is not in use, so that a step installed later changes nothing of what the document
makes; in the window a person can switch it on. The entry of a step that is not installed and was not in
use is carried along as it is. Version 1 (docrepro 0.1 and 0.2) is no longer read.

## Failures

As every tool of docrepro: `error`, `details`, `message` in English and German. docrepro's own kind:

| `error` | when | `details` |
|---|---|---|
| `step-missing` | the chain document used a step that is not installed, or `docrepro <step>` for one | `step` |
| `step-needs` | a step in use needs one that is switched off or not installed | `step`, `needs` |
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
folder of models (`use_models(project, folder)`). A step says in docrepro's list of steps which others it
cannot do without (`needs`). typdoc (order 5) and tagdoc (order 40) join so; semdoc (order 30, takes the
reading, gives annotations, format `semdoc-annotations`) and attdoc (order 50, signs) have their places
already.

## Licence

docrepro is free software under the GNU Affero General Public License 3.0 or later.
