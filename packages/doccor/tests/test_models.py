"""Models: listed with their source, fetched on request and kept only when they are the
file the catalogue names; the network is open for that download alone."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import io
import json
import subprocess
import sys
import threading
import urllib.error
from pathlib import Path

import pytest

from doccor import cli, models
from doccor.errors import DocError

CONTENT = bytes(range(256)) * 600  # 153,600 bytes that stand for a model
MODEL = models.Model(
    name="example-layout", file="example-layout.onnx",
    url="https://models.example/example-layout.onnx",
    sha256=hashlib.sha256(CONTENT).hexdigest(), size=len(CONTENT), licence="Apache-2.0",
    source="https://models.example/", does={"en": "finds areas", "de": "findet Bereiche"})


def _opener(content: bytes, calls: list[str]) -> models.Opener:
    def opener(url: str) -> io.BytesIO:
        calls.append(url)
        return io.BytesIO(content)
    return opener


def test_fetched_once_and_found_again(tmp_path: Path) -> None:
    calls: list[str] = []
    seen: list[tuple[int, int]] = []
    assert models.present(MODEL, tmp_path) is None and models.present(MODEL, None) is None
    path = models.fetch(MODEL, tmp_path / "models", lambda n, m: seen.append((n, m)),
                        _opener(CONTENT, calls))
    assert path == tmp_path / "models" / MODEL.file and path.read_bytes() == CONTENT
    assert calls == [MODEL.url] and seen[-1] == (MODEL.size, MODEL.size)
    assert models.present(MODEL, tmp_path / "models") == path
    assert models.fetch(MODEL, tmp_path / "models", opener=_opener(b"", calls)) == path
    assert calls == [MODEL.url]  # the right file lies there: not fetched again
    assert [p.name for p in (tmp_path / "models").iterdir()] == [MODEL.file]
    listed = models.listing([MODEL], tmp_path / "models")[0]
    assert listed["present"] is True and listed["bytes"] == MODEL.size
    assert models.listing([MODEL])[0]["present"] is None


@pytest.mark.parametrize("content", [CONTENT[:-1], CONTENT + b"more", CONTENT[::-1], b""],
                         ids=["short", "long", "other", "empty"])
def test_another_file_is_not_kept(tmp_path: Path, content: bytes) -> None:
    with pytest.raises(DocError) as caught:
        models.fetch(MODEL, tmp_path, opener=_opener(content, []))
    assert caught.value.kind == "model-checksum" and caught.value.details == {"name": MODEL.name}
    assert list(tmp_path.iterdir()) == []  # neither the file nor the part of it
    (tmp_path / MODEL.file).write_bytes(CONTENT[::-1])  # a file of the right size and name
    assert models.present(MODEL, tmp_path) is None


def test_addresses_that_do_not_answer(tmp_path: Path) -> None:
    def refusing(url: str) -> io.BytesIO:
        raise urllib.error.URLError("no route")

    with pytest.raises(DocError) as caught:
        models.fetch(MODEL, tmp_path, opener=refusing)
    assert caught.value.kind == "model-unreachable"
    plain = models.Model(**{**MODEL.__dict__, "url": "http://models.example/x.onnx"})
    with pytest.raises(DocError) as caught:  # no https address: not even tried
        models.fetch(plain, tmp_path)
    assert caught.value.kind == "model-unreachable"
    with pytest.raises(DocError) as caught:
        models.find([MODEL], "another", "ocrdoc")
    assert caught.value.kind == "unknown-model" and "ocrdoc" in caught.value.message("de")
    assert list(tmp_path.iterdir()) == []


def test_the_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                      capsys: pytest.CaptureFixture[str]) -> None:
    """``models list`` and ``models fetch`` of a tool, answered as every command is."""
    parser = cli.Parser(prog="exampledoc")
    sub = parser.add_subparsers(dest="command", required=True)
    cli.add_models(sub, "exampledoc")
    run = sub.add_parser("run")
    cli.add_models_option(run)
    assert parser.parse_args(["run", "--models", str(tmp_path)]).models == tmp_path
    commands = {"models": cli.models_command([MODEL], "exampledoc"),
                "run": lambda _args: {}}
    monkeypatch.setattr(models, "_open", lambda url: io.BytesIO(CONTENT))

    def answer(argv: list[str]) -> tuple[int, dict]:
        status = cli.main(parser, commands, tool="exampledoc", version="1.0", interface=1,
                          argv=argv)
        return status, json.loads(capsys.readouterr().out)

    status, listed = answer(["models", "list"])
    assert status == 0 and listed["models"][0]["name"] == MODEL.name
    assert listed["models"][0]["url"] == MODEL.url and listed["models"][0]["present"] is None
    status, fetched = answer(["models", "fetch", MODEL.name, "--to", str(tmp_path / "m")])
    assert status == 0 and fetched["sha256"] == MODEL.sha256
    assert Path(fetched["file"]).read_bytes() == CONTENT
    status, listed = answer(["models", "list", "--models", str(tmp_path / "m")])
    assert listed["models"][0]["present"] is True
    status, failed = answer(["models", "fetch", "nothing", "--to", str(tmp_path / "m")])
    assert status == 2 and failed["error"] == "unknown-model"
    assert isinstance(parser.parse_args(["models", "list"]), argparse.Namespace)


def test_the_network_is_open_for_the_download_alone(tmp_path: Path) -> None:
    """With the network closed, fetching a model goes out (here to a server on this
    computer) and nothing else does, before or after."""
    (tmp_path / "served").mkdir()
    (tmp_path / "served" / MODEL.file).write_bytes(CONTENT)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(tmp_path / "served"), **kwargs)  # type: ignore[arg-type]

        def log_message(self, *_args: object) -> None:
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/{MODEL.file}"
        code = f"""
import urllib.request
from pathlib import Path
from doccor import models, offline
from doccor.errors import DocError

model = models.Model(name="m", file={MODEL.file!r}, url={url!r}, sha256={MODEL.sha256!r},
                     size={MODEL.size}, licence="x", source="x", does={{}})
offline.forbid_network("exampledoc")
def tried() -> str:
    try:
        urllib.request.urlopen({url!r}, timeout=5).read()
    except Exception as e:
        return type(e).__name__
    return "went out"
print(tried())
path = models.fetch(model, Path({str(tmp_path / "kept")!r}), opener=models._open)
print(path.stat().st_size)
print(tried(), offline.attempts)
"""
        run = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             check=False)
    finally:
        server.shutdown()
    assert run.returncode == 0, run.stderr
    before, size, after = run.stdout.split("\n")[:3]
    assert before == "NetworkForbidden" and size == str(MODEL.size)
    assert after.split() == ["NetworkForbidden", "2"]
