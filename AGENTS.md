# AGENTS.md

Operating manual for coding agents in this repository.

## Project

A reproducible pipeline that translates research papers (PDF or web) into an A4-sized,
offline-readable HTML page. Each paper gets its own folder, `dist/<slug>/`, holding
`index.html` beside a real `assets/` tree (stylesheet, reader script, figure crops), all
referenced by relative path so the page opens straight from `file://` with no server and no
base64 payloads. Only the pipeline is published: `papers/` is git-ignored, so no translation,
figure crop, manifest or extracted source text enters the repository or its history. Four
papers were translated with it locally: *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache
Compression* (DeepSeek-AI), *A comprehensive survey and taxonomy of mamba: Applications,
Challenges, and Future Directions* (Miao et al., Information Fusion 130, 2026), *Neural Text
Degeneration with Unlikelihood Training* (Welleck et al., NeurIPS 2019) and *On-device large
language models: a survey of model compression and system optimization* (Chen et al.,
Artificial Intelligence Review 59:191, 2026).

## Layout

```
papers/<slug>/paper.json   Manifest: title, author, source PDF, section map, expectations (local only)
papers/<slug>/content/     Translated sections, one Markdown per section, source of truth (local only)
papers/<slug>/glossary.md  Terminology table shared across that paper's sections (local only)
papers/<slug>/assets/      Figure crops extracted from the PDF (local only)
src/templates/             HTML page template (shared by every paper)
src/styles/                CSS (theme + print/A4)
src/scripts/               Progressive-enhancement JS for the reader page
tools/                     Python pipeline (extract, build, pack, coverage, paper, survey)
tests/                     pytest suite
docs/                      Architecture and design notes (committed)
dist/<slug>/               Deliverable folder per paper (generated, ignored): index.html plus its assets/ tree
dist/survey/               Survey deliverable (generated, ignored): index.html, papers/*.html, assets/
survey/survey.json         Survey identity: title, subtitle, author, the seven directions (local only)
survey/hub/NN-*.md         Survey narrative in reading order; `{{paper:<slug>}}` expands to a card (local only)
survey/papers/<slug>/      One folded paper per surveyed work: meta.json, abstract.md (local only)
src/survey/survey.css      Survey styling, additive on top of src/styles/reader.css (committed)
src/templates/survey-*.html  Hub and detail-page templates (committed)
.local/                    Isolated venv and source PDFs (ignored)
.tasks/                    Local task documents (ignored, never committed)
.reports/                  Test/scan reports (ignored)
```

## Environment

Python 3.12 or newer is required (3.14 is what the pins in `requirements.txt` were verified
against). Everything else lives in an isolated virtual environment:

```powershell
py -3.14 -m venv .local/venv          # or: C:\Users\Lozz\anaconda3\python.exe -m venv .local/venv
.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run all pipeline commands with that interpreter, for example:

```powershell
.\.local\venv\Scripts\python.exe tools\build.py --paper mamba-survey
```

## Commands

`$P` is a registered paper slug: `deepseek-v41-flash`, `mamba-survey`,
`unlikelihood-training` or `on-device-llm-survey`. When only one paper is
registered, `--paper` may be omitted; with several it is required. The slug is also the
deliverable folder name, so it is a lowercase English identifier (`^[a-z0-9]+(?:-[a-z0-9]+)*$`),
never the Chinese title.

| Task | Command |
|---|---|
| Install deps | `.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt` |
| Extract source | `.\.local\venv\Scripts\python.exe tools\extract.py --paper $P` |
| Build page | `.\.local\venv\Scripts\python.exe tools\build.py --paper $P` |
| Pack single file (export) | `.\.local\venv\Scripts\python.exe tools\pack.py --paper $P --out dist\$P.html` |
| Tests | `.\.local\venv\Scripts\python.exe -m pytest` |
| Lint | `.\.local\venv\Scripts\python.exe -m ruff check .` |
| Format | `.\.local\venv\Scripts\python.exe -m ruff format .` |
| Coverage check | `.\.local\venv\Scripts\python.exe tools\coverage.py --paper $P` |
| Build the survey | `.\.local\venv\Scripts\python.exe tools\survey.py` |

## Conventions

- Google style; for Python this means PEP 8 plus PEP 257 docstrings.
- Additive changes keep `dist/` buildable at all times; never commit generated output.
- The deliverable is a folder, `dist/<slug>/`, not an embedded blob. Figures, the stylesheet
  and the reader script stay real files reached by relative path; `tools/pack.py` is an
  opt-in export, never the default. Do not put `data:` image URIs back into the built page.
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
- `tools/survey.py` is a separate product from `tools/build.py` and is deliberately
  direction-agnostic: surveying another paper means adding `survey/papers/<slug>/{meta.json,
  abstract.md}` and one `{{paper:<slug>}}` marker in the hub prose, never editing the tool. The
  card on the hub and the detail page are rendered from the same `meta.json`, so they cannot
  drift apart. The build fails loudly in both directions - a marker with no folder, and a
  surveyed folder the hub never references.
- A paper may be referenced from more than one section: `reading_order` deduplicates it, and
  only the HTML `id` is suffixed (`paper-<slug>`, then `paper-<slug>--2`). This is what lets the
  survey be problem-first, since a problem like repetition is addressed at several stages.
- Citation counts are nullable. A count that was not verified must stay `null` and render as
  unverified - never store `0`, which is a claim that nobody cited the paper. Verified counts
  carry `cites_asof` and `cites_source`; `cites_matched_title` records the title the API matched.
- `survey/curation/` holds the local-only provenance scripts (source archiving, metadata
  materialization, citation application, built-site audit). They are ignored along with the rest
  of `survey/`, and they must never invent a count or overwrite a verified field.
- Survey prose and abstract translations are mixed in the same files, so the whole of `survey/`
  is local-only for the same reason as `papers/`. Keep the ignore rule **anchored** (`/survey/`):
  a bare `survey/` also matches the tracked `src/survey/` and would silently drop the survey
  stylesheet from the repository.
- Run `ruff format` and `ruff check` before every commit.

## Do not touch

- `papers/` at all: it is local state, ignored by git and never published. Never `git add -f` it,
  and never rewrite the ignore rule to let it back in.
- `survey/` at all: same reasoning as `papers/`, since its Markdown files interleave our prose
  with translations of other people's abstracts. Build it, never commit it.
- `papers/*/assets/figures/` images: they are extracted verbatim from the source PDFs; regenerate
  them with `tools/extract.py` instead of editing by hand.
- `.tasks/`, `.local/`, `.logs/`, `.reports/`, `.tmp/`: local-only state.
