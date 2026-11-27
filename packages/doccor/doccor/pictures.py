"""Pictures as the tools look at them: which files are pictures, every picture of a file
upright, its size in its own pixels, and a picture as a page.

docrepro forces no file type: a picture goes through the steps as a picture.  To work on
one, a tool looks at it as pages: one for each picture in the file (a TIFF may hold
several), upright as its EXIF orientation says, the long side that of A4 (842 points).
That is the page the standard medRDS binds a picture into (9.5, what typdoc does).  So a
box in points means the same in every tool, whether the tool is handed the picture itself
or typdoc's PDF of it; and where a tool speaks of a picture's own pixels, it means the
upright picture's (:func:`sizes`).

Pillow opens the pictures (it is imported when a picture is, not before), and pillow-heif
those of HEIC and HEIF; a tool that takes pictures depends on them.  Nothing here words an
error: a tool catches :class:`NoHeic` and whatever Pillow and MuPDF raise (their messages
may name the file), and says it in its own way.
"""

from __future__ import annotations

import io
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pymupdf

SUFFIXES = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".heif", ".webp", ".bmp", ".gif",
            ".pnm")
JPEG = (".jpg", ".jpeg")
HEIC = (".heic", ".heif")
LONG_SIDE = 842.0  # points: the long side of A4, as medRDS 9.5 binds a picture
_ORIENTATION = 0x0112
_ON_ITS_SIDE = (5, 6, 7, 8)  # the EXIF orientations that swap width and height
# the readers of Pillow that name a picture's size as it is stored and leave the turning
# to whoever looks at it (HEIF: libheif has turned it, and the orientation says upright)
_AS_STORED = ("JPEG", "MPO", "PNG", "WEBP", "GIF", "BMP", "PPM", "HEIF")


class NoHeic(Exception):
    """A HEIC or HEIF picture, and pillow-heif is not installed."""


def is_picture(path: str | Path) -> bool:
    """True for a file whose type is a picture's (by its name)."""
    return Path(path).suffix.lower() in SUFFIXES


def heic_available() -> bool:
    """True when HEIC and HEIF pictures can be opened (pillow-heif is installed)."""
    return find_spec("pillow_heif") is not None


def _image(path: Path) -> Any:
    """Pillow's Image module, able to open the file."""
    from PIL import Image

    if path.suffix.lower() in HEIC:
        try:
            import pillow_heif
        except ImportError as e:
            raise NoHeic from e
        pillow_heif.register_heif_opener()
    return Image


def opened(path: str | Path) -> Any:
    """The file as Pillow opens it (to be used in a ``with``); nothing is decoded yet.
    Raises :class:`NoHeic`, and what Pillow raises for a file that is no picture."""
    path = Path(path)
    return _image(path).open(path)


def _held(path: str | Path, image: Any) -> int:
    """How many pictures an opened file holds for the tools.  A JPEG is one picture,
    whatever else it carries: a phone's JPEG may hold a second image beside the photo (a
    gain map for bright screens), which is no page of a document."""
    if Path(path).suffix.lower() in JPEG:
        return 1
    return int(getattr(image, "n_frames", 1))


def count(path: str | Path) -> int:
    """How many pictures the file holds (a TIFF may hold several; a JPEG is one)."""
    with opened(path) as image:
        return _held(path, image)


def _upright_size(image: Any) -> tuple[int, int]:
    """The size of the picture a Pillow image stands on once it is upright, without
    decoding it where the reader is known."""
    width, height = image.size
    if image.format == "TIFF":  # Pillow's TIFF reader turns the picture and names it so
        return width, height
    if image.format in _AS_STORED:
        if image.getexif().get(_ORIENTATION) in _ON_ITS_SIDE:
            return height, width
        return width, height
    upright: tuple[int, int] = flat(image).size  # a reader not known here: by looking
    return upright


def sizes(path: str | Path) -> list[tuple[int, int]]:
    """Width and height in pixels of every picture in the file, upright (as
    :func:`flat` turns it); read from what the file says, without decoding it."""
    found = []
    with opened(path) as image:
        for n in range(_held(path, image)):
            image.seek(n)
            found.append(_upright_size(image))
    return found


def flat(image: Any) -> Any:
    """The picture a Pillow image stands on, as a tool looks at it: upright as its EXIF
    orientation says, what is transparent on white, in RGB."""
    from PIL import Image, ImageOps

    upright = ImageOps.exif_transpose(image)
    if upright.mode in ("RGBA", "LA", "PA") or "transparency" in upright.info:
        rgba = upright.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        upright = Image.alpha_composite(white, rgba)
    return upright.convert("RGB")


def frame(path: str | Path, n: int = 0) -> Any:
    """Picture ``n`` of the file (from 0), as :func:`flat` gives it: the pixels as they
    came, not a rendering of them."""
    with opened(path) as image:
        image.seek(n)
        return flat(image)


def frames(path: str | Path) -> list[Any]:
    """Every picture of the file, as :func:`flat` gives it."""
    with opened(path) as image:
        found = []
        for n in range(_held(path, image)):
            image.seek(n)
            found.append(flat(image))
        return found


def _add_pages(doc: pymupdf.Document, image: pymupdf.Document) -> None:
    """Add the pictures of an image document to ``doc`` as pages: each fills its page,
    whose long side is that of A4."""
    source = pymupdf.open("pdf", image.convert_to_pdf())
    try:
        for i, sheet in enumerate(source.pages()):
            scale = LONG_SIDE / max(sheet.rect.width, sheet.rect.height)
            page = doc.new_page(width=round(sheet.rect.width * scale, 2),
                                height=round(sheet.rect.height * scale, 2))
            page.show_pdf_page(page.rect, source, i)
    finally:
        source.close()


def pages(path: str | Path) -> pymupdf.Document:
    """The pictures of a file as pages to work on, one for each: upright, the long side
    that of A4.  A JPEG is looked at as it is (MuPDF shows it upright by its EXIF); any
    other picture is decoded by Pillow, so that the page shows the very pixels
    :func:`frame` gives.  Raises :class:`NoHeic`, and what Pillow and MuPDF raise for a
    file that is no picture."""
    path = Path(path)
    doc = pymupdf.open()
    try:
        if path.suffix.lower() in JPEG:
            image = pymupdf.open(path)
            try:
                _add_pages(doc, image)
            finally:
                image.close()
        else:
            for picture in frames(path):
                buffer = io.BytesIO()
                picture.save(buffer, format="PNG", compress_level=1)
                between = pymupdf.open("png", buffer.getvalue())
                try:
                    _add_pages(doc, between)
                finally:
                    between.close()
        return pymupdf.open("pdf", doc.tobytes())  # independent of what it was made from
    finally:
        doc.close()


__all__ = ["HEIC", "JPEG", "LONG_SIDE", "SUFFIXES", "NoHeic", "count", "flat", "frame", "frames",
           "heic_available", "is_picture", "opened", "pages", "sizes"]
