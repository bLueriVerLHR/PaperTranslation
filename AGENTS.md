# AGENTS.md

Operating manual for coding agents in this repository.

## Project

A reproducible pipeline that translates research papers (PDF or web) into a single
A4-sized, offline-readable HTML page, one self-contained file per paper. Only the pipeline is
published: `papers/` is git-ignored, so no translation, figure crop, manifest or extracted
source text enters the repository or its history. Three papers were translated with it locally:
*DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression* (DeepSeek-AI), *A comprehensive
survey and taxonomy of mamba: Applications, Challenges, and Future Directions* (Miao et al.,
Information Fusion 130, 2026) and *Neural Text Degeneration with Unlikelihood Training* (Welleck
et al., NeurIPS 2019).

## Layout

```
papers/<slug>/paper.json   Manifest: title, author, source PDF, section map, expectations (local only)
papers/<slug>/content/     Translated sections, one Markdown per section, source of truth (local only)
papers/<slug>/glossary.md  Terminology table shared across that paper's sections (local only)
papers/<slug>/assets/      Figure crops extracted from the PDF (local only)
src/templates/             HTML page template (shared by every paper)
src/styles/                CSS (theme + print/A4)
src/scripts/               Progressive-enhancement JS for the reader page
tools/                     Python pipeline (extract, build, pack, coverage, paper)
tests/                     pytest suite
docs/                      Architecture and design notes (committed)
dist/                      Build output (generated, ignored): dist/<title>.html plus dist/build/
.local/                    Isolated venv and source PDFs (ignored)
.tasks/                    Local task documents (ignored, never committed)
.reports/                  Test/scan reports (ignored)
```

## Environment

Python 3.14 is required. Everything else lives in an isolated virtual environment.

```powershell
py -3.14 -m venv .local/venv
.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run all pipeline commands with that interpreter, for example:

```powershell
.\.local\venv\Scripts\python.exe tools\build.py --paper mamba-survey
```

## Commands

`$P` is a registered paper slug: `deepseek-v41-flash`, `mamba-survey` or
`unlikelihood-training`. When only one paper is
registered, `--paper` may be omitted; with several it is required.

| Task | Command |
|---|---|
| Install deps | `.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt` |
| Extract source | `.\.local\venv\Scripts\python.exe tools\extract.py --paper $P` |
| Build page | `.\.local\venv\Scripts\python.exe tools\build.py --paper $P` |
| Pack single file | `.\.local\venv\Scripts\python.exe tools\pack.py --paper $P` |
| Tests | `.\.local\venv\Scripts\python.exe -m pytest` |
| Lint | `.\.local\venv\Scripts\python.exe -m ruff check .` |
| Format | `.\.local\venv\Scripts\python.exe -m ruff format .` |
| Coverage check | `.\.local\venv\Scripts\python.exe tools\coverage.py --paper $P` |

## Conventions

- Google style; for Python this means PEP 8 plus PEP 257 docstrings.
- Additive changes keep `dist/` buildable at all times; never commit generated output.
- Content is written one section per file and translated section by section. Do not
  translate ahead of the source order.
- Math is authored as MathML directly in the content files. Do not introduce LaTeX or
  runtime math renderers into the delivered page.
- No font is embedded, downloaded or vendored. The stylesheet only names font families in
  priority order and the browser resolves every glyph from the reader's own fonts, so do not
  add `@font-face`, `data:font/` URIs or a bundled face back into the page.
- Keep the raw English source and the source PDFs out of git (they live under `.local/`).
- Keep the whole of `papers/` out of git too: translations are derivative works and figure crops
  are verbatim extracts, so they are local-only and `.gitignore` must list them. `git ls-files
  papers` stays empty, in the working tree and in every commit.
- References and the author list are intentionally not translated.
- A new paper is added by writing `papers/<slug>/paper.json`; do not add per-paper constants to
  the tools.
- Run `ruff format` and `ruff check` before every commit.

## Do not touch

- `papers/` at all: it is local state, ignored by git and never published. Never `git add -f` it,
  and never rewrite the ignore rule to let it back in.
- `papers/*/assets/figures/` images: they are extracted verbatim from the source PDFs; regenerate
  them with `tools/extract.py` instead of editing by hand.
- `.tasks/`, `.local/`, `.logs/`, `.reports/`, `.tmp/`: local-only state.
