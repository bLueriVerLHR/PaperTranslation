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
Paper translations are local-only: do not publish full-paper readers or their crops,
even with `public_export: true`. Public content consists of approved self-authored reviews
and source-code books. Do not default to translating online surveys. Withdrawal, history
rewriting and publishing local revisions require their own explicit authorization.

## Layout

```
dist/<slug>/index.html                Offline reader page
dist/<slug>/assets/figures/           Page-specific published figures
dist/assets/{styles,scripts}/         One shared reader/library/survey runtime
dist/<slug>/manifest.json             Generated page/asset inventory
dist/<slug>/work/paper.json           Project identity, source kind, sections, expectations
dist/<slug>/work/content/*.md         Translation source of truth, one file per section
dist/<slug>/work/glossary.md          Binding terminology
dist/<slug>/work/reader.json          Optional citation/presentation metadata
dist/<slug>/work/reader-meta.md       Header-only source/rights/reading notes
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
translation source and metadata there, not a second parallel project-source tree. Reading needs the project HTML/figures plus the sibling library-root `dist/assets/` runtime;
`work/` is retained for maintenance and rebuilding. Never reintroduce per-project copies of
reader/library/survey CSS or JS. `tools/assets.py` updates the runtime once without rebuilding
prose; Pages composes it from main into the approved snapshot at deployment.
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

## Documentation responsibilities

- README describes capabilities, setup and project layout. `docs/` specifies architecture,
  interfaces, procedures and writing conventions, not current task progress or approval history.
- AGENTS contains durable execution constraints. Actual version changes belong in CHANGELOG;
  temporary plans, pauses, approvals and execution logs belong in task state and TEMP reports.
  Do not turn user dialogue or one-off operations into permanent documentation rules.

## Mandatory reading before manuscript work

Before every manuscript task (new writing, expansion, rewriting, translation or polishing),
read the applicable documents **in full** and follow them throughout drafting and review.
Do not rely only on summaries, remembered rules or keyword scans:

- All manuscript work: `docs/chinese-writing.md` for genre, mechanism depth, mathematical
  reasoning, evidence boundaries, terminology, prose and paragraph-level review.
- Original reviews: also `docs/review-method.md` for source identity, primary-source checks,
  claim-to-evidence mapping and fair comparisons.
- Framework/project/source-code analysis, including such passages within reviews: also
  `docs/source-analysis.md` for structure, state/data flow, documented challenges, design
  trade-offs, readable fixed-version excerpts and modular manuscript maintenance.
- Explicit question-bank/revision chapters: also read `docs/questions.md`; Q&A is opt-in
  for the requested scope, not a reason to convert ordinary book chapters into interview
  scripts. Preserve evidence-based answers, offline fallbacks and complete printed content.
- Before changing an existing project manuscript, read its canonical `work/README.md`,
  glossary, relevant source map/research records and the complete affected sections.

Explain how mechanisms work, how they differ from prior approaches, why their benefits
can arise and what assumptions and costs constrain them. Include necessary derivations
with explicit premises; distinguish mathematical properties, explanatory inference and
reported experiments. Writing requirements and task dialogue are not reader prose.
Keep document-build checks separate from mathematical or empirical validation, and do
not execute upstream projects or experiments without separate explicit authorization.
Detailed requirements belong to the linked specifications, not duplicate project templates.

## Content and rendering conventions

- Google-style Python: PEP 8 and PEP 257. Run `ruff format` and `ruff check` before committing.
- Additive changes keep existing reader deliverables buildable. Do not commit generated output
  to main; only approved, validated reader-only exports belong on `pages-content`.
- Translate one section at a time in source order. Do not translate ahead of the source.
- Follow the mandatory manuscript reading requirements above. Translations
  and reviews use academic prose; source-code analyses use analysis-centred technical-book
  prose with relevant practical cases. Task prompts, meeting/interview framing, answer scripts,
  authoring progress and delivery/rebuild chatter do not belong in reader prose. Keep useful
  technical conditions, evidence, attribution and verification limits; do not substitute keyword
  deletion or boilerplate templates for paragraph-level review.
- For framework and project source analyses, read and follow `docs/source-analysis.md`: explain
  module structure and state/data flow, then connect documented business challenges to
  implemented mechanisms and trade-offs. Ground challenges and design rationale in official
  docs, source comments, maintainer explanations and verified issue/PR/commit discussions;
  distinguish community consensus, version-specific reports and explanatory inference.
  Show relevant short source excerpts with fixed commit, file, symbol and real line ranges,
  not path-only inventories. Do not compile/run upstream projects, their tests or benchmarks,
  or perform local ablations for manuscript research without separate explicit authorization.
  Read-only source checks and documentation-build validation are distinct from upstream execution.
  Split large manuscripts into focused subdocuments with the shared builder's safe include
  interface; retain a single canonical copy and keep authoring instructions out of prose.
- Author math directly as MathML. Do not add LaTeX or runtime math renderers to delivered pages.
- Keep figures, CSS and scripts as real files referenced by relative paths. Do not introduce
  `data:` image URIs into the default reader. `tools/pack.py` is an opt-in export only.
- Offline builds use installed fonts and do not embed or download them. The authorized
  Pages export is the exception: `tools/pages_fonts.py` downloads hash-pinned OFL fonts to
  system TEMP and publishes renamed WOFF2 subsets plus licenses on `pages-content` only.
  Do not vendor font binaries into main or redistribute Microsoft Times New Roman.
- References and the author list are intentionally not translated. Retain original
  bibliography data locally even when the reader replaces its visible list with citation
  links/cards. Never invent reference identities or choose ambiguous matches.
- Reader typography and modal behavior belong to the shared styles/script. Keep source,
  licensing and reading-limit notes beneath the title, not as publishing-style body sections;
  see `docs/reader.md` for presentation profiles and progressive fallback behavior.
- Before translating a rights-restricted published paper, first look for its corresponding
  arXiv preprint. Confirm authors, identity, fixed version and a license permitting adaptations;
  being on arXiv is not itself permission. Use that version as the full translation source.
  Cite the published paper for revisions, without reproducing its complete content by default.
- Do not maintain `.pagesignore` as a substitute for source/rights review. Public exports
  remain explicitly approved reader-only snapshots. Personal learning and translation-only
  publication do not grant additional rights. History rewrites/artifact deletion still require
  explicit owner authorization; no rewrite can recall third-party clones or caches.
- Register a project by writing `dist/<slug>/work/paper.json`, never per-project tool constants.
  Slugs match `^[a-z0-9]+(?:-[a-z0-9]+)*$`, not Chinese titles.
- Original source-code analyses are not PDF/web translations. They may retain `work/meta.json`
  with the inspected local repository and exact commit, section Markdown, and a local
  `work/rebuild.py` that uses the shared builder. Do not invent a PDF/web manifest merely to
  register an analysis. Do not copy external repositories wholesale by default. Owner-requested
  relocation may move an existing checkout into ignored `repos/<repository>/`, preserving
  its independent Git history, uncommitted files and license. Never stage or publish that tree;
  update canonical path metadata without changing the inspected commit. Keep experiments in TEMP.
- Keep authored local-only material intact when changing the pipeline. Migration authorization
  permits relocation and path metadata updates, not rewriting translations or figure images.

## Survey conventions

- Self-authored reviews organize evidence and explanations by topic. Retain accurate source
  attribution, distinguish reported findings from original analysis, and do not copy paper text.
  New scopes and publication require explicit owner direction; unreviewed drafts remain local.
- `tools/survey.py` is a legacy, direction-agnostic builder separate from the paper builder.
  Its inputs use `survey/papers/<slug>/{meta.json,abstract.md}` and hub `{{paper:<slug>}}`
  markers, never tool constants. The schema describes compatibility, not an instruction to
  create or restore a dataset. Do not modify or publish existing `survey/` source material
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
