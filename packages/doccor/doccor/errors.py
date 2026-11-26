"""Kinds of error, with their wording in English and German.

A document may hold anything, and its file name may name a patient.  So no message
quotes the content or the path of a document, and the details are only what is safe to
show: a file name extension, the name of an engine or a paper size, a page number, the
name of an exception class.  A program that calls a tool decides by the kind; a person
reads :func:`describe_error` in the language of the interface.

The kinds every tool has are here; a tool registers its own (:func:`register`).  A
message may name the tool (``{tool}``): each tool's errors carry its name.
"""

from __future__ import annotations

from collections.abc import Mapping

LANGUAGES = ("en", "de")

KINDS: dict[str, dict[str, str]] = {
    "missing": {
        "en": "The file or folder does not exist.",
        "de": "Die Datei oder den Ordner gibt es nicht.",
    },
    "bad-config": {
        "en": "The configuration cannot be used: {reason}.",
        "de": "Die Konfiguration ist nicht verwendbar: {reason}.",
    },
    "config-mismatch": {
        "en": "The configuration belongs to another file.",
        "de": "Die Konfiguration gehört zu einer anderen Datei.",
    },
    "cancelled": {
        "en": "The work was cancelled; nothing was written.",
        "de": "Die Arbeit wurde abgebrochen; nichts wurde geschrieben.",
    },
    "no-gui": {
        "en": "The window needs PySide6, which comes with the extra 'gui'.",
        "de": "Das Fenster braucht PySide6, das mit dem Extra „gui“ kommt.",
    },
    "same-as-source": {
        "en": "The results would overwrite the document itself; choose another folder.",
        "de": "Die Ergebnisse würden das Dokument selbst überschreiben; bitte einen anderen "
              "Ordner wählen.",
    },
    "unwritable": {
        "en": "The results cannot be written to the folder given.",
        "de": "Die Ergebnisse lassen sich nicht in den angegebenen Ordner schreiben.",
    },
    "network": {
        "en": "Something tried to reach the network, which {tool} never does; it was stopped "
              "and nothing was sent.",
        "de": "Etwas wollte ins Netz, was {tool} nie tut; es wurde angehalten, nichts wurde "
              "gesendet.",
    },
    "unknown-model": {
        "en": "{tool} knows no model named {name}; see {tool} models list.",
        "de": "{tool} kennt kein Modell namens {name}; siehe {tool} models list.",
    },
    "model-unreachable": {
        "en": "The model {name} could not be fetched from its address.",
        "de": "Das Modell {name} ließ sich von seiner Adresse nicht abrufen.",
    },
    "model-checksum": {
        "en": "What came for the model {name} is not the file {tool} expects; nothing was kept.",
        "de": "Was für das Modell {name} kam, ist nicht die Datei, die {tool} erwartet; nichts "
              "wurde behalten.",
    },
    "usage": {
        "en": "The command line is not valid; see {tool} --help.",
        "de": "Die Kommandozeile ist nicht gültig; siehe {tool} --help.",
    },
    "internal": {
        "en": "{tool} failed unexpectedly ({error}).",
        "de": "{tool} ist unerwartet gescheitert ({error}).",
    },
}

# the reasons a configuration is refused, worded for "bad-config"
REASONS: dict[str, dict[str, str]] = {
    "json": {"en": "it is no JSON that can be read",
             "de": "sie ist kein lesbares JSON"},
    "format": {"en": "it is no configuration of this version of {tool}",
               "de": "sie ist keine Konfiguration dieser Fassung von {tool}"},
    "page": {"en": "it does not have one entry for each page of the document",
             "de": "sie hat nicht für jede Seite des Dokuments einen Eintrag"},
    "field": {"en": "a value is of the wrong kind",
              "de": "ein Wert ist von der falschen Art"},
}


def register(kinds: Mapping[str, Mapping[str, str]]) -> None:
    """Add a tool's own kinds, each worded in every language.  A kind registered twice
    must be worded the same both times (two tools may share one)."""
    for kind, wording in kinds.items():
        if set(wording) != set(LANGUAGES):
            raise ValueError(f"kind {kind} is not worded in {LANGUAGES}")
        if kind in KINDS and KINDS[kind] != dict(wording):
            raise ValueError(f"kind {kind} is registered with other words already")
        KINDS[kind] = dict(wording)


class DocError(Exception):
    """An error a tool can word for a person: its kind (a key of :data:`KINDS`), the
    details the wording needs, and the tool whose it is (``tool``, a class attribute of
    each tool's own error class, or given).  ``str(error)`` is the English message."""

    tool = "doccor"

    def __init__(self, kind: str, *, tool: str | None = None, **details: str | int) -> None:
        if kind not in KINDS:
            raise KeyError(f"unknown kind of error: {kind}")
        if tool is not None:
            self.tool = tool
        self.kind = kind
        self.details = details
        super().__init__(self.message("en"))

    def message(self, language: str = "en") -> str:
        """The message in ``language`` ("en" or "de"; any other means English)."""
        wording = KINDS[self.kind]
        details: dict[str, object] = dict(self.details)
        if self.kind == "bad-config":
            reason = REASONS.get(str(details.get("reason")), REASONS["json"])
            details["reason"] = reason.get(language, reason["en"]).format(tool=self.tool)
        return wording.get(language, wording["en"]).format(tool=self.tool, **details)


def describe_error(error: BaseException, language: str = "en") -> str:
    """The message of an error for a person, in English (``"en"``) or German (``"de"``);
    an error that is not a tool's keeps its own message."""
    if isinstance(error, DocError):
        return error.message(language)
    return str(error)
