"""Where the pages of a file came from: a picture is itself, page by page; a page of a PDF
is the file it names as its source, else the one JPEG it is, else the PDF and the page's
number.  Two letters of the same size are never the same; a picture and a PDF that holds it
as medRDS 9.5 binds it are."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pymupdf

from doccor import origins


def _jpeg(width: int = 300, height: int = 400, shade: int = 30) -> bytes:
    """An invented JPEG: white with a dark bar along its top."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (width, height), (255, 255, 255))
    ImageDraw.Draw(image).rectangle((0, 0, width - 1, height // 10), fill=(shade, shade, shade))
    out = io.BytesIO()
    image.save(out, "JPEG", quality=90)
    return out.getvalue()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _page_of_jpeg(doc: pymupdf.Document, jpeg: bytes) -> pymupdf.Page:
    """A page that is the JPEG and nothing else, its long side 842 points."""
    page = doc.new_page(width=631.5, height=842)
    page.insert_image(page.rect, stream=jpeg)
    return page


def _with_source(doc: pymupdf.Document, page: pymupdf.Page, data: bytes, name: str) -> int:
    """Associate a file with a page as medRDS 9.5 does (``/AF``, ``/AFRelationship
    /Source``); the number of its file specification."""
    stream = doc.get_new_xref()
    doc.update_object(stream, "<< /Type /EmbeddedFile >>")
    doc.update_stream(stream, data, new=True)
    spec = doc.get_new_xref()
    doc.update_object(spec, f"<< /Type /Filespec /F ({name}) /UF ({name}) "
                            f"/EF << /F {stream} 0 R >> /AFRelationship /Source >>")
    doc.xref_set_key(page.xref, "AF", f"[{spec} 0 R]")
    return spec


def test_a_picture_is_itself_page_by_page(tmp_path: Path) -> None:
    from PIL import Image

    photo = tmp_path / "foto.jpg"
    photo.write_bytes(_jpeg())
    assert origins.of(photo) == [origins.origin(_sha(photo.read_bytes()), 0)]
    tiff = tmp_path / "scan.tiff"
    first, second = Image.new("RGB", (60, 80), "white"), Image.new("RGB", (60, 80), "grey")
    first.save(tiff, save_all=True, append_images=[second])
    digest = _sha(tiff.read_bytes())
    assert origins.of(tiff) == [origins.origin(digest, 0), origins.origin(digest, 1)]


def test_a_page_that_is_one_jpeg_is_that_jpeg(tmp_path: Path) -> None:
    jpeg = _jpeg()
    doc = pymupdf.open()
    _page_of_jpeg(doc, jpeg)
    doc.save(tmp_path / "bound.pdf")
    doc.close()
    photo = tmp_path / "foto.jpg"
    photo.write_bytes(jpeg)
    assert origins.of(tmp_path / "bound.pdf") == origins.of(photo)


def test_a_page_names_its_source(tmp_path: Path) -> None:
    """Pages of a file associated with them: the file, counted in the order the PDF shows
    its pages; the JPEG a page shows of it does not count."""
    tiff_bytes = b"II*\x00 an invented TIFF"
    png_bytes = b"\x89PNG an invented PNG"
    doc = pymupdf.open()
    one = _page_of_jpeg(doc, _jpeg(shade=10))
    spec = _with_source(doc, one, tiff_bytes, "scan.tiff")
    two = _page_of_jpeg(doc, _jpeg(shade=60))
    doc.xref_set_key(two.xref, "AF", f"[{spec} 0 R]")  # the TIFF's second picture
    three = _page_of_jpeg(doc, _jpeg(shade=90))
    _with_source(doc, three, png_bytes, "bild.png")
    doc.save(tmp_path / "bound.pdf")
    doc.close()
    assert origins.of(tmp_path / "bound.pdf") == [
        origins.origin(_sha(tiff_bytes), 0), origins.origin(_sha(tiff_bytes), 1),
        origins.origin(_sha(png_bytes), 0)]


def test_any_other_page_is_the_pdf_and_its_number(tmp_path: Path) -> None:
    """A page with text, a page with two pictures, a JPEG that does not cover its page, a
    file associated with another relationship: the PDF itself.  Two letters of the same
    size are two originals."""
    letters = []
    for who in ("Erika Beispiel", "Max Muster"):
        doc = pymupdf.open()
        doc.new_page(width=595, height=842).insert_text((72, 100), f"Brief an {who}")
        small = doc.new_page(width=595, height=842)
        small.insert_image(pymupdf.Rect(0, 0, 200, 300), stream=_jpeg())
        two = doc.new_page(width=595, height=842)
        two.insert_image(pymupdf.Rect(0, 0, 595, 421), stream=_jpeg(shade=10))
        two.insert_image(pymupdf.Rect(0, 421, 595, 842), stream=_jpeg(shade=90))
        other = _page_of_jpeg(doc, _jpeg(shade=50))
        _with_source(doc, other, b"a supplement", "beilage.txt")
        spec = origins._references(doc.xref_get_key(other.xref, "AF"))[0]
        doc.xref_set_key(spec, "AFRelationship", "/Supplement")
        path = tmp_path / f"{who.split()[0]}.pdf"
        doc.save(path)
        doc.close()
        whole = _sha(path.read_bytes())
        found = origins.of(path)
        assert found[:3] == [origins.origin(whole, n) for n in range(3)]
        assert found[3] == origins.origin(_sha(_jpeg(shade=50)), 0)  # a JPEG, the supplement aside
        letters.append(found)
    assert not any(origins.same(a, b) for a, b in zip(letters[0][:3], letters[1][:3], strict=True))


def test_the_document_already_open_gives_the_same(tmp_path: Path) -> None:
    doc = pymupdf.open()
    _page_of_jpeg(doc, _jpeg())
    doc.save(tmp_path / "bound.pdf")
    doc.close()
    with pymupdf.open(tmp_path / "bound.pdf") as opened:
        assert origins.of(tmp_path / "bound.pdf", opened) == origins.of(tmp_path / "bound.pdf")


def test_the_same_origin() -> None:
    a = origins.origin("ab" * 32, 0)
    assert origins.same(a, dict(a)) and not origins.same(a, origins.origin("ab" * 32, 1))
    assert not origins.same(a, None) and not origins.same({"sha256": None, "index": 0}, a)
