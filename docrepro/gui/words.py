"""The words docrepro's window shows besides those of its steps' panels, in English and
German, registered with doccor's words (:mod:`doccor.gui.words`).  The panels bring their
own (optdoc's, ocrdoc's); a key here is docrepro's alone or means the same as theirs."""

from __future__ import annotations

from doccor.gui import words as _words
from doccor.gui.words import LANGUAGES, Words, system_language

WORDS: dict[str, tuple[str, str]] = {  # key: (English, German)
    # the tabs of the steps whose adapters are docrepro's; the window numbers them
    "tab_optdoc": ("Prepare", "Aufbereiten"),
    "tab_ocrdoc_filters": ("Filters for OCR", "Filter für die Texterkennung"),
    "tab_ocrdoc_regions": ("Areas", "Bereiche"),
    "tab_ocrdoc_text": ("Check the text", "Text prüfen"),
    # the steps on the left: which are in use, and what became of each
    "chain_steps": ("Steps in use", "Schritte in Gebrauch"),
    "chain_typdoc": ("bind into a PDF", "zum PDF binden"),
    "chain_optdoc": ("prepare", "aufbereiten"),
    "chain_ocrdoc": ("recognise", "erkennen"),
    "chain_tagdoc": ("describe", "beschreiben"),
    "chain_nothing": ("nothing to do: a PDF already", "nichts zu tun: schon ein PDF"),
    "chain_off": ("off", "aus"),
    "chain_auto": ("in use, as suggested", "in Gebrauch, wie vorgeschlagen"),
    "chain_person": ("in use, changed by hand", "in Gebrauch, von Hand geändert"),
    "chain_stale": ("in use, to be made anew", "in Gebrauch, neu zu machen"),
    "chain_missing": ("not installed", "nicht installiert"),
    "chain_several": ("{count} pictures: one document only bound into one",
                      "{count} Bilder: nur gebunden ein Dokument"),
    "chain_off_tip": ("{step} is switched off (see the steps on the left).",
                      "{step} ist ausgeschaltet (siehe die Schritte links)."),
    "chain_none": ("No step is switched on: there is nothing to do.",
                   "Kein Schritt ist eingeschaltet: es gibt nichts zu tun."),
    # what became of a person's decisions in a step when a step before it changed
    "chain_anew": ("{step} is handed pages now that are not those its work was made on: it "
                   "starts anew, and what was decided in it went.",
                   "{step} bekommt jetzt Seiten, die nicht die sind, auf denen seine Arbeit "
                   "gemacht war: es beginnt neu, und was darin entschieden war, ist verworfen."),
    "dropped_pages": ("{step}: page(s) {pages} lie otherwise now (a step before turned, "
                      "unwarped or straightened them otherwise, or was switched): what was "
                      "decided there went.",
                      "{step}: Seite(n) {pages} liegen jetzt anders (ein Schritt davor hat sie "
                      "anders gedreht, entzerrt oder begradigt, oder wurde umgeschaltet): was "
                      "dort entschieden war, ist verworfen."),
    "kept_decisions": ("{step}: a step before it changed; what was decided in it stays, every "
                       "page lying as it lay.",
                       "{step}: ein Schritt davor hat sich geändert; was darin entschieden war, "
                       "bleibt, jede Seite liegt, wie sie lag."),
    "opening_step": ("The step opens on the result of the one before …",
                     "Der Schritt öffnet sich auf dem Ergebnis des vorigen …"),
    "bringing": ("{step} is brought up to what the steps before it give now …",
                 "{step} wird auf das gebracht, was die Schritte davor jetzt geben …"),
}

_words.register(WORDS)
__all__ = ["LANGUAGES", "WORDS", "Words", "system_language"]
