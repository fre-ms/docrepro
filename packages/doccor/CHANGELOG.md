# Changelog

## 0.2.0 (2026-11-26)

### Added

- **Models a step may use** (`doccor.models`): a tool's catalogue of models, each with the
  address it is fetched from, its SHA-256, size and licence; `fetch`, which keeps a file only
  when it is the one the catalogue names; `present`, which finds a model in a models folder.
  A model that is missing is no error: the step works without it.
- **The one door** (`doccor.offline.network_allowed`): the network, closed for everything
  else, is open for the time of that download alone.
- **For a tool's command line** (`doccor.cli`): `add_models` and `models_command` give it
  `models list [--models <folder>]` and `models fetch <name> --to <folder> [--progress]`;
  `add_models_option` gives `run` and `edit` the option `--models <folder>`.
- Kinds of error `unknown-model`, `model-unreachable`, `model-checksum`.

## 0.1.0 (2026-11-26)

### Added

- The shared core of the document tools, taken from optdoc 0.6.0 with its behaviour:
  `doccor.documents` (configuration documents: bytes, SHA-256, reading from a file or a
  PDF, embedding without dates, the PDF's identifier), `doccor.errors` (kinds of error in
  English and German, registered by each tool, naming it), `doccor.cli` (one JSON answer,
  usage errors as answers, standard error for the tool's own lines), `doccor.offline` (no
  network, no ONNX Runtime telemetry), `doccor.gui` (page view, worker, words).
