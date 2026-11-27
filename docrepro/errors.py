"""The errors docrepro reports, besides those of its steps: a fixed kind, the details its
wording needs, and that wording in English and German.

The kinds every tool has (a file missing, a configuration broken, the network refused …)
and the mechanism are doccor's (:mod:`doccor.errors`); a step's own failures come as that
step's errors (optdoc's, ocrdoc's) and keep their kinds.  No message quotes the content
or the path of a document.
"""

from __future__ import annotations

from doccor import errors as _core
from doccor.errors import LANGUAGES, DocError, describe_error

_OWN: dict[str, dict[str, str]] = {
    "step-missing": {
        "en": "The step {step} is not installed; this document was made with it.",
        "de": "Der Schritt {step} ist nicht installiert; dieses Dokument wurde damit gemacht.",
    },
    "step-needs": {
        "en": "The step {step} needs the step {needs}, which is switched off or not installed.",
        "de": "Der Schritt {step} braucht den Schritt {needs}, der ausgeschaltet oder nicht "
              "installiert ist.",
    },
    "several-originals": {
        "en": "Several files are one document only where typdoc binds them into one PDF "
              "(pictures, typdoc in use); here they are several. {tool} run takes them one by "
              "one; the window and a chain document work on one document.",
        "de": "Mehrere Dateien sind nur ein Dokument, wo typdoc sie zu einem PDF bindet (Bilder, "
              "typdoc in Gebrauch); hier sind es mehrere. {tool} run nimmt sie einzeln; das "
              "Fenster und ein Kettendokument arbeiten auf einem Dokument.",
    },
    "same-stem": {
        "en": "Two of the files have the same name before their ending; their results would "
              "overwrite each other. Rename one, or take them one by one.",
        "de": "Zwei der Dateien heißen vor ihrer Endung gleich; ihre Ergebnisse würden einander "
              "überschreiben. Eine umbenennen oder sie einzeln nehmen.",
    },
    "no-steps": {
        "en": "No step is switched on: there is nothing to do.",
        "de": "Kein Schritt ist eingeschaltet: es gibt nichts zu tun.",
    },
}

_core.register(_OWN)
KINDS = _core.KINDS  # every kind docrepro may report, the common ones with its own
__all__ = ["KINDS", "LANGUAGES", "DocError", "DocreproError", "describe_error"]


class DocreproError(DocError):
    """An error docrepro can word for a person: its kind (a key of :data:`KINDS`) and the
    details the wording needs."""

    tool = "docrepro"
