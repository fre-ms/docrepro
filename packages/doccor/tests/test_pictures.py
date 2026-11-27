"""Pictures as the tools look at them: by their names; every picture of a file upright, its
size in its own pixels read without decoding it; and as a page whose long side is that of
A4, whatever the type."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from doccor import pictures
from doccor.errors import DocError

ENDINGS = ("jpg", "png", "tiff", "webp", "heic", "bmp", "gif", "pnm")


def _drawing(width: int = 300, height: int = 400) -> object:
    """An invented picture that shows which way is up: white, a dark bar along its top
    edge and a red square in its top left corner."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, height // 10), fill=(30, 30, 30))
    draw.rectangle((0, 0, width // 5, height // 5), fill=(220, 0, 0))
    return image


def _saved(image: object, path: Path, **options: object) -> Path:
    import pillow_heif

    pillow_heif.register_heif_opener()
    image.save(path, **options)  # type: ignore[attr-defined]
    return path


def _red_corner(picture: object) -> bool:
    """True when the top left corner of a picture is the drawing's red square."""
    r, g, b = picture.getpixel((8, 8))  # type: ignore[attr-defined]
    return r > 150 and g < 90 and b < 90


def test_pictures_by_their_names() -> None:
    for name in ("foto.JPG", "scan.tiff", "bild.heic", "seite.webp", "raster.pnm"):
        assert pictures.is_picture(name), name
    for name in ("brief.pdf", "brief.docx", "foto", "foto.jpg.txt"):
        assert not pictures.is_picture(name), name
    assert set(pictures.JPEG) | set(pictures.HEIC) < set(pictures.SUFFIXES)
    assert pictures.heic_available() is True


@pytest.mark.parametrize("ending", ENDINGS)
def test_a_picture_as_a_page(tmp_path: Path, ending: str) -> None:
    """One page for the picture, in its proportions, the long side that of A4; the page
    shows the picture, and the size named is the picture's own."""
    path = _saved(_drawing(), tmp_path / f"bild.{ending}")
    assert pictures.count(path) == 1 and pictures.sizes(path) == [(300, 400)]
    doc = pictures.pages(path)
    try:
        assert len(doc) == 1
        rect = doc[0].rect
        assert rect.height == pytest.approx(pictures.LONG_SIDE, abs=0.01)
        assert rect.width == pytest.approx(pictures.LONG_SIDE * 300 / 400, abs=0.02)
        pix = doc[0].get_pixmap(dpi=36)
        assert pix.pixel(8, 8)[0] > 150 and pix.pixel(8, 8)[1] < 100  # the red square
        assert min(pix.pixel(pix.width - 8, pix.height - 8)[:3]) > 200  # white
    finally:
        doc.close()
    picture = pictures.frame(path)
    assert picture.mode == "RGB" and picture.size == (300, 400) and _red_corner(picture)


@pytest.mark.parametrize("ending", ("jpg", "png", "tiff", "webp"))
def test_a_picture_stored_on_its_side_stands_upright(tmp_path: Path, ending: str) -> None:
    """A phone stores the pixels as its sensor lay and says how to turn them: the page,
    the pixels and the size named are the upright picture's.  (Pillow's TIFF reader turns
    the picture itself; the size it names is the upright one already.)"""
    from PIL import Image

    exif = Image.Exif()
    exif[0x0112] = 6  # the pixels lie a quarter turn anticlockwise
    stored = _drawing().rotate(90, expand=True)  # type: ignore[attr-defined]
    assert stored.size == (400, 300)
    path = _saved(stored, tmp_path / f"foto.{ending}", exif=exif)
    assert pictures.sizes(path) == [(300, 400)]
    picture = pictures.frame(path)
    assert picture.size == (300, 400) and _red_corner(picture)
    doc = pictures.pages(path)
    try:
        assert doc[0].rect.height > doc[0].rect.width  # upright: a portrait
        pix = doc[0].get_pixmap(dpi=36)
        assert pix.pixel(8, 8)[0] > 150 and pix.pixel(8, 8)[1] < 100
    finally:
        doc.close()


@pytest.mark.parametrize("ending", ENDINGS)
@pytest.mark.parametrize("orientation", (1, 3, 6, 8))
def test_the_size_named_is_the_size_of_the_pixels(tmp_path: Path, ending: str,
                                                  orientation: int) -> None:
    """Whatever the type and whatever it says of its orientation: the sizes read without
    decoding are those of the pixels :func:`frame` gives, and of the pages."""
    from PIL import Image

    exif = Image.Exif()
    exif[0x0112] = orientation
    options = {"exif": exif} if ending in ("jpg", "png", "tiff", "webp", "heic") else {}
    path = _saved(_drawing(240, 400), tmp_path / f"bild.{ending}", **options)
    named = pictures.sizes(path)
    assert named == [picture.size for picture in pictures.frames(path)]
    doc = pictures.pages(path)
    try:
        width, height = named[0]
        assert (doc[0].rect.width > doc[0].rect.height) == (width > height)
        assert doc[0].rect.width / doc[0].rect.height == pytest.approx(width / height, rel=0.01)
    finally:
        doc.close()


def test_a_jpeg_is_one_picture_whatever_else_it_holds(tmp_path: Path) -> None:
    """A phone's JPEG may carry a second image beside the photo (a gain map for bright
    screens; Pillow then counts two): for the tools it is one picture and one page."""
    from PIL import Image

    path = tmp_path / "foto.jpg"
    _drawing().save(path, format="MPO", save_all=True,  # type: ignore[attr-defined]
                    append_images=[Image.new("RGB", (150, 200), (128, 128, 128))])
    with Image.open(path) as image:
        assert image.format == "MPO" and image.n_frames == 2
    assert pictures.count(path) == 1 and pictures.sizes(path) == [(300, 400)]
    assert len(pictures.frames(path)) == 1 and _red_corner(pictures.frame(path))
    doc = pictures.pages(path)
    try:
        assert len(doc) == 1
    finally:
        doc.close()


def test_every_picture_of_a_file_is_a_page(tmp_path: Path) -> None:
    path = tmp_path / "zwei.tiff"
    _drawing().save(path, save_all=True,  # type: ignore[attr-defined]
                    append_images=[_drawing(500, 250)], compression="tiff_lzw")
    assert pictures.count(path) == 2 and pictures.sizes(path) == [(300, 400), (500, 250)]
    assert [p.size for p in pictures.frames(path)] == [(300, 400), (500, 250)]
    assert pictures.frame(path, 1).size == (500, 250)
    doc = pictures.pages(path)
    try:
        assert len(doc) == 2
        assert doc[0].rect.height == pytest.approx(842, abs=0.01)
        assert doc[1].rect.width == pytest.approx(842, abs=0.01)  # a landscape
        assert doc[1].rect.height == pytest.approx(421, abs=0.02)
    finally:
        doc.close()


def test_what_is_transparent_stands_on_white(tmp_path: Path) -> None:
    from PIL import Image

    clear = Image.new("RGBA", (120, 160), (0, 0, 0, 0))
    clear.paste((0, 0, 200, 255), (0, 0, 60, 80))
    path = _saved(clear, tmp_path / "klar.png")
    picture = pictures.frame(path)
    assert picture.getpixel((100, 140)) == (255, 255, 255)
    assert picture.getpixel((10, 10)) == (0, 0, 200)
    doc = pictures.pages(path)
    try:
        pix = doc[0].get_pixmap(dpi=36)
        assert min(pix.pixel(pix.width - 4, pix.height - 4)[:3]) > 240
    finally:
        doc.close()


def test_the_page_is_independent_of_the_file(tmp_path: Path) -> None:
    """The pages hold the picture: the file may go."""
    path = _saved(_drawing(), tmp_path / "bild.jpg")
    doc = pictures.pages(path)
    path.unlink()
    try:
        assert doc[0].get_pixmap(dpi=36).pixel(8, 8)[0] > 150
        assert isinstance(doc, pymupdf.Document)
    finally:
        doc.close()


def test_without_the_heic_library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A HEIC picture where pillow-heif is not installed is told apart from a broken one;
    every other picture opens all the same."""
    import sys

    heic = _saved(_drawing(), tmp_path / "bild.heic")
    other = _saved(_drawing(), tmp_path / "bild.png")
    monkeypatch.setitem(sys.modules, "pillow_heif", None)  # importing it now fails
    for work in (pictures.pages, pictures.sizes, pictures.count, pictures.frame):
        with pytest.raises(pictures.NoHeic):
            work(heic)
    assert pictures.sizes(other) == [(300, 400)]


def test_what_is_no_picture(tmp_path: Path) -> None:
    for name in ("kaputt.png", "kaputt.jpg", "kaputt.tiff", "kaputt.webp"):
        broken = tmp_path / name
        broken.write_bytes(b"not a picture at all")
        for work in (pictures.pages, pictures.sizes, pictures.frame):
            with pytest.raises(Exception) as caught:  # noqa: B017, PT011
                work(broken)
            assert not isinstance(caught.value, pictures.NoHeic), (name, work.__name__)


def test_the_kinds_every_tool_has() -> None:
    """A type a tool cannot open, a file that cannot be read and a PDF behind a password
    are worded once, naming the tool."""
    assert DocError("unsupported", tool="sometool", suffix=".docx").message("en") == \
        "sometool cannot open files of type .docx."
    assert DocError("unsupported", tool="sometool", suffix=".docx").message("de") == \
        "Dateien vom Typ .docx kann sometool nicht öffnen."
    assert "cannot be read" in DocError("unreadable").message("en")
    assert "Kennwort" in DocError("encrypted").message("de")
