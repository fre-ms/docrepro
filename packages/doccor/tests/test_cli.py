"""A tool's command line: one JSON answer whatever happens, usage errors as answers,
standard error for the tool's own lines, no network."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap

TOOL = textwrap.dedent(r'''
    import os, socket, sys
    from doccor import cli
    from doccor.errors import DocError

    def hello(args):
        cli.progress(1, 2)
        os.write(2, b"native noise\n")
        return {"hello": args.name}

    def fails(args):
        raise DocError("missing", tool="sometool")

    def breaks(args):
        raise RuntimeError("Gotthard Beispiel, geb. 21.07.1959")

    def online(args):
        socket.getaddrinfo("example.org", 443)
        return {}

    parser = cli.Parser(prog="sometool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hello").add_argument("name")
    for name in ("fails", "breaks", "online"):
        sub.add_parser(name)
    commands = {"hello": hello, "fails": fails, "breaks": breaks, "online": online}
    sys.exit(cli.main(parser, commands, tool="sometool", version="1.0", interface=3))
''')


def _run(*argv: str) -> tuple[int, dict, str]:
    run = subprocess.run([sys.executable, "-c", TOOL, *argv], capture_output=True, text=True,
                         timeout=60)
    return run.returncode, json.loads(run.stdout), run.stderr


def test_one_answer_whatever_happens() -> None:
    """Success, failure, a fault and the network each give one JSON object with the head."""
    status, answer, err = _run("hello", "Kalium")
    assert status == 0
    assert answer == {"interface": 3, "made_with": "sometool 1.0", "hello": "Kalium"}
    assert err == '{"page": 1, "of": 2}\n'  # the tool's own line, no native noise
    status, answer, _ = _run("fails")
    assert status == 2 and answer["error"] == "missing"
    assert answer["message"]["de"] == "Die Datei oder den Ordner gibt es nicht."
    status, answer, _ = _run("breaks")
    assert status == 2 and answer["error"] == "internal"
    assert answer["details"] == {"error": "RuntimeError"} and "Gotthard" not in json.dumps(answer)
    status, answer, _ = _run("online")
    assert status == 2 and answer["error"] == "network"
    assert "sometool never" in answer["message"]["en"]


def test_usage_errors_are_answers() -> None:
    """An invalid command line answers "usage" without repeating the arguments."""
    status, answer, err = _run("hello", "/Users/someone/Erika Musterfrau.pdf", "--nonsense")
    assert status == 2 and answer["error"] == "usage"
    assert "see sometool --help" in answer["message"]["en"]
    assert "Musterfrau" not in json.dumps(answer) and "Musterfrau" not in err
