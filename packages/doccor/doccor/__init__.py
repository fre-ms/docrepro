"""doccor: what the document tools share (optdoc, ocrdoc, …), so that it is written once.

- :mod:`doccor.documents`: the configuration document every tool writes for every input,
  from which its step is made again, byte for byte, and resumed: its bytes, the SHA-256 of
  the input, reading it from its file or from a PDF that carries it, embedding it, the
  PDF's file identifier made from it;
- :mod:`doccor.errors`: kinds of error with their wording in English and German; every
  tool registers its own and its name;
- :mod:`doccor.cli`: the manners of a tool's command line: exactly one JSON answer,
  usage errors as answers, standard error for the tool's own lines only;
- :mod:`doccor.offline`: no network, and ONNX Runtime's telemetry switched off;
- :mod:`doccor.models`: models a step may use, listed with their source, fetched on a
  person's request and never otherwise;
- :mod:`doccor.pictures`: a picture as the tools look at it: upright, its size in its own
  pixels, and as a page whose long side is that of A4;
- :mod:`doccor.gui`: the window's building blocks (the page view, work off the window's
  thread, words in two languages).
"""

__version__ = "0.3.0"
