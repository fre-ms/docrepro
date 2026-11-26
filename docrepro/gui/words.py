"""The words docrepro's window shows besides those of its steps' panels, in English and
German, registered with doccor's words (:mod:`doccor.gui.words`).  The panels bring their
own (optdoc's, ocrdoc's); a key here is docrepro's alone or means the same as theirs."""

from __future__ import annotations

from doccor.gui import words as _words
from doccor.gui.words import LANGUAGES, Words, system_language

WORDS: dict[str, tuple[str, str]] = {  # key: (English, German)
    "tab_prepare": ("1 Prepare", "1 Aufbereiten"),
    "tab_filters_2": ("2 Filters for OCR", "2 Filter für die Texterkennung"),
    "tab_regions_3": ("3 Areas", "3 Bereiche"),
    "tab_text_4": ("4 Check the text", "4 Text prüfen"),
    "tab_tagdoc": ("Describe", "Beschreiben"),
    "opening_step": ("The step opens on the result of the one before …",
                     "Der Schritt öffnet sich auf dem Ergebnis des vorigen …"),
    "describing": ("ocrdoc writes its result for the description (reading the pages not read "
                   "yet) …", "ocrdoc schreibt sein Ergebnis für die Beschreibung (und liest "
                   "die Seiten, die noch nicht gelesen sind) …"),
    "preparing": ("optdoc prepares the pages for the next steps …",
                  "optdoc bereitet die Seiten für die nächsten Schritte auf …"),
    "dropped_pages": ("Page(s) {pages} moved in optdoc (turned, unwarped or straightened "
                      "otherwise): what was decided there in the later steps went.",
                      "Seite(n) {pages} haben sich in optdoc verschoben (anders gedreht, "
                      "entzerrt oder begradigt): was dort in den späteren Schritten entschieden "
                      "war, ist verworfen."),
    "kept_decisions": ("optdoc changed the pages; what was decided in the later steps stays "
                       "where a page did not move.",
                       "optdoc hat die Seiten geändert; was in den späteren Schritten "
                       "entschieden war, bleibt, wo sich eine Seite nicht verschoben hat."),
}

_words.register(WORDS)
__all__ = ["LANGUAGES", "WORDS", "Words", "system_language"]
