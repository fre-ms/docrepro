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
    # the steps on the left: which are in use, and what became of each
    "chain_steps": ("Steps in use", "Schritte in Gebrauch"),
    "chain_typdoc": ("bind into a PDF", "zum PDF binden"),
    "chain_optdoc": ("prepare", "aufbereiten"),
    "chain_ocrdoc": ("recognise", "erkennen"),
    "chain_semdoc": ("understand", "verstehen"),
    "chain_tagdoc": ("describe", "beschreiben"),
    "chain_attdoc": ("sign", "signieren"),
    "chain_nothing": ("nothing to do: a PDF already", "nichts zu tun: schon ein PDF"),
    "chain_off": ("off", "aus"),
    "chain_auto": ("in use, as suggested", "in Gebrauch, wie vorgeschlagen"),
    "chain_person": ("in use, changed by hand", "in Gebrauch, von Hand geändert"),
    "chain_stale": ("in use, to be made anew", "in Gebrauch, neu zu machen"),
    "chain_missing": ("not installed", "nicht installiert"),
    "chain_rebound": ("optdoc is handed another file now (typdoc was switched), whose pages it "
                      "could not match: it starts anew, and what was decided in it went.",
                      "optdoc bekommt jetzt eine andere Datei (typdoc wurde umgeschaltet), deren "
                      "Seiten nicht passen: es beginnt neu, und was darin entschieden war, ist "
                      "verworfen."),
    "chain_needs": ("needs {needs}", "braucht {needs}"),
    "chain_several": ("{count} pictures: one document only bound into one",
                      "{count} Bilder: nur gebunden ein Dokument"),
    "chain_off_tip": ("{step} is switched off (see the steps on the left).",
                      "{step} ist ausgeschaltet (siehe die Schritte links)."),
    "chain_none": ("No step is switched on: there is nothing to do.",
                   "Kein Schritt ist eingeschaltet: es gibt nichts zu tun."),
    "chain_anew": ("ocrdoc reads another file now (a step before it was switched): it starts "
                   "anew, and what was decided in it went.",
                   "ocrdoc liest jetzt eine andere Datei (ein Schritt davor wurde umgeschaltet): "
                   "es beginnt neu, und was darin entschieden war, ist verworfen."),
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
