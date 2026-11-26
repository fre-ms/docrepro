# doccor

The shared core of the document tools that reproduce photographed and scanned documents as
digital documents, one step each: optdoc (prepares the page), ocrdoc (recognises it), and
later semdoc (finds medical terms and identifying information) and tagdoc (sets a
document's metadata). What every one of them needs is here, once:

- **The configuration document** (`doccor.documents`). Every tool writes one for every
  input (`<stem>.<tool>.json`): everything that decides its step's result, and the results
  of everything that is not deterministic, so that the step is made again from it, byte
  for byte, and a person can stop and go on later. Its bytes, the SHA-256 of the input,
  reading it from its file or from a PDF that carries it, embedding it without dates, and
  the PDF's file identifier made from it.
- **Kinds of error** (`doccor.errors`), worded in English and German, never quoting a
  document or its path; every tool registers its own kinds and its name.
- **The manners of a command line** (`doccor.cli`): exactly one JSON answer whatever
  happens, usage errors as answers, standard error for the tool's own lines.
- **No network** (`doccor.offline`): nothing resolves a name or connects once a tool's
  command line has started; ONNX Runtime's telemetry is switched off before it loads.
- **Models a step may use** (`doccor.models`): a tool lists them in its own code, each with
  its address, SHA-256, size and licence. One command goes on the network, on a person's
  request: `<tool> models fetch <name> --to <folder>`, which keeps a file only when it is
  the one listed. Work never goes out: `run` and `edit` take `--models <folder>` and do
  without what is not there. What a model found is kept in the configuration document, so
  that making the result again needs the model no more.
- **The window's building blocks** (`doccor.gui`, extra `gui`): the page view, work off the
  window's thread, words in two languages.

**Status: pre-alpha (0.2.0).** The code comes from optdoc 0.6.0, with its behaviour.

## Install

Python 3.12 or later, with [uv](https://docs.astral.sh/uv/): `uv sync --dev --extra gui`,
tests with `uv run pytest`.

## Licence

GNU Affero General Public License 3.0 or later (see `LICENSE`), as the tools that share it.
