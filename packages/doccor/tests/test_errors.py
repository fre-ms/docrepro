"""Kinds of error: worded in English and German, naming the tool whose they are; a tool
adds its own."""

from __future__ import annotations

import pytest

from doccor import errors
from doccor.errors import DocError, describe_error


class ToolError(DocError):
    tool = "sometool"


def test_messages_name_the_tool() -> None:
    """A message that names the tool names the tool the error belongs to."""
    assert ToolError("usage").message("en") == "The command line is not valid; see sometool --help."
    assert DocError("internal", tool="other", error="KeyError").message("de") == \
        "other ist unerwartet gescheitert (KeyError)."
    assert str(ToolError("missing")) == "The file or folder does not exist."


def test_bad_configuration_says_why() -> None:
    """A broken configuration says what is wrong with it, in both languages."""
    error = ToolError("bad-config", reason="format")
    assert error.message("en").endswith("it is no configuration of this version of sometool.")
    assert "keine Konfiguration dieser Fassung von sometool" in error.message("de")
    assert describe_error(error, "de") == error.message("de")
    assert describe_error(ValueError("plain"), "de") == "plain"


def test_a_tool_registers_its_kinds() -> None:
    """A tool's own kinds join the common ones; an unknown kind is a programming error,
    and one kind cannot have two wordings."""
    paper = {"en": "Unknown paper: {name}.", "de": "Unbekanntes Papier: {name}."}
    errors.register({"paper-x": paper})
    assert ToolError("paper-x", name="b9").message("de") == "Unbekanntes Papier: b9."
    errors.register({"paper-x": paper})
    with pytest.raises(ValueError):
        errors.register({"paper-x": {"en": "Other.", "de": "Anders."}})
    with pytest.raises(ValueError):
        errors.register({"half": {"en": "Only English."}})
    with pytest.raises(KeyError):
        DocError("no-such-kind")
