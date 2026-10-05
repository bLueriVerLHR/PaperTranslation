# Paper Translation Project

A reproducible pipeline for A4-sized, offline-readable Simplified Chinese HTML, with
paper extraction, native MathML, shared reader layout, coverage checks and packaging.
Translations are authored section by section; source-code analyses use the same reader runtime.

## What is published

**On `main`: the pipeline only.** The separately approved `pages-content` branch and
GitHub Pages site contain approved self-authored reviews and source-code analyses, not
rebuild sources. Paper translations are local-only and excluded from export. Translations
and figure crops retain the original authors' rights. All project content and output under
`dist/` is git-ignored, as is the local survey source under `/survey/`. A fresh clone has tools
and synthetic test fixtures, but no registered paper. Read `NOTICE.md` before redistributing
any output: the repository's MIT license does not cover other people's paper material.
Writing conventions are in `docs/chinese-writing.md`; publication boundaries and procedures
are in `docs/pages.md`. [Documentation responsibilities](docs/README.md) distinguish current
interfaces and procedures from version changes and temporary execution records.

## Project layout

Each project has one folder and one canonical set of rebuilding materials:

```
dist/<slug>/
    index.html                  Offline reading page
    manifest.json               Generated page/asset inventory
    assets/figures/             Reader figures (page-specific)
../assets/{styles,scripts}/      One shared reader/library/survey runtime
    notes/                      Supplementary analysis and reading notes, when present
    work/
        paper.json              Identity, source kind, section map, expectations
        content/                Translated Markdown sections, in reading order
        glossary.md             Shared terminology
        assets/figures/         Figure crops used by the builder
        reference/
            sections/           Useful extracted source sections
            pages/              Extracted page text or web snapshots
            pages-png/          Page rasters for formula/table review
            report.json         Extraction inventory
```

The folder is named `work`, without a leading underscore. It is retained for repairs,
additional information and rebuilding; it is not a disposable build cache. **Do not delete
`dist/` to clean the project.** Rebuilds update the reader and its published assets while
preserving `work/`. All pages reference one `dist/assets/` runtime. A reader-only library
copy keeps that shared tree plus the selected project HTML/figures in the same relative layout;
`work/` is not required for reading and may contain material unsuitable for redistribution.

Source PDFs are not copied into the workspace. Extraction reads the user's external original
in place; rebuilding needs only the retained translation, metadata and figure crops. A PDF
manifest may use `"source": {"pdf": null}` and require `--pdf` for future re-extraction, or
record the external original's path. The manifest schema is described in `docs/architecture.md`.

## Setup

Python 3.12+ is required; the dependency pins were verified with Python 3.14.

```powershell
. .\tools\dev-env.ps1 -CreateVenv
& $Python -m pip install -r requirements.txt
```

In each subsequent PowerShell session:

```powershell
. .\tools\dev-env.ps1
```

The helper sets `$Python`, `$ProjectTemp` and external Python/pytest/ruff cache paths.
The virtual environment and all disposable development state live beneath `$env:TEMP`, in a
project-specific directory. Do not use a separate fixed `C:/tmp` root. Use `$ProjectTemp/tasks` for task plans/presets and development
inputs, `$ProjectTemp/reports` for audit evidence, and `$ProjectTemp/scratch` for experiments,
trial outputs and throwaway backups. Do not create temporary folders in the workspace.
The harness's `.pi/tasks` is only a lightweight junction: its actual task logs live in TEMP too.
If the OS clears TEMP, recreate the environment and reinstall requirements using the setup
commands. Never store the only copy of canonical project materials there.

## Translate and build

Register a paper by creating `dist/<slug>/work/paper.json`. A slug is a lowercase English
identifier matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`; the Chinese title belongs in the metadata.
No per-paper tool constants are needed. Then extract from an external original:

```powershell
$P = "my-paper"
& $Python tools\extract.py --paper $P --pdf C:\path\to\original.pdf
```

For a web paper, the manifest instead names `source.web` and section URLs; `tools/web.py`
handles extraction. Both source kinds keep useful reference intermediates in `work/reference/`
and figure crops in `work/assets/figures/`.

Author translations one section at a time in `work/content/`, maintaining `work/glossary.md`.
Equations are MathML directly in the content, not LaTeX or runtime-rendered images. References
and author lists are intentionally not translated. Build from the retained work materials:

```powershell
& $Python tools\build.py --paper $P
```

Open `dist/<slug>/index.html` directly from `file://`, or copy the selected project and its
sibling shared `dist/assets/` tree to another machine.
The reader has light/dark mode and A4 print styles. Figures, CSS and scripts remain real files
reached by relative paths: no server, base64 payloads or runtime math renderer is needed.
Offline builds use installed fonts: Times New Roman (with compatible Latin fallbacks),
Source Han Serif SC for Chinese, and Maple Mono for code. Pages additionally self-hosts
licensed WOFF2 subsets; see `docs/pages.md`. Explicit-language code fences are highlighted
with Pygments at build time; pseudocode classes remain supported. Neither needs runtime tooling.

A shared UI change needs no article rebuild or per-project copying:

```powershell
& $Python tools\assets.py             # refresh dist/assets/ once; migrate legacy URLs if needed
```

Pages deployments automatically compose that same runtime from main with the approved
content snapshot. New review/analysis content requires separate publication approval;
paper translations remain local-only.

If a folder is inconvenient, export one file explicitly:

```powershell
& $Python tools\pack.py --paper $P --out dist\$P.html
# --figures-as-files inlines CSS/JS but leaves figures beside the export.
```

This is an opt-in export, not the default deliverable. No font is embedded in either format.

## GitHub Pages and mobile reading

The public reading library groups all exported pages by project, with title search and
relative links that work under `/PaperTranslation/`. Mobile readers have comfortable serif
text, persistent font-size controls, a theme toggle and TOC access. Wide formulas, tables
and code scroll locally instead of widening the entire page. Local reader presentation uses
centered TOC/citation cards and compact title-area source notes; see `docs/reader.md`.

For rights-restricted published articles, first seek and verify a corresponding arXiv
preprint and its license; translate that fixed version, citing the published edition only
for revisions rather than reproducing its full text. No `.pagesignore` is maintained.
`.gitignore` alone cannot withdraw already published pages or history. Author attribution and learning-use notices do not grant permission to
publish a translation. Reader redesigns can remain local without updating the live snapshot.

`main` contains `.github/workflows/pages.yml`; `pages-content` contains only validated public
HTML/assets and font licenses. Actions deploys the latter whenever either branch changes.
Neither `dist/` nor `/survey/` is force-added to main. Full setup and update instructions:
[docs/pages.md](docs/pages.md).

## Quality gates

```powershell
& $Python -m pytest
& $Python -m ruff check .
& $Python -m ruff format --check .
& $Python tools\coverage.py --paper $P
```

Coverage checks required headings, figures, tables and equations, and untranslated English
prose outside math/code. Source PDFs are not required to build or validate retained work.

## Shared pipeline and survey

| Path | Purpose |
|---|---|
| `src/templates/`, `src/styles/`, `src/scripts/` | Shared reader template, styling and enhancements |
| `tools/paper.py` | Discover `dist/*/work/paper.json` and derive all per-paper paths |
| `tools/` | Extract, build, coverage, optional pack, web extraction and survey tools |
| `tests/` | pytest suite with committed synthetic fixtures |
| `docs/` | Architecture and design notes |
| `src/survey/`, `src/templates/survey-*.html` | Tracked survey styling and templates |
| `survey/` | Local-only survey source, metadata, abstract translations and provenance |
| `dist/llm-survey/` | Generated offline LLM survey hub, detail pages and assets |

The survey is a separate product: one problem-first narrative places many papers in context,
with a detail page for every surveyed work. Its source remains under `survey/`, not the
per-paper `work/` layout:

- `survey/survey.json`: identity and declared directions;
- `survey/hub/NN-*.md`: narrative in reading order, with `{{paper:<slug>}}` markers;
- `survey/papers/<slug>/{meta.json,abstract.md}`: paper identity and translated abstract.

```powershell
& $Python tools\survey.py
```

The result is `dist/llm-survey/index.html`, `papers/*.html` and a real asset tree. Cards and detail
pages derive from the same metadata. Missing folders and unreferenced folders fail loudly;
repeated cards have unique HTML IDs, while reading order deduplicates each paper. Content
hashes include metadata and prose, and stale generated detail pages are removed on rebuild.

Citation counts are nullable: an unverified count is `null`, never zero. Verified counts carry
an as-of date and source, and notes distinguish editorial caveats from translated abstracts.
Directions and works are data, not tool constants. The anchored `/survey/` ignore rule must
remain so the tracked `src/survey/` stylesheet is not accidentally ignored.

## Local source checkouts

Owner-approved source checkouts live under ignored `repos/<repository>/`. Each keeps
its own `.git`, uncommitted files and upstream license; none is part of the pipeline's MIT
source tree or a Pages export. Canonical analysis metadata records the actual local path and
inspected commit. Do not create parallel copies when relocating a checkout. Build directories,
experiments and logs still belong under `$env:TEMP`, not inside these checkouts.

## Source-code analyses

Original code analyses can use the same offline reader without pretending to be translated
PDFs. `dist/redis-source-interview/work/` retains the authored sections, `meta.json` with the
inspected Redis commit, and `rebuild.py`. It reads no Redis checkout during rebuilding:

```powershell
& $Python dist\redis-source-interview\work\rebuild.py
```

Large chapters can compose focused topic/project Markdown files through standalone
`{{include:relative/path.md}}` directives. Includes are local, bounded and included in the
content hash; only top-level files become chapters. See `docs/source-analysis.md` for the
composition interface and requirements for structure, design comparisons and fixed-source
excerpts with symbols and line ranges.

External checkouts are not committed or published with the pipeline, and no runtime benchmark
claims are made without measurements. Per-paper supplementary notes live in `dist/<slug>/notes/`.

See `CONTRIBUTING.md` for the development workflow and `AGENTS.md` for operating rules.
