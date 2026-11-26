# docrepro's command line as an interface

**Interface 1**, since docrepro 0.1.0. This is what a program may rely on when it calls docrepro, a records
app above all, which ships one program instead of one per step.

Every answer carries `interface`; it goes up when something a caller relies on changes in a way that breaks
it. Within one interface, new fields, options and kinds of error may come; a caller ignores what it does not
know. The steps' own command lines (`docrepro optdoc …`, `docrepro ocrdoc …`) keep their own interfaces
(optdoc's 3, ocrdoc's 1), described in their repositories.

## Calling

```
docrepro about
docrepro run  <original> --out <folder> [--config <chain>] [settings] [--progress]
docrepro edit <original> --out <folder> [--config <chain>] [settings] [--language de|en]
docrepro <step> …                      the step's own command line (optdoc, ocrdoc; semdoc, tagdoc once installed)
docrepro --version
```

Every command writes **exactly one JSON object to standard output**, whether it succeeds or not, and ends
with exit status **0** on success and **2** on failure. Standard error is free for `--progress` and the usage
line of an invalid command line. No answer and no message quotes the content of a document or a path given
to docrepro. docrepro never goes on the network.

| field | example | meaning |
|---|---|---|
| `interface` | `1` | the version of this description |
| `made_with` | `"docrepro 0.1.0"` | the program and its version |

## `about`

```json
{"interface": 1, "made_with": "docrepro 0.1.0", "version": "0.1.0", "window": true,
 "steps": [{"tool": "optdoc", "order": 10, "takes": "original", "gives": "pdf",
            "does": {"en": "…", "de": "…"}, "planned": false, "installed": true, "version": "0.7.0"},
           {"tool": "ocrdoc", "order": 20, "…": "…"},
           {"tool": "semdoc", "order": 30, "takes": "reading", "gives": "annotations",
            "planned": true, "installed": false, "version": null},
           {"tool": "tagdoc", "order": 40, "…": "…"}]}
```

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

**Progress** with `--progress`: a line per step and page on standard error,
`{"step": "optdoc", "page": 1, "of": 2}`.

The answer:

```json
{"interface": 1, "made_with": "docrepro 0.1.0",
 "pdf": "<folder>/<stem>.pdf", "config": "<folder>/<stem>.docrepro.json",
 "reading": "<folder>/<stem>.reading.json", "markdown": "<folder>/<stem>.md",
 "pages": 2,
 "steps": [{"tool": "optdoc", "made_with": "optdoc 0.7.0", "dropped": []},
           {"tool": "ocrdoc", "made_with": "ocrdoc 0.1.0", "dropped": [2]}],
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

## The chain document: `docrepro-chain`, version 1

```json
{"format": "docrepro-chain", "version": 1, "made_with": "docrepro 0.1.0",
 "original": {"sha256": "…", "bytes": 245678, "suffix": ".jpg"},
 "steps": [{"tool": "optdoc", "made_with": "optdoc 0.7.0", "config": {"format": "optdoc-config", "…": "…"}},
           {"tool": "ocrdoc", "made_with": "ocrdoc 0.1.0", "config": {"format": "ocrdoc-config", "…": "…"}}]}
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
`no-gui`, `network`, `usage`, `internal`). A step's own failure comes with the step's kind (optdoc's
`unsupported`, ocrdoc's `no-reader` …).

## Steps to come

A step joins the chain by being installed: docrepro brings the adapters of optdoc and ocrdoc; any other step
brings its own through the entry-point group `docrepro.steps`, named after the step. An adapter opens the
step's project on its input (fresh with the settings, or as its configuration document says), gives the
configuration document, makes and writes the result (a PDF for the next step, and its own files), and names
the pages whose decisions went (`docrepro.steps.Adapter`), and may bring a panel for the window
(`panel(project, words)`). tagdoc (order 40) joins so; semdoc (order 30, takes the reading, gives
annotations, format `semdoc-annotations`) has its place already.

## Licence

docrepro is free software under the GNU Affero General Public License 3.0 or later.
