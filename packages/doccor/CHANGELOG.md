# Changelog

## 0.1.0 (2026-11-26)

### Added

- The shared core of the document tools, taken from optdoc 0.6.0 with its behaviour:
  `doccor.documents` (configuration documents: bytes, SHA-256, reading from a file or a
  PDF, embedding without dates, the PDF's identifier), `doccor.errors` (kinds of error in
  English and German, registered by each tool, naming it), `doccor.cli` (one JSON answer,
  usage errors as answers, standard error for the tool's own lines), `doccor.offline` (no
  network, no ONNX Runtime telemetry), `doccor.gui` (page view, worker, words).
