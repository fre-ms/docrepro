# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification: docrepro as one executable file with every step inside, to
ship beside an application (a Tauri sidecar, for a records app).

Build it with ``packaging/build.py``, which names the file after the target platform and
tries it out.  Everything travels inside: Python; optdoc, ocrdoc and tagdoc with doccor;
PyMuPDF, OpenCV, ONNX Runtime, RapidOCR with its models, pillow-heif, Camelot with pandas
and pdfium for the tables, zxing-cpp for the barcodes, PySide6 (Qt) for the windows.
Nothing is downloaded at run time.

Environment: ``DOCREPRO_BINARY_NAME`` (the file's name), ``DOCREPRO_CODESIGN_IDENTITY`` (a
Developer ID for macOS; without it the build is signed ad hoc), ``DOCREPRO_ONEDIR`` (a
folder of that name, with the program ``docrepro`` in it, instead of one file).
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

root = Path(SPECPATH).parent  # noqa: F821 (given by PyInstaller)
identity = os.environ.get("DOCREPRO_CODESIGN_IDENTITY") or None
TOOLS = ("docrepro", "doccor", "optdoc", "ocrdoc", "tagdoc")

datas, binaries, hiddenimports = [], [], []
# rapidocr: its models and settings; camelot and playa: their parsers; pypdfium2: pdfium
for package in ("rapidocr", "onnxruntime", "pymupdf", "camelot", "playa", "pypdfium2",
                "pypdfium2_raw"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h
binaries += collect_dynamic_libs("pillow_heif")
for tool in TOOLS:
    hiddenimports += collect_submodules(tool)  # a step's command line is imported by name
    datas += collect_data_files(tool)  # tagdoc's copy of the standard's schema
# a step joins docrepro through its entry point (docrepro.steps), which is read from the
# metadata of its distribution
datas += copy_metadata("tagdoc")
# packages compiled with mypyc (playa) import a helper module with a hashed name that
# PyInstaller does not see
for path in sys.path:
    if Path(path).is_dir():
        hiddenimports += sorted({f.name.split(".")[0] for f in Path(path).glob("*__mypyc*")})
hiddenimports += ["pillow_heif", "PIL.Image", "PIL.ImageFilter", "PIL.ImageOps", "cv2",
                  "zxingcpp", "shapely", "pyclipper", "omegaconf", "colorlog", "yaml"]
# RapidOCR's other inference engines and what the tools never use
excludes = ["torch", "paddle", "openvino", "tensorrt", "MNN", "tkinter", "matplotlib",
            "IPython", "jupyter", "notebook", "pytest", "PyQt5", "PyQt6",
            # Qt modules the windows do not use
            "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtSql",
            "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
            "PySide6.QtDBus", "PySide6.QtConcurrent", "PySide6.QtPrintSupport",
            "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtUiTools", "PySide6.QtDesigner",
            "PySide6.QtHelp"]

a = Analysis(  # noqa: F821
    [str(root / "packaging" / "start.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[str(root / "packaging" / "rth_offline.py")],
    excludes=excludes,
    noarchive=False,
)
# ONNX Runtime's C library is for other languages; the Python module carries its own copy
# (it neither links nor loads the library), and the file is 35 MB unpacked at every start.
# collect_all and the library's hook both bring it, as binary and as data.
a.binaries = [e for e in a.binaries if not Path(e[0]).name.startswith("libonnxruntime")]
a.datas = [e for e in a.datas if not Path(e[0]).name.startswith("libonnxruntime")]
pyz = PYZ(a.pure)  # noqa: F821
name = os.environ.get("DOCREPRO_BINARY_NAME", "docrepro")
signing = {"codesign_identity": identity,
           "entitlements_file": str(root / "packaging" / "entitlements.plist") if identity
           else None}
if os.environ.get("DOCREPRO_ONEDIR"):  # a folder: nothing unpacked at start, see docs/sidecar.md
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="docrepro", debug=False,  # noqa: F821
              strip=False, upx=False, console=True, **signing)
    COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=name)  # noqa: F821
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name=name, debug=False,  # noqa: F821
              strip=False, upx=False, console=True, runtime_tmpdir=None, **signing)
