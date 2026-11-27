"""Shared fixtures: invented pictures of an invented letter in the formats a phone and a
scanner write, and the reference library of medRDS where it is at hand (``MEDRDS``, else
``medRDS`` beside this repository)."""

from __future__ import annotations

import io
import os
import shutil
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

# medRDS beside this repository (tests -> package -> packages -> docrepro -> beside it)
MEDRDS = Path(os.environ.get("MEDRDS", Path(__file__).resolve().parents[4] / "medRDS"))
LINES = ["Neurologische Sprechstunde Beispiel", "Musterweg 1, 12345 Musterstadt", "",
         "Betr.: Erika Mustermann, geb. 12.08.1964", "",
         "Sehr geehrte Frau Kollegin,", "anbei der Befund vom 12.03.2026.",
         "Kalium 5,8 mmol/l (3,5 - 5,1)", "", "Mit freundlichen Grüßen"]
needs_medrds = pytest.mark.skipif(shutil.which("node") is None or not (MEDRDS / "lib").is_dir(),
                                  reason="needs Node and the reference library of medRDS")


def letter(width: int = 420, height: int = 594, mode: str = "RGB") -> Image.Image:
    """A page of an invented letter as a picture."""
    white = {"RGB": (255, 255, 255), "L": 255, "RGBA": (255, 255, 255, 0)}[mode]
    black = {"RGB": (20, 20, 20), "L": 20, "RGBA": (20, 20, 20, 255)}[mode]
    image = Image.new(mode, (width, height), white)
    draw = ImageDraw.Draw(image)
    for n, line in enumerate(LINES):
        draw.text((30, 40 + 22 * n), line, fill=black)
    draw.rectangle((30, 300, 200, 360), outline=black, width=2)
    return image


def encoded(image: Image.Image, format_: str, **options: object) -> bytes:
    """A picture's bytes in a format."""
    import pillow_heif

    pillow_heif.register_heif_opener()
    buffer = io.BytesIO()
    image.save(buffer, format=format_, **options)
    return buffer.getvalue()


def several(*images: Image.Image, form: str = "TIFF") -> bytes:
    """A file of several pictures: a TIFF of several pages, a HEIC of several images."""
    return encoded(images[0], form, save_all=True, append_images=list(images[1:]))


def with_orientation(jpeg: bytes, orientation: int) -> bytes:
    """A JPEG as a camera writes it that was held turned: EXIF orientation ``n``."""
    exif = (b"Exif\0\0" + b"MM\0\x2a\0\0\0\x08" + b"\0\x01"
            + b"\x01\x12\0\x03\0\0\0\x01\0" + bytes([orientation]) + b"\0\0" + b"\0\0\0\0")
    segment = b"\xff\xe1" + (len(exif) + 2).to_bytes(2, "big") + exif
    return jpeg[:2] + segment + jpeg[2:]


@pytest.fixture(scope="session")
def jpeg() -> bytes:
    return encoded(letter(), "JPEG", quality=85)


@pytest.fixture(scope="session")
def png() -> bytes:
    return encoded(letter(mode="RGBA"), "PNG")


@pytest.fixture(scope="session")
def heic() -> bytes:
    return encoded(letter(), "HEIF", quality=80)
