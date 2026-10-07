# Paper Translation Project

A Python pipeline for A4-sized, offline-readable Chinese HTML: PDF/web extraction,
native MathML, modular Markdown, shared reader assets, citations and optional question banks.
Translations are authored in source order; original reviews and source-code books use the
same reader without inventing a PDF manifest.

## Publication and source boundaries

- `main` contains tools, tests and documentation only.
- Approved **original reviews and source-code books** can publish reader-only snapshots on
  `pages-content` and GitHub Pages. Paper translations and their figure crops remain local-only.
- `dist/`, `/survey/` and owner-approved `repos/` checkouts are ignored. Never force-add them.
- `work/` is canonical rebuilding material, not a cache. **Never clean the project by deleting
  `dist/`**, and do not copy external source PDFs into the workspace.
- The pipeline MIT license does not license papers, crops or upstream code quotations.
  Attribution and permission are separate from export eligibility; see [NOTICE.md](NOTICE.md).

## Setup

Python 3.12+ is required; dependency pins were verified on Python 3.14.

```powershell
. .\tools\dev-env.ps1 -CreateVenv
& $Python -m pip install -r requirements.txt
```

In each subsequent PowerShell session, run `. .\tools\dev-env.ps1` and use `$Python`.
The helper places the environment and caches under system TEMP and provides `$ProjectTemp`:
`tasks/` for plans, `reports/` for evidence and `scratch/` for experiments. Recreate the environment
if TEMP is cleared; never keep the only copy of useful source material there.

## Quick commands

Register PDF/web projects with `dist/<slug>/work/paper.json`; use lowercase English slugs.
`--paper` is required when several projects are registered. Extraction reads the external
original in place; rebuilding needs only the retained work materials.

```powershell
$P = "my-paper"
& $Python tools\extract.py --paper $P --pdf C:\path\to\original.pdf
& $Python tools\build.py --paper $P
& $Python tools\coverage.py --paper $P
& $Python tools\assets.py                 # refresh the shared runtime, not article prose
& $Python tools\pack.py --paper $P --out dist\my-paper.html  # optional single-file export
```

A source-code book instead uses its canonical `work/meta.json`, sections and local
`work/rebuild.py`, which calls the shared builder. The legacy survey builder is separate:
`& $Python tools\survey.py`. Its schema is compatibility documentation, not a request to
create or restore a dataset.

Open the generated `index.html` directly. A portable folder copy includes the selected
reader/figures and the sibling `dist/assets/` runtime. Default readers use installed fonts,
real relative files and no runtime math/highlighting service. The optional packer can inline
assets; Pages uses separately licensed, hash-pinned font subsets.

## Layout

```text
dist/<slug>/index.html             generated reader
dist/<slug>/assets/figures/        reader-specific figures
dist/assets/{styles,scripts}/     one shared runtime
dist/<slug>/work/
  paper.json or meta.json         canonical identity and inspected version
  content/                       canonical sections and included subdocuments
  glossary.md                    binding terminology
  reader.json, reader-meta.md     citation/presentation metadata and rights notes
  assets/figures/                 retained rebuild figures
  reference/                     useful local source material and research records
src/                             shared templates, styles and scripts
tools/                           pipeline and maintenance entry points
tests/                           synthetic fixtures and regression tests
repos/                           ignored, independently versioned source checkouts
survey/                          ignored legacy survey inputs
```

Rebuilds preserve `work/`; do not hand-edit generated HTML or figure crops. External source
checkouts retain their own Git history, modifications and upstream licenses. Experiments and
build directories belong in TEMP, not in those checkouts.

## Choose the task, then the document

Start with [the task workflow](docs/workflow.md), not the entire documentation directory.
[docs/README.md](docs/README.md) routes to the specific authoring, schema, reader or publication
specification. Writing standards still apply in full to the relevant manuscript task.

- Content review: reuse local sources, inspect complete answers and check only the disputed
  claims. A download, source count or passing structural test is not semantic coverage.
- HTML research: use the bounded readable view described in the workflow before raw markup.
- Code changes: see [CONTRIBUTING.md](CONTRIBUTING.md); agent safety rules are in [AGENTS.md](AGENTS.md).
- Publishing: follow [docs/pages.md](docs/pages.md). Stage approved readers in TEMP, validate,
  and push normally; do not rewrite history or publish local revisions without authorization.

## Pipeline checks

```powershell
& $Python -m pytest
& $Python -m ruff check .
& $Python -m ruff format --check .
```

Synthetic tests work without local papers. Optional browser tests use an installed isolated
Chrome/Chromium, not a signed-in profile. Build/coverage/browser checks validate their stated
engineering scope, not the correctness of every technical answer or upstream performance.
