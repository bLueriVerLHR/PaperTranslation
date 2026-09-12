# AGENTS.md

Operating manual for coding agents in this repository.

## Project

A reproducible pipeline that translates research papers (PDF or web) into a single
A4-sized, offline-readable HTML page. The current instance translates
*DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression* into Simplified Chinese.

## Layout

```
src/content/       Translated sections, one Markdown file per section (the source of truth)
src/glossary.md    Terminology table shared across sections
src/templates/     HTML page template
src/styles/        CSS (theme + print/A4)
src/scripts/       Progressive-enhancement JS for the reader page
src/assets/        Committed inputs: extracted figures, subset fonts (+ OFL notice)
tools/             Python pipeline (extract, build, fonts)
tests/             pytest suite
docs/              Architecture and design notes (committed)
dist/              Build output (generated, ignored)
.local/            Isolated venv, source PDF, downloaded fonts (ignored)
.tasks/            Local task documents (ignored, never committed)
.reports/          Test/scan reports (ignored)
```

## Environment

Python 3.14 is required. Everything else lives in an isolated virtual environment.

```powershell
py -3.14 -m venv .local/venv
.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run all pipeline commands with that interpreter, for example:

```powershell
.\.local\venv\Scripts\python.exe tools\build.py
```

## Commands

| Task | Command |
|---|---|
| Install deps | `.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt` |
| Extract source | `.\.local\venv\Scripts\python.exe tools\extract.py` |
| Build page | `.\.local\venv\Scripts\python.exe tools\build.py` |
| Tests | `.\.local\venv\Scripts\python.exe -m pytest` |
| Lint | `.\.local\venv\Scripts\python.exe -m ruff check .` |
| Format | `.\.local\venv\Scripts\python.exe -m ruff format .` |
| Font download | `.\.local\venv\Scripts\python.exe tools\fonts.py download` |
| Font subset | `.\.local\venv\Scripts\python.exe tools\fonts.py subset` |
| Coverage check | `.\.local\venv\Scripts\python.exe tools\coverage.py` |
| Font coverage check | `.\.local\venv\Scripts\python.exe tools\build.py --check-fonts` |

## Conventions

- Google style; for Python this means PEP 8 plus PEP 257 docstrings.
- Additive changes keep `dist/` buildable at all times; never commit generated output.
- Content is written one section per file and translated section by section. Do not
  translate ahead of the source order.
- Math is authored as MathML directly in the content files. Do not introduce LaTeX or
  runtime math renderers into the delivered page.
- Keep the raw English source, the source PDF, and downloaded upstream fonts out of git
  (they live under `.local/`).
- References and the author list are intentionally not translated.
- Run `ruff format` and `ruff check` before every commit.

## Do not touch

- `src/assets/figures/` images: they are extracted verbatim from the source PDF; regenerate
  them with `tools/extract.py` instead of editing by hand.
- `.tasks/`, `.local/`, `.logs/`, `.reports/`, `.tmp/`: local-only state.
