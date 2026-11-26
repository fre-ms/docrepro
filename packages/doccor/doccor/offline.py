"""The tools never go on the network; :func:`forbid_network` makes sure nothing they load does.

The documents they read are often a patient's, and they run on computers that may have
no network at all.  Everything they need travels with them.  Some libraries can download
models and dictionaries they do not find, though, and others may want to look something
up.  A tool's command line therefore closes the door before it does anything else:
every attempt to resolve a name or open a connection raises :class:`NetworkForbidden` (a
:class:`~doccor.errors.DocError` of kind "network") instead of going out, and is counted.

An application that embeds a tool decides for its own process; the guard is not set by
importing anything.  Unix sockets (``AF_UNIX``) stay usable; internet sockets are refused
even towards this computer (loopback), which the tools have no use for either.

The guard sees what Python does; native code passes it by.  ONNX Runtime, which runs
the OCR models, carries Microsoft's telemetry (1DS) in its native library: measured with
onnxruntime 1.32 on macOS, every run wrote a device identifier, the computer's model,
processor and system into a queue for sending, under
``~/Library/Application Support/Microsoft/DeveloperTools/.onnxruntime`` and a ``.ses``
file in the temporary folder.  No document goes into it, but nothing is to leave the
computer, and nothing is to be written outside the folder given.  The library reads
``ORT_DISABLE_TELEMETRY`` once, when it is loaded; :func:`no_telemetry` sets it, to be
called before ONNX Runtime is loaded (its own ``disable_telemetry_events()`` comes too
late: the queue is set up by then).  With it, nothing is written and nothing is queued.
"""

from __future__ import annotations

import os
import socket
import sys
from typing import Any

from doccor.errors import DocError

attempts = 0  # how many times something tried to go out since the guard was set
_closed = False
_tool = "doccor"  # the tool that closed the door, named in the error


class NetworkForbidden(DocError):
    """Something tried to reach the network; nothing was sent."""

    def __init__(self, tool: str) -> None:
        super().__init__("network", tool=tool)


def _refuse(*_args: Any, **_kwargs: Any) -> Any:
    """Count the attempt and refuse it."""
    global attempts
    attempts += 1
    raise NetworkForbidden(_tool)


class _GuardedSocket(socket.socket):
    """A socket that may only be local: connecting or sending to an address of the
    internet families is refused."""

    def connect(self, address: Any) -> None:  # type: ignore[override]
        """Connect, unless the socket would leave the computer."""
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _refuse()
        super().connect(address)

    def connect_ex(self, address: Any) -> int:  # type: ignore[override]
        """As :meth:`connect`."""
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _refuse()
        return super().connect_ex(address)

    def sendto(self, *args: Any) -> int:  # type: ignore[override]
        """Send a datagram, unless it would leave the computer."""
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _refuse()
        return super().sendto(*args)


def forbid_network(tool: str = "doccor") -> None:
    """From now on, no name is resolved and no internet socket connects in this process;
    an attempt names ``tool`` in its message."""
    global _closed, _tool
    _tool = tool
    if _closed:
        return
    socket.socket = _GuardedSocket  # type: ignore[misc]
    socket.getaddrinfo = _refuse  # type: ignore[assignment]
    socket.gethostbyname = _refuse  # type: ignore[assignment]
    socket.gethostbyname_ex = _refuse  # type: ignore[assignment]
    socket.create_connection = _refuse  # type: ignore[assignment]
    _closed = True


def no_telemetry() -> bool:
    """Switch off ONNX Runtime's telemetry, which only works before the library is loaded;
    returns False when it was loaded already (by the application, before the tool)."""
    os.environ["ORT_DISABLE_TELEMETRY"] = "1"
    return "onnxruntime" not in sys.modules


def network_forbidden() -> bool:
    """True once :func:`forbid_network` has run in this process."""
    return _closed
