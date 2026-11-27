"""The metadata as medRDS writes them: the same packet as the reference library, people
named as 7.2 says, copies of cards that hold only what they may, a PDF's own metadata
beyond the standard kept."""

from __future__ import annotations

import pytest

from tagdoc import medrds
from tests.conftest import CARD

META = {"title": "Laborbefund <Kalium> & mehr", "kind": "lab",
        "creator": ["Dr. Erika Beispiel <mailto:beispiel@praxis.example>"],
        "description": "Blutbild", "subject": ["Kalium", "Natrium"], "language": ["de"],
        "source": "Ihr Zeichen 2026/1234", "creatorTool": "docrepro 0.1.0",
        "date": "2026-03-12T09:30:00+01:00", "typeCode": ["http://loinc.org|11502-2"],
        "institution": ["Labor Muster GmbH <mailto:befunde@labor.example> "
                        "<urn:uuid:4d2c9b1e-7a3f-4c5d-9e8f-0a1b2c3d4e5f>"],
        "authenticator": "Dr. Erika Beispiel <mailto:beispiel@praxis.example>",
        "confidentiality": "R", "cards": [medrds.card_copy(CARD)]}


def test_people_and_cards() -> None:
    name, ids = medrds.parse_person("Labor Muster GmbH <mailto:a@b.example> <tel:+49-1>")
    assert name == "Labor Muster GmbH" and ids == ["mailto:a@b.example", "tel:+49-1"]
    assert medrds.format_person(" Dr. <X> ", ["mailto:x@y.example"]) == "Dr. X <mailto:x@y.example>"
    copy = medrds.card_copy(CARD)
    names = [n for n, _v in medrds.properties_of(copy)]
    assert "PHOTO" not in names and "X-SECDAV-SEALED" not in names and "X-MEDDAV-BSNR" in names
    assert "\r" not in copy and medrds.card_file(copy).count("\r\n") == len(names)
    uid = medrds.uid_of_card(copy)
    assert uid == "4d2c9b1e-7a3f-4c5d-9e8f-0a1b2c3d4e5f"
    assert medrds.reference(copy) == f"urn:uuid:{uid}"
    assert medrds.card_of(META["institution"][0]) == uid
    assert medrds.card_problems(META) == []
    unused = {**META, "institution": ["Labor Muster GmbH"]}
    assert [p["code"] for p in medrds.card_problems(unused)] == ["CARD_UNUSED"]
    missing = {**META, "cards": []}
    assert [p["code"] for p in medrds.card_problems(missing)] == ["CARD_MISSING"]
    assert [p["code"] for p in medrds.card_problems({**META, "cards": [CARD]})] == ["CARD_CONTENT"]
    apple = "BEGIN:VCARD\nUID:ABC123:ABPerson\nFN:A\nEND:VCARD\n"
    assert medrds.reference(apple) == "urn:x-contact-uid:ABC123:ABPerson"


def test_dates_and_the_information_dictionary() -> None:
    assert medrds.pdf_date("2026-03-12") == "D:20260312"
    assert medrds.pdf_date("2026-03-14T08:15:00+01:00") == "D:20260314081500+01'00'"
    assert medrds.pdf_date("12.03.2026") is None
    info = medrds.info_of(META)
    assert info == {"title": META["title"], "author": "Dr. Erika Beispiel", "subject": "Blutbild",
                    "creator": "docrepro 0.1.0", "creationDate": "D:20260312093000+01'00'"}


def test_what_a_packet_held_beyond_the_standard_stays() -> None:
    existing = medrds.serialise_xmp({"title": "alt", "kind": "note"}).replace(
        "  </rdf:Description>",
        '   <pdfaid:part xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">2</pdfaid:part>\n'
        "  </rdf:Description>")
    merged = medrds.merge_xmp(existing, {"title": "neu", "kind": "lab"})
    assert "neu" in merged and "alt" not in merged and ">note<" not in merged
    assert "http://www.aiim.org/pdfa/ns/id/" in merged and ">2</" in merged
    assert medrds.merge_xmp("kein XML", {"title": "neu"}) == medrds.serialise_xmp({"title": "neu"})


@pytest.mark.parametrize("kind", ["lab", "letter", "consent"])
def test_kinds_come_from_the_schema(kind: str) -> None:
    assert set(medrds.kinds()[kind]) == {"en", "de"}
