# Paper Translation Project

This project is initially built for translate papers from websites or pure PDF.

## What this is

A reproducible pipeline that turns a research paper into a single self-contained A4-sized,
offline-readable HTML page in Simplified Chinese, plus the translated papers themselves.

The problem it solves: translating a long technical paper well needs many sessions, consistent
terminology, faithful math, and a layout that survives both a phone and a printed page. Doing
that by hand in one document is error-prone, so each paper's source is split into one Markdown
file per section, the mechanical parts (extraction, MathML, fonts, layout, packaging) are
automated, and a coverage checker proves nothing was dropped.

Two papers are translated so far:

| Paper | Scope |
|---|---|
| *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression* (DeepSeek-AI, 51 pages) | abstract, Sections 1-6, Appendix B, Appendix C; 12 figures, 5 tables, 17 equations |
| *A comprehensive survey and taxonomy of mamba: Applications, Challenges, and Future Directions* (Miao et al., Information Fusion 130, 2026, 23 pages) | abstract, Sections 1-9; 3 figures, 5 tables, 5 equations |

In both, references, the author list, funding, CRediT and the competing-interest statement stay
in the original.

## Quickstart

```powershell
py -3.14 -m venv .local/venv
.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt
```

The source PDFs are not committed. Each paper's manifest names where it expects its PDF, under
`.local/source/<slug>/`:

```
.local/source/deepseek-v41-flash/DeepSeek_V41_Tech_Report.pdf
.local/source/mamba-survey/paper.pdf
```

Then, per paper:

```powershell
$P = "deepseek-v41-flash"   # or: mamba-survey

.\.local\venv\Scripts\python.exe tools\extract.py --paper $P   # PDF -> page text, rasters, figure crops
.\.local\venv\Scripts\python.exe tools\build.py   --paper $P   # content -> dist/build/<slug>/index.html
.\.local\venv\Scripts\python.exe tools\pack.py    --paper $P   # -> dist/<title>.html
```

The deliverable is one self-contained file per paper, `dist/<document title>.html`. It inlines
the subset fonts, all figures, the stylesheet and the reader script as `data:` URIs, so it can
be copied to a USB stick or another machine and opened by double-clicking, with no server and
no sibling assets. The multi-file build under `dist/build/<slug>/` remains available, because
it is easier to inspect and test. Print the packed file to get an A4 PDF.

One-time font vendoring, only needed when the content introduces new characters:

```powershell
.\.local\venv\Scripts\python.exe tools\fonts.py download   # Source Han Sans SC -> .local/fonts
.\.local\venv\Scripts\python.exe tools\fonts.py subset     # -> src/assets/fonts (committed)
```

The subset covers the union of every paper's characters, so it is shared rather than per paper.

## Quality gates

```powershell
.\.local\venv\Scripts\python.exe -m pytest                      # unit tests
.\.local\venv\Scripts\python.exe -m ruff check .                # lint
.\.local\venv\Scripts\python.exe tools\coverage.py --paper $P   # every section/figure/table/equation present, no English prose left
.\.local\venv\Scripts\python.exe tools\build.py --paper $P --check-fonts   # zero missing CJK glyphs
```

## Repository layout

| Path | Purpose |
|---|---|
| `papers/<slug>/paper.json` | The manifest: title, author, source PDF, printed section map, coverage expectations |
| `papers/<slug>/content/*.md` | The translation, one Markdown file per section (source of truth) |
| `papers/<slug>/glossary.md` | Binding terminology table shared across that paper's sections |
| `papers/<slug>/assets/figures/` | Figure crops extracted verbatim from that paper's PDF |
| `src/templates/`, `src/styles/`, `src/scripts/` | Page template, theme/print CSS, reader enhancements (shared) |
| `src/assets/fonts/` | Source Han Sans SC subset to the content characters, plus its OFL notice (shared) |
| `tools/paper.py` | Manifest loading and every path derived from a paper slug |
| `tools/` | `extract.py`, `build.py`, `pack.py`, `fonts.py`, `coverage.py` |
| `tests/` | pytest suite, including a sample fixture that exercises every rendering path |
| `docs/` | Architecture and design notes |
| `dist/` | Build output (generated, ignored) |
| `.local/` | Isolated venv, source PDFs, downloaded fonts (ignored) |

Adding a paper means creating `papers/<slug>/paper.json` with its title, source PDF, section
map and expectations; no tool code changes.

## Destination Format

- A HTML page with A4 paper size.
- Pure reading experience with light/dark mode.
- Equations and formulas are written in HTML not latex for adapting mobile view.
- Default font for alphabet is Times New Roman.
- Codes and pseudo codes using monospace font with syntax highlights.
- Chinese font use Source Han Sans.
- Citations, Reference, Acknowledgement and format stuffs are not needed to be translated.
- Need a table of content which is folded by default.

If you find anything missing and need an installation, make list and the user will install it in
the best way. Keep isolation environment.

## While Translating

- Translate sections one by one, step by step avoiding translate as a whole.
- You are allowed to fix previous mistakes if new evidence appears in the following contents.
- Do not spoil.
- Follow the tongue.

## Licensing

The pipeline code (under `tools/`, `tests/`, and the template/styles/script directories) is
MIT-licensed; see `LICENSE`. The translated text and the extracted figures are **not** covered
by that grant: they reproduce material from the original papers and remain the rights holders'
property. Read `NOTICE.md` before redistributing anything.
