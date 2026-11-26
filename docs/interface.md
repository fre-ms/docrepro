# docrepro's command line as an interface

**Interface 1**, since docrepro 0.1.0 (this description: docrepro 0.2.0). This is what a program may rely on
when it calls docrepro, a records app above all, which ships one program instead of one per step.

Every answer carries `interface`; it goes up when something a caller relies on changes in a way that breaks
it. Within one interface, new fields, options and kinds of error may come; a caller ignores what it does not
know. The steps' own command lines (`docrepro optdoc …`, `docrepro ocrdoc …`) keep their own interfaces
(optdoc's 3, ocrdoc's 1), described in their repositories.

**Added within interface 1 (docrepro 0.2.0):** models as an optional download: the commands `models list`
and `models fetch`, the option `--models`, and `models` in the answer of `about`.

## Calling

```
docrepro about
docrepro run  <original> --out <folder> [--config <chain>] [settings] [--progress]
docrepro edit <original> --out <folder> [--config <chain>] [settings] [--language de|en]
docrepro models list [--models <folder>]
docrepro models fetch <name> --to <folder> [--progress]
docrepro <step> …                      the step's own command line (optdoc, ocrdoc; semdoc, tagdoc once installed)
docrepro --version
```

Every command writes **exactly one JSON object to standard output**, whether it succeeds or not, and ends
with exit status **0** on success and **2** on failure. Standard error is free for `--progress` and the usage
line of an invalid command line. No answer and no message quotes the content of a document or a path given
to docrepro. docrepro never goes on the network while it works; the one command that goes out is
`models fetch`, on request, for one file from the address listed (below).

| field | example | meaning |
|---|---|---|
| `interface` | `1` | the version of this description |
| `made_with` | `"docrepro 0.2.0"` | the program and its version |

## `about`

```json
{"interface": 1, "made_with": "docrepro 0.2.0", "version": "0.2.0", "window": true,
 "steps": [{"tool": "optdoc", "order": 10, "takes": "original", "gives": "pdf",
            "does": {"en": "…", "de": "…"}, "planned": false, "installed": true, "version": "0.8.0"},
           {"tool": "ocrdoc", "order": 20, "…": "…"},
           {"tool": "semdoc", "order": 30, "takes": "reading", "gives": "annotations",
            "planned": true, "installed": false, "version": null},
           {"tool": "tagdoc", "order": 40, "…": "…"}],
 "models": [{"step": "optdoc", "name": "page-orientation", "…": "…", "present": null}]}
```

`models` are the models the installed steps can use, as `models list` gives them.

## `run`: the whole way

`<original>` is a photo, an image or a PDF; docrepro never changes it and always starts from it. It takes it
through every installed step in their order; each step's input is the result of the one before. Into
`<folder>` (made when missing; default `<original>.docrepro` beside it) it writes the last step's files under
the original's stem, and **nothing anywhere else** (what the steps make on the way goes into the hidden
folder `.docrepro-work` inside `<folder>` and is removed at once):

| file | what it is |
|---|---|
| `<stem>.pdf` | the document: optdoc's prepared pages with ocrdoc's text layer and tagdoc's description (medRDS 7: XMP and the information dictionary), carrying every step's configuration document (`optdoc.json`, `ocrdoc.json`, `tagdoc.json`) and the chain document (`docrepro.json`) |
| `<stem>.reading.json` | ocrdoc's reading (`ocrdoc-reading` 1) |
| `<stem>.md` | the text as Markdown |
| `<stem>.docrepro.json` | the chain document (below) |

tagdoc adds `<stem>.pdf.xmp` where the description goes into a sidecar; a step to come adds its own files
(semdoc its annotations).

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
{"interface": 1, "made_with": "docrepro 0.2.0",
 "pdf": "<folder>/<stem>.pdf", "config": "<folder>/<stem>.docrepro.json",
 "reading": "<folder>/<stem>.reading.json", "markdown": "<folder>/<stem>.md",
 "pages": 2,
 "steps": [{"tool": "optdoc", "made_with": "optdoc 0.8.0", "dropped": []},
           {"tool": "ocrdoc", "made_with": "ocrdoc 0.2.0", "dropped": [2]}],
 "not_installed": ["semdoc", "tagdoc"]}
```

`dropped` names, per step, the pages (from 1) whose decisions a person had made in that step and that went,
because an earlier step moved the page (turned, unwarped or straightened it otherwise).

## `edit`: one window for the whole way

Opens a window with a tab for every installed step, in their order: optdoc's preparation (1), ocrdoc's
filters for OCR (2), areas (3) and text (4), tagdoc's description (5); a step to come brings its tab. When the
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
{"interface": 1, "made_with": "docrepro 0.2.0",
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

## The chain document: `docrepro-chain`, version 1

```json
{"format": "docrepro-chain", "version": 1, "made_with": "docrepro 0.2.0",
 "original": {"sha256": "…", "bytes": 245678, "suffix": ".jpg"},
 "steps": [{"tool": "optdoc", "made_with": "optdoc 0.8.0", "config": {"format": "optdoc-config", "…": "…"}},
           {"tool": "ocrdoc", "made_with": "ocrdoc 0.2.0", "config": {"format": "ocrdoc-config", "…": "…"}}]}
```

The original by its SHA-256, and every step's configuration document as the step wrote it; no paths, no
times. **The original and the chain document give every file again, byte for byte**, on the same versions of
the steps; `--config` takes the chain document or the PDF docrepro wrote. A chain document of another
original is refused (`config-mismatch`), one that names a step which is not installed too (`step-missing`):
without it, the result cannot be made again. A step installed later than the chain document was written
starts fresh.

## Failures

As every tool of docrepro: `error`, `details`, `message` in English and German. docrepro's own kind:

| `error` | when | `details` |
|---|---|---|
| `step-missing` | the chain document names a step that is not installed, or `docrepro <step>` for one | `step` |

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
folder of models (`use_models(project, folder)`). tagdoc (order 40) joins so; semdoc (order 30, takes the reading, gives
annotations, format `semdoc-annotations`) has its place already.

## Licence

docrepro is free software under the GNU Affero General Public License 3.0 or later.
