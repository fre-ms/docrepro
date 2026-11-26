"""The manners every tool's command line keeps.

- **Exactly one JSON object on standard output**, whether the command succeeds or fails,
  so that programs in any language can call a tool as a helper (a Tauri sidecar, for
  one). Its head names the version of the tool's interface (``interface``) and the tool
  (``made_with``).
- **A failure** answers with its kind, its details and its message in English and German
  (:mod:`doccor.errors`), and ends with exit status 2; an invalid command line too (its
  usage line goes to standard error, the arguments are never repeated: one of them is
  the path of a document).
- **Standard error carries the tool's own lines only** (progress): libraries write to it
  below Python, where no setting reaches them, so for the time of a command the
  descriptor points at the null device and the tool writes through a copy.
- **No network** (:mod:`doccor.offline`), and no warnings or MuPDF messages, which may
  name a file.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import warnings
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any, NoReturn, TextIO

from doccor import offline
from doccor.errors import LANGUAGES, DocError

STATUS_ERROR = 2
said: TextIO = sys.stderr  # where the tool's own lines on standard error go (own_stderr)

Command = Callable[[argparse.Namespace], dict[str, Any]]


class Parser(argparse.ArgumentParser):
    """An argument parser whose complaints become an answer of kind "usage" naming the
    tool (its ``prog``): the usage line goes to standard error, the arguments themselves
    are never repeated."""

    def error(self, message: str) -> NoReturn:
        """Show the usage and fail with kind "usage"."""
        self.print_usage(said)
        raise DocError("usage", tool=self.prog)


def progress(page: int, of: int) -> None:
    """One line of progress on standard error: the page about to be done, of how many."""
    said.write(json.dumps({"page": page, "of": of}) + "\n")
    said.flush()


def failure(error: DocError) -> dict[str, Any]:
    """The answer for a failure: its kind, its details, its message in every language."""
    return {"error": error.kind, "details": error.details,
            "message": {language: error.message(language) for language in LANGUAGES}}


def quiet() -> None:
    """Keep standard error for the progress lines: no warnings of the libraries, and no
    messages of MuPDF, which may name the file it failed on."""
    import pymupdf

    warnings.simplefilter("ignore")
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)


@contextlib.contextmanager
def own_stderr() -> Iterator[TextIO]:
    """Standard error for the tool's own lines only.  Libraries write to it below Python,
    where no setting reaches them (ONNX Runtime warned about PCI buses on Linux, in
    colour); for the time of a command the descriptor points at the null device, and the
    tool's lines go through a copy of the real one, which is put back afterwards."""
    sys.stderr.flush()
    try:
        kept = os.dup(2)
    except OSError:  # no standard error to begin with
        yield sys.stderr
        return
    null = os.open(os.devnull, os.O_WRONLY)
    os.dup2(null, 2)
    os.close(null)
    stream = os.fdopen(os.dup(kept), "w", encoding="utf-8", errors="replace")
    try:
        yield stream
    finally:
        stream.close()
        sys.stderr.flush()
        os.dup2(kept, 2)
        os.close(kept)


def main(parser: argparse.ArgumentParser, commands: Mapping[str, Command], *, tool: str,
         version: str, interface: int, argv: Sequence[str] | None = None) -> int:
    """Run a tool's command line: close the network, parse (the parser's subcommand is
    ``args.command``), run the command, and print its answer or its failure as one JSON
    object.  Returns the exit status: 0, or 2 for a failure."""
    global said
    offline.no_telemetry()
    offline.forbid_network(tool)
    quiet()
    try:
        with own_stderr() as said:
            try:
                args = parser.parse_args(argv)
                answer, status = commands[args.command](args), 0
            except DocError as error:
                answer, status = failure(error), STATUS_ERROR
            except Exception as error:  # a fault of the tool: its message might quote a document
                answer = failure(DocError("internal", tool=tool, error=type(error).__name__))
                status = STATUS_ERROR
    finally:  # --help and --version leave by SystemExit
        said = sys.stderr
    head = {"interface": interface, "made_with": f"{tool} {version}"}
    json.dump({**head, **answer}, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return status
