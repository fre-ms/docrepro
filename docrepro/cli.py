"""The command line: ``docrepro about``, ``docrepro run``, ``docrepro edit`` (the window),
``docrepro models`` (the models of every step: listed, and fetched on request), and every
step's own command line as ``docrepro <tool> …`` (``docrepro optdoc run …``, ``docrepro ocrdoc
edit …``), so that one program holds them all.

Every command answers with exactly one JSON object on standard output, whether it
succeeds or fails; a failure answers with its kind and its message in English and
German, and ends with exit status 2.  No answer and no message quotes a document or its
path.  ``--progress`` writes a line of JSON per step and page to standard error.  ``run``
and ``edit`` take a chain document (``--config``) and make the same results from it
every time (:mod:`docrepro.chain`).  The manners are doccor's (:mod:`doccor.cli`): one
JSON answer, standard error for its own lines, never the network.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from doccor import cli as frame
from doccor.models import Model

from docrepro import __version__, gui
from docrepro.chain import SUFFIX, Chain, load_chain
from docrepro.errors import DocreproError
from docrepro.steps import STEPS, adapter, catalogue

INTERFACE = 1  # the version of docs/interface.md the answers follow
TOOL = "docrepro"

# the settings of the steps, by option: the name a step's options know it by
_SETTINGS = {"paper": "paper", "photo": "photo", "no_clean_up": "clean_up",
             "colour_pages": "colour_pages", "reader": "reader", "languages": "languages",
             "no_cells": "cells", "no_areas": "areas"}


def _progress(step: str, page: int, of: int) -> None:
    """One line of progress on standard error: the step, the page about to be done, of
    how many."""
    frame.said.write(json.dumps({"step": step, "page": page, "of": of}) + "\n")
    frame.said.flush()


def _about(args: argparse.Namespace) -> dict[str, Any]:
    """The steps, which are installed, and whether the window can open."""
    steps = []
    for step in STEPS:
        made = adapter(step)
        steps.append({"tool": step.name, "order": step.order, "takes": step.takes,
                      "gives": step.gives, "does": step.does, "planned": step.planned,
                      "installed": made is not None,
                      "version": made.version if made is not None else None})
    return {"version": __version__, "steps": steps, "window": gui.available(),
            "models": [{"step": name, **model.as_dict()} for name, model in _catalogue()]}


def _catalogue() -> list[tuple[str, Model]]:
    """The models the installed steps can use, each with the step that lists it, in the
    order of the steps; a model two steps list is named once."""
    found: dict[str, tuple[str, Model]] = {}
    for step in STEPS:
        made = adapter(step)
        for model in catalogue(made) if made is not None else ():
            found.setdefault(model.name, (step.name, model))
    return list(found.values())


def _models(args: argparse.Namespace) -> dict[str, Any]:
    """``models list`` and ``models fetch`` over the models of every installed step; the
    answers are a step's own, with the step that lists the model."""
    listed = _catalogue()
    step_of = {model.name: name for name, model in listed}
    answer = frame.models_command([model for _name, model in listed], TOOL)(args)
    if "models" in answer:
        return {"models": [{"step": step_of[m["name"]], **m} for m in answer["models"]]}
    return {"step": step_of[answer["model"]], **answer}


def _settings(args: argparse.Namespace) -> dict[str, Any]:
    """The settings given on the command line, as the steps' options name them."""
    found: dict[str, Any] = {}
    for option, name in _SETTINGS.items():
        value = getattr(args, option)
        if value is None:
            continue
        found[name] = (not value) if option.startswith("no_") else value
    return found


def _chain(args: argparse.Namespace) -> Chain:
    """The chain on the original: from its chain document (``--config``, a JSON file or
    a PDF docrepro wrote), or fresh with the settings given.  Both at once is a "usage"."""
    settings = _settings(args)
    if args.config is not None:
        if settings:
            raise DocreproError("usage")
        chain = Chain.open(args.file, chain=load_chain(args.config))
    else:
        chain = Chain.open(args.file, settings=settings)
    chain.models = args.models
    return chain


def _out(args: argparse.Namespace) -> Path:
    """The folder for the results: ``--out``, else ``<file>.docrepro`` beside the file."""
    return args.out or args.file.with_name(f"{args.file.stem}.docrepro")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    """Take the original through every step and write the results."""
    return _chain(args).run(_out(args), _progress if args.progress else None)


def _edit(args: argparse.Namespace) -> dict[str, Any]:
    """Open the window on the original; write the results when the person applies, the
    chain document alone when they will continue later, nothing when they cancel."""
    if not gui.available():
        raise DocreproError("no-gui")
    from docrepro.gui.app import edit

    chain = _chain(args)
    outcome, configs = edit(chain, _out(args), language=args.language,
                            self_test=args.self_test)
    if outcome == "cancelled":
        raise DocreproError("cancelled")
    if outcome == "saved":
        saved = chain.save(configs, _out(args) / f"{args.file.stem}{SUFFIX}")
        return {"config": str(saved), "finished": False}
    return {**chain.run(_out(args), _progress if args.progress else None, configs),
            "finished": True}


def _document_options(pr: argparse.ArgumentParser) -> None:
    """The options of run and edit.  The settings default to None, so that the use of one
    beside ``--config`` can be told."""
    pr.add_argument("file", type=Path, help="the original: a photo, an image or a PDF")
    pr.add_argument("--out", type=Path, help="folder for the results (default: <file>.docrepro/)")
    pr.add_argument("--config", type=Path,
                    help="chain document to start from: <name>.docrepro.json, or a PDF "
                         "docrepro wrote")
    pr.add_argument("--paper", help="optdoc: paper an image is placed on (a4, a5, a3, letter, "
                                    "legal, image)")
    kind = pr.add_mutually_exclusive_group()
    kind.add_argument("--photo", dest="photo", action="store_const", const=True,
                      help="optdoc: take every page without text for a photo")
    kind.add_argument("--scan", dest="photo", action="store_const", const=False,
                      help="optdoc: take every page for a scan: never unwarp")
    pr.add_argument("--no-clean-up", action="store_const", const=True,
                    help="optdoc: leave the pages as they came unless a person prepares them")
    pr.add_argument("--colour-pages", choices=["jpeg", "png"],
                    help="optdoc: how a page in colour is stored (default: jpeg)")
    pr.add_argument("--reader", choices=["auto", "rapidocr", "tesseract", "none"],
                    help="ocrdoc: OCR engine (default: auto)")
    pr.add_argument("--languages", help="ocrdoc: language packs (deu+eng for Tesseract)")
    pr.add_argument("--no-cells", action="store_const", const=True,
                    help="ocrdoc: find no tables with their cells")
    pr.add_argument("--no-areas", action="store_const", const=True,
                    help="ocrdoc: find no barcodes, stamps, pictures or handwriting")
    frame.add_models_option(pr)
    pr.add_argument("--progress", action="store_true",
                    help='a line {"step": …, "page": n, "of": m} on standard error per page')


def _parser() -> argparse.ArgumentParser:
    """The argument parser of docrepro's own commands."""
    p = frame.Parser(prog=TOOL, description="Reproduce photographed and scanned documents "
                                            "as digital documents, every step reproducible.")
    p.add_argument("--version", action="version", version=f"{TOOL} {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("about", help="the steps, which are installed, and the window")
    ru = sub.add_parser("run", help="take a document through every step and write the results")
    _document_options(ru)
    ed = sub.add_parser("edit", help="open the window: every step by eye")
    _document_options(ed)
    ed.add_argument("--language", choices=["de", "en"],
                    help="language of the window (default: the system's)")
    ed.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    frame.add_models(sub, TOOL)
    for step in STEPS:
        sub.add_parser(step.name, help=f"{step.name}'s own command line ({step.does['en']})"
                       + (", planned" if step.planned else ""), add_help=False)
    return p


COMMANDS: dict[str, Callable[[argparse.Namespace], dict[str, Any]]] = {
    "about": _about, "run": _run, "edit": _edit, "models": _models}


def _missing(name: str) -> Callable[[argparse.Namespace], dict[str, Any]]:
    """A step's command line where its tool is not installed: the error "step-missing"."""
    def command(_args: argparse.Namespace) -> dict[str, Any]:
        raise DocreproError("step-missing", step=name)
    return command


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line; returns the exit status.  ``docrepro <tool> …`` hands the
    rest to that step's own command line."""
    import sys

    given = list(sys.argv[1:] if argv is None else argv)
    if given and given[0] in {s.name for s in STEPS}:
        name = given[0]
        step = next(s for s in STEPS if s.name == name)
        if adapter(step) is not None:
            from importlib import import_module

            tool_main: Callable[[Sequence[str]], int] = import_module(f"{name}.cli").main
            return tool_main(given[1:])
        commands = {**COMMANDS, name: _missing(name)}
        return frame.main(_parser(), commands, tool=TOOL, version=__version__,
                          interface=INTERFACE, argv=[name])
    return frame.main(_parser(), COMMANDS, tool=TOOL, version=__version__,
                      interface=INTERFACE, argv=given)
