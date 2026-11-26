"""No network: once the door is closed, nothing resolves a name or connects, and the
attempt names the tool; ONNX Runtime's telemetry is switched off before it loads.  Run in
a process of its own, since the door does not open again."""

from __future__ import annotations

import subprocess
import sys

SCRIPT = r'''
import os, socket, json
from doccor import offline
from doccor.errors import DocError
assert offline.no_telemetry() and os.environ["ORT_DISABLE_TELEMETRY"] == "1"
offline.forbid_network("sometool")
said = []
for attempt in (lambda: socket.getaddrinfo("example.org", 443),
                lambda: socket.create_connection(("127.0.0.1", 9)),
                lambda: socket.socket(socket.AF_INET).connect(("127.0.0.1", 9))):
    try:
        attempt()
        said.append("went out")
    except DocError as e:
        said.append(e.kind + ": " + e.message("en"))
import sys
if sys.platform != "win32":  # Windows pairs sockets over loopback, which is refused too
    a, b = socket.socketpair(socket.AF_UNIX)  # local sockets still work
    a.sendall(b"x"); assert b.recv(1) == b"x"
print(json.dumps({"said": said, "attempts": offline.attempts,
                  "closed": offline.network_forbidden()}))
'''


def test_the_door_is_closed() -> None:
    """Every way out is refused and counted; Unix sockets still work (Windows has none to
    pair)."""
    import json

    run = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["attempts"] == 3 and result["closed"]
    assert all(s.startswith("network: ") and "which sometool never does" in s
               for s in result["said"])
