# Paper Translation Project

This project is initially built for translate papers from websites or pure PDF.

## What this is

A reproducible pipeline that turns a research paper into a single A4-sized, offline-readable
HTML page in Simplified Chinese, plus the working instance of that pipeline: a full
translation of *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression*
(51 pages, 12 figures, 5 tables, 17 numbered equations).

The problem it solves: translating a long technical paper well needs many sessions, consistent
terminology, faithful math, and a layout that survives both a phone and a printed page. Doing
that by hand in one document is error-prone, so the source is split into one Markdown file per
section, the mechanical parts (extraction, MathML, fonts, layout, packaging) are automated, and
a coverage checker proves nothing was dropped.

## Quickstart

```powershell
py -3.14 -m venv .local/venv
.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt

# The source PDF is not committed. Put it here first:
#   .local/source/DeepSeek_V41_Tech_Report.pdf

.\.local\venv\Scripts\python.exe tools\extract.py     # PDF -> page text, rasters, figure crops
.\.local\venv\Scripts\python.exe tools\build.py       # content -> dist/index.html
```

Open `dist/index.html` directly from the filesystem (no server needed) or print it to A4 PDF.

One-time font vendoring, only needed when the content introduces new characters:

```powershell
.\.local\venv\Scripts\python.exe tools\fonts.py download   # Source Han Sans SC -> .local/fonts
.\.local\venv\Scripts\python.exe tools\fonts.py subset     # -> src/assets/fonts (committed)
```

## Quality gates

```powershell
.\.local\venv\Scripts\python.exe -m pytest                 # unit tests
.\.local\venv\Scripts\python.exe -m ruff check .           # lint
.\.local\venv\Scripts\python.exe tools\coverage.py         # every section/figure/table/equation present, no English prose left
.\.local\venv\Scripts\python.exe tools\build.py --check-fonts   # zero missing CJK glyphs
```

## Repository layout

| Path | Purpose |
|---|---|
| `src/content/*.md` | The translation, one Markdown file per section (source of truth) |
| `src/glossary.md` | Binding terminology table shared across sections |
| `src/templates/`, `src/styles/`, `src/scripts/` | Page template, theme/print CSS, reader enhancements |
| `src/assets/figures/` | Figure crops extracted verbatim from the PDF |
| `src/assets/fonts/` | Source Han Sans SC subset to the content characters, plus its OFL notice |
| `tools/` | `extract.py`, `build.py`, `fonts.py`, `coverage.py` |
| `tests/` | pytest suite, including a sample fixture that exercises every rendering path |
| `docs/` | Architecture and design notes |
| `dist/` | Build output (generated, ignored) |
| `.local/` | Isolated venv, source PDF, downloaded upstream fonts (ignored) |

## Destination Format

- A HTML page with A4 paper size.
- Pure reading experience with light/dark mode.
- Equations and formulas are written in HTML not latex for adapting mobile view.
- Default font for alphabet is Times New Roman.
- Codes and pseudo codes using monospace font with syntax highlights.
- Chinese font use Source Han Sans.
- Citations, Reference, Acknowledgement and format stuffs are not needed to be translated.
- Need a table of content which is folded by default.

If you find anything missing and need an installation, make list and the user will install it in the best way. Keep isolation environment.

## While Translating

- Translate sections one by one, step by step avoiding translate as a whole.
- You are allowed to fix previous mistakes if new evidence appears in the following contents.
- Do not spoil.
- Follow the tongue.

## Scope of the current instance

Translated: abstract, Sections 1-6, Appendix B, Appendix C.
Not translated, by project rule: References, Appendix A (author list), acknowledgement and
format matter. Highlighting is expressed with committed CSS classes rather than a runtime
highlighter, because the paper contains a single pseudocode block.
