# docrepro as a standalone program

For an application that ships docrepro beside it rather than inside it (a records app, as a Tauri
sidecar): **one program with every step in it**, typdoc, optdoc, ocrdoc and tagdoc with doccor, Python,
PyMuPDF, OpenCV, ONNX Runtime, RapidOCR with its models, pillow-heif, Camelot with pandas and pdfium
for the tables, zxing-cpp for the barcodes, PySide6 (Qt Widgets) for the windows. It needs no Python
on the computer, loads nothing at run time and never goes on the network while it works (models are
an optional download on request, below). The application talks to
it through the command line described in [interface.md](interface.md); every step's own command
line is in it too (`docrepro typdoc …`, `docrepro optdoc …`, `docrepro ocrdoc …`, `docrepro tagdoc …`),
so that an
application ships one program, not one per step.

## Build

On the computer the program is for (PyInstaller does not cross-build), from a checkout of the
commit or tag the application pins:

```
uv sync --extra gui --group build
uv run python packaging/build.py
```

This writes into `dist/`:

| file | what it is |
|---|---|
| `docrepro-<target>` | the program; `<target>` is the Rust target triple Tauri expects, `aarch64-apple-darwin` on a Mac with Apple silicon |
| `docrepro-<target>.sha256` | its checksum |
| `docrepro-<target>.licences.json` | the packages inside, with versions and licences |

and then tries the program out the way an application uses it:

- `about` (typdoc, optdoc, ocrdoc and tagdoc installed, the window there) and each step's own `about` (the
  clean-up, HEIC, RapidOCR, the filters, tables and barcodes, the standard tagdoc follows);
- `run` on an invented photographed laboratory report with the temporary, home and cache folders
  pointed at empty folders, which must stay empty: the page prepared, its table found with its rows,
  the document described (its kind and date), a line of progress per step, four files;
- `run --config` with the chain document it wrote: the same four files, byte for byte;
- `edit --self-test`, which goes through the window without a person, off screen: every tab shown,
  the same PDF, nothing left behind;
- the steps one by one through their own command lines (typdoc binds the photo: it is in the
  PDF byte for byte);
- a failure, which must answer with its kind;
- `run --without ocrdoc --without tagdoc`: prepared only, the PDF and the chain document;
- `run --without typdoc`: the photo stays a JPEG through every step, prepared, read (its reading, the
  boxes in the picture's pixels, and the Markdown beside it) and described (the description in the
  picture itself); and the same picture again from its chain document;
- `run` with two photos of one document: bound into one PDF of two pages, the chain document naming
  both originals; and without typdoc, each a document of its own;
- `models list`: the models the steps can use, each with its step;
- on macOS the whole way and the window once more with the network closed by the system
  (`sandbox-exec`), and there `models fetch`, which must answer `model-unreachable` and keep
  nothing;
- with `--models <folder>` (a folder the orientation model was fetched into; the build fetches
  nothing itself): a scan on its head, which must come out upright and read, and the same files
  again from its chain document without the model.

It ends with a summary: size, checksum, timings, checks. `--no-check` builds only; `--check-only`
tries out the program built before. `--onedir` builds a folder instead of one file.

Built on macOS 27 (Apple M1 Max) with docrepro 0.2.0 (optdoc 0.8.0, ocrdoc 0.2.0, tagdoc 0.1.1),
Python 3.13, PyInstaller 6.22:

| | one file (default) | folder (`--onedir`) |
|---|---|---|
| size | 163 MB | 508 MB |
| `docrepro about` | 3.8 s | 0.3 s |
| `docrepro run` on a photographed one-page report (prepared, read, described) | 12.7 s | 4.2 s |
| the same with `--no-cells` (no tables) | 10.5 s | 3.7 s |
| `docrepro edit --self-test` on it (window open to closed, without a person) | 14.6 s | 5.3 s |
| `docrepro run --models` on a one-page scan on its head (set upright, read, described) | 12.2 s | 3.8 s |

Times are the mean of three runs; the first run after building or copying the program, or after a
while unused, takes longer (25 s for `run` as one file, 9 s as a folder). The one file unpacks
itself into the temporary folder at every start (and removes that copy at exit); that is where the
difference goes. The folder starts at once. Both pass the same checks. The program with every step
is no larger than optdoc 0.6.0 was on its own (162 MB): the steps share what is large (Python, Qt,
OpenCV, ONNX Runtime, the models).

## Into a Tauri application

**One file** (what Tauri calls a sidecar): put `docrepro-aarch64-apple-darwin` into
`src-tauri/binaries/` and name it in `tauri.conf.json`:

```json
{ "bundle": { "externalBin": ["binaries/docrepro"] } }
```

Tauri copies the file for the target it builds for into the application, beside its own program.
Start it with the shell plugin's `Command.sidecar("binaries/docrepro")` or from Rust.

**Folder**, for the shorter wait: put the folder `docrepro-aarch64-apple-darwin-onedir/` into the
application's resources (`bundle.resources`) and start
`<resources>/docrepro-aarch64-apple-darwin-onedir/docrepro` from Rust with `std::process::Command`.
The folder holds 64 symbolic links (Qt's frameworks); Tauri resolves them when it copies resources,
which makes the application larger than the folder and does no harm. Every library in it has to be
signed for notarisation; the build signs them all when given an identity (below).

Either way: give `run` and `edit` an empty folder of its own for `--out`, read the answer from
standard output (always one JSON object; status 0 or 2), and with `--progress` read standard error
line by line for `{"step": "ocrdoc", "page": n, "of": m}`. `edit` returns when the person closes the
window, which may take as long as they work: give it no time limit, and treat the error `cancelled`
as no error. The window asks to be brought to the front when it opens. With one file it appears
after the unpacking, some seconds after the start (the folder is quicker). A caller on macOS that
wants the system to make sure nothing goes out may start the program under
`sandbox-exec -p "(version 1)(allow default)(deny network*)"`; the whole way and the window work the
same there.

Tauri signs an `externalBin` again when it bundles the application, by default with the hardened
runtime (`bundle.macOS.hardenedRuntime`) and without docrepro's entitlements. The one file then does
not start: the system refuses the Python library it unpacks ("different Team IDs"). Either bundle
without the hardened runtime, or sign the program again after Tauri, with the hardened runtime and
`packaging/entitlements.plist`.

**Steps left out.** An application need not use every step: `--without <step>` leaves one out for a
document (a records app that only wants the text of a PDF it already holds gives `--without optdoc`),
and in the window the person switches steps on and off. The answer's `steps` say which were in use;
the filed PDF carries the chain document, which says so too, and makes the same files again.

**Models.** The program carries no optional model, and nothing fetches one unasked. An application
that wants its users to have one (so far `page-orientation`, 6.8 MB, with which a page scanned on
its head comes out upright) offers the download and keeps a folder for it, say in its application
support folder, and gives `run` and `edit` that folder with `--models`. Two ways to fill the folder,
both giving the same file: start `docrepro models fetch <name> --to <folder>` **outside** the fence
that closes the network (inside it the answer is `model-unreachable`), or fetch `url` from
`docrepro models list` itself, check `sha256` and `bytes`, and store the file under the name `file`.
`docrepro models list --models <folder>` says what is there (`present`). A file that is not the one
listed is never used. Nothing of a document or a person goes with the request.

**What a records app files.** The PDF docrepro writes carries tagdoc's description as the standard
medRDS says (title, kind, clinical date, the program, and what a person added). A records app that
files it with medRDS's reference library (`writePdfMetadata`) appends its own metadata; the
description stays beside them, and from the filed PDF and the original docrepro makes every file
again, byte for byte (`run --config <the filed PDF>`; `tests/test_filed.py` checks it with the
reference library). So the filed PDF is all an application has to keep to improve a result later:
`edit <original> --config <the filed PDF>`.

## Signing and notarising (macOS)

Without an identity the build is signed ad hoc, which is enough on the computer it was built on
and for trying out. For other computers:

```
uv run python packaging/build.py --identity "Developer ID Application: <name> (<team>)"
```

signs every library and the program with the hardened runtime and `packaging/entitlements.plist`
(`disable-library-validation`, because the one file loads the libraries it has just unpacked).
Inside an application, Tauri's notarisation of the application covers the program. Not tried yet:
there was no Developer ID to try it with.

## Other systems

`packaging/build.py` names the program for Linux (`x86_64-unknown-linux-gnu`, …) and Windows
(`x86_64-pc-windows-msvc`, with `.exe`) as well, and the specification is not tied to macOS; built
and tried so far only on macOS. That holds for `models fetch` too: from the program built on macOS
it reaches the address over TLS with the system's certificate authorities; whether the built
program finds them on Linux and Windows is not tried.

## Licences

docrepro, its steps and doccor are AGPL-3.0-or-later, and so is PyMuPDF. The program carries
further packages under permissive licences (`docrepro-<target>.licences.json` lists all 42) and
native libraries with their own: OpenCV brings FFmpeg (LGPL), pillow-heif brings libheif and
libde265 (LGPL) and x265 (GPL 2.0 or later), pypdfium2 brings pdfium (Apache 2.0 and BSD), PySide6
brings Qt (LGPL 3.0; its libraries are loaded from the program's own files and can be replaced);
tagdoc carries a copy of the schema of medRDS (MIT). An application that ships the program names
docrepro, its licence and where its source is (https://github.com/fre-ms/docrepro, the commit or
tag it pins, and those of the steps: `docrepro about` and the licence list name their versions).
