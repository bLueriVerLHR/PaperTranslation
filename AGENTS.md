# AGENTS.md

Operating manual for coding agents in this repository.

## Project and publication boundary

A reproducible pipeline translates research papers (PDF or web) into A4-sized,
offline-readable HTML. The `main` branch publishes only the pipeline. An explicitly
approved reader-only export is published separately on `pages-content` and GitHub Pages;
translations and figure crops retain the original authors' rights, not the MIT license.
All canonical project material lives under ignored `dist/`; never force-add it to main.
`work/`, source PDFs, extracted reference data and `/survey/` sources remain local-only.
Use `tools/pages.py` to stage approved rendered pages/assets in system TEMP and validate
before pushing the content branch. Never publish that branch's files under the MIT license.

## Layout

```
dist/<slug>/index.html                Offline reader page
dist/<slug>/assets/                   Published styles, script and figures
dist/<slug>/manifest.json             Generated page/asset inventory
dist/<slug>/work/paper.json           Project identity, source kind, sections, expectations
dist/<slug>/work/content/*.md         Translation source of truth, one file per section
dist/<slug>/work/glossary.md          Binding terminology
dist/<slug>/work/assets/figures/      Figure crops used to rebuild the page
dist/<slug>/work/reference/           Useful extracted source text, page rasters and inventory
dist/<slug>/notes/                    Supplementary analysis and reading notes
src/templates/                       Shared page and survey templates
src/styles/                          Shared reader theme and print/A4 styles
src/scripts/                         Progressive-enhancement reader script
src/survey/                          Tracked survey stylesheet
tools/                               Python pipeline and development environment helper
tests/                               pytest suite and committed synthetic test fixtures
docs/                                Architecture and design notes
survey/survey.json                   Local-only survey identity and directions
survey/hub/NN-*.md                    Local-only survey narrative
survey/papers/<slug>/                 Local-only survey metadata and abstract translations
dist/llm-survey/                     Generated LLM survey hub, detail pages and assets
System TEMP/<project>/               Disposable environment, caches, tasks, reports, experiments
```

`work` is the directory name, not an underscore-prefixed variant. Keep one canonical copy of
translation source and metadata there, not a second parallel project-source tree. The reader
needs only `index.html` and `assets/`; `work/` is retained for maintenance and rebuilding.
Never delete the whole `dist/` tree as a cleanup step: it now contains source-of-truth material.

## Environment and commands

Python 3.12+ is required; dependency pins were verified with Python 3.14. In each new
PowerShell session, initialize the external environment:

```powershell
. .\tools\dev-env.ps1                 # sets $Python and $ProjectTemp
# First setup, or after system TEMP has been cleared:
. .\tools\dev-env.ps1 -CreateVenv
& $Python -m pip install -r requirements.txt
```

Always run commands with `$Python`. `$P` is a registered project slug, discovered from
`dist/*/work/paper.json`. If several projects exist, `--paper` is required.

| Task | Command |
|---|---|
| Extract external PDF | `& $Python tools\extract.py --paper $P --pdf C:\path\to\original.pdf` |
| Build reader | `& $Python tools\build.py --paper $P` |
| Optional single-file export | `& $Python tools\pack.py --paper $P --out dist\$P.html` |
| Tests | `& $Python -m pytest` |
| Lint | `& $Python -m ruff check .` |
| Format | `& $Python -m ruff format .` |
| Coverage | `& $Python tools\coverage.py --paper $P` |
| Build survey | `& $Python tools\survey.py` |

## Source and intermediate-data policy

- Do not copy source PDFs into the workspace or into a project's `work/` folder. Read the
  user's existing external original in place with `--pdf`. A manifest may record an external
  path, or use `"source": {"pdf": null}` when no path is retained. Building the reader requires
  no original PDF. Re-extraction requires the original to be supplied again.
- Keep only useful reference intermediates in `work/reference/`: extracted sections, page
  text, page rasters and extraction inventory. Keep translated sections, glossary, metadata
  and figure crops in their designated `work/` paths.
- Rebuilds update the reader and published assets in place and preserve `work/`. Do not
  hand-edit figure crops; regenerate from the external original using the extraction tool.
- Per-project source and reference data stay out of git. `git ls-files dist` must be empty.
  Legacy denylist entries in `.gitignore` are safeguards, not instructions to create folders.

## Temporary-state policy

- Every disposable task plan/preset, development dataset, log, screenshot, scan report,
  experiment, trial build and backup uses an **absolute path under system TEMP**.
  Use `$ProjectTemp/tasks`, `$ProjectTemp/reports` and `$ProjectTemp/scratch` respectively.
  Python scratch files use `tempfile`, never repository-relative scratch paths.
- The environment helper routes Python/pytest/ruff caches outside the workspace and keeps
  the virtual environment there too. Do not create workspace environments or cache folders.
- The background harness's `.pi/tasks` path is a lightweight junction to system TEMP;
  actual task records and logs live outside the workspace. If another tool cannot redirect
  logs, relocate them only after its writer has finished.
- TEMP is disposable: recreate the environment and reinstall requirements if it is cleared.
  Never make it the only copy of canonical translation material or useful reference data.
  PDF copies removed during migration are only a temporary recovery archive, not a permanent
  source location or an input path to record in project metadata.

## Content and rendering conventions

- Google-style Python: PEP 8 and PEP 257. Run `ruff format` and `ruff check` before committing.
- Additive changes keep existing reader deliverables buildable. Do not commit generated output
  to main; only approved, validated reader-only exports belong on `pages-content`.
- Translate one section at a time in source order. Do not translate ahead of the source.
- Author math directly as MathML. Do not add LaTeX or runtime math renderers to delivered pages.
- Keep figures, CSS and scripts as real files referenced by relative paths. Do not introduce
  `data:` image URIs into the default reader. `tools/pack.py` is an opt-in export only.
- Offline builds use installed fonts and do not embed or download them. The authorized
  Pages export is the exception: `tools/pages_fonts.py` downloads hash-pinned OFL fonts to
  system TEMP and publishes renamed WOFF2 subsets plus licenses on `pages-content` only.
  Do not vendor font binaries into main or redistribute Microsoft Times New Roman.
- References and the author list are intentionally not translated.
- Register a project by writing `dist/<slug>/work/paper.json`, never per-project tool constants.
  Slugs match `^[a-z0-9]+(?:-[a-z0-9]+)*$`, not Chinese titles.
- Original source-code analyses are not PDF/web translations. They may retain `work/meta.json`
  with the inspected local repository and exact commit, section Markdown, and a local
  `work/rebuild.py` that uses the shared builder. Do not invent a PDF/web manifest merely to
  register an analysis. Copy no external repository wholesale; keep experiments in TEMP.
- Keep authored local-only material intact when changing the pipeline. Migration authorization
  permits relocation and path metadata updates, not rewriting translations or figure images.

## Survey conventions

- `tools/survey.py` is separate from the paper builder and direction-agnostic. Add surveyed
  works through `survey/papers/<slug>/{meta.json,abstract.md}` and hub `{{paper:<slug>}}`
  markers, never tool constants. Do not modify or publish existing `survey/` source material
  as part of pipeline cleanup.
- Hub cards and detail pages come from the same metadata. Fail on markers without folders
  and folders without markers. Repeated references deduplicate reading order; only HTML IDs
  gain suffixes (`paper-<slug>`, then `paper-<slug>--2`).
- Citation counts are nullable: unverified means `null`, not zero. Verified counts carry
  `cites_asof` and `cites_source`; `cites_matched_title` records the API-matched title.
  Local provenance scripts must not invent counts or overwrite verified fields.
- Keep the survey ignore rule anchored (`/survey/`), so tracked `src/survey/` is not swallowed.
  `git ls-files survey` stays empty. Keep translations and extracted material out of all
  future commits; never relax ignore rules or use `git add -f` to publish them.

## Source selection and publication review

Before translating a rights-restricted published article, first seek its corresponding
arXiv preprint. Verify identity, authors, fixed version and an adaptation-permitting license;
arXiv availability alone is not permission. Translate that version in full, and use the
published edition only for cited revisions rather than reproducing its complete content.

Do not maintain `.pagesignore` as a substitute for this review. Public snapshots still
require explicit owner approval and contain only readers/assets, not source PDFs, complete
English papers, extraction data or canonical work. Personal-learning and translation-only
publication do not grant additional rights. Preserve actual attribution and licensing.
