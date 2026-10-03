# Contributing

## Environment setup

```powershell
git clone <repo-url>
cd PaperTranslation
. .\tools\dev-env.ps1 -CreateVenv
& $Python -m pip install -r requirements.txt
```

Python 3.12+ works; the pins were verified on 3.14. Dot-source `. .\tools\dev-env.ps1` in each
new session. The virtual environment, Python/pytest/ruff caches and disposable development
state live in system TEMP, not the workspace. Recreate them if TEMP is cleared.

Use `$ProjectTemp/tasks` for plans, presets and development inputs, `$ProjectTemp/reports`
for screenshots/audit evidence, and `$ProjectTemp/scratch` for experiments and trial builds.
Temporary paths must be absolute. The harness's `.pi/tasks` junction stores actual logs in
system TEMP. Legacy ignore entries are defensive denylist rules, not active folder locations.

## Local project materials

Each paper keeps its canonical rebuild inputs in `dist/<slug>/work/`:

- `paper.json`: identity, source kind, sections and coverage expectations;
- `content/*.md`: translated sections in source order;
- `glossary.md`: shared terminology;
- `assets/figures/`: extracted figure crops;
- `reference/`: useful extracted text, page rasters and extraction inventory.

Use `work`, without a leading underscore. Do not delete `dist/` as a cleanup step, and do not
maintain a parallel copy of the same project inputs elsewhere in the workspace. Rebuilds
preserve `work/` and update `index.html`, `manifest.json` and published `assets/` in place.
Source PDFs are external originals, not files to copy into a project folder. Re-extract with
`& $Python tools\extract.py --paper <slug> --pdf C:\path\to\original.pdf`. A manifest can use
`"source": {"pdf": null}` when no original path is retained; building does not require a PDF.

## What must never be committed

The main branch is the pipeline only. A translation is a derivative work, and figure
crops and extracted source are someone else's material. Keep the entire `dist/` tree ignored,
including `work/`, and ensure `git ls-files dist` is empty. Never force-add project materials
or relax ignore rules to publish them. Get rights-holder permission before redistributing a
translation or figure; see `NOTICE.md`.

The local survey source remains under `survey/`. Narrative and translated abstracts are
interleaved, so the whole tree is ignored. Keep `git ls-files survey` empty too.
`src/survey/survey.css` is tracked; the ignore rule must stay anchored (`/survey/`).

## Workflow

1. Initialize the external environment and open a task under `$ProjectTemp/tasks`.
2. Create a branch: `feature/<short-description>` (Conventional Branch 1.1.0).
3. Translate/edit one `dist/<slug>/work/content/` section in source order; keep the glossary
   consistent. Use MathML directly, without a runtime math renderer.
4. Build with `& $Python tools\build.py --paper <slug>` and inspect `dist/<slug>/index.html`.
   Figures, CSS and scripts are ordinary relative-path files. Packing is an opt-in export.
5. Run `& $Python -m pytest`, `& $Python -m ruff format .`, and
   `& $Python -m ruff check .` before committing. Check coverage for the affected paper.
6. Commit only pipeline changes with Conventional Commits, e.g. `fix(print): avoid clipping`.

Do not vendor fonts into main, put base64 images into the default page, edit extracted
figure crops by hand, or translate references and author lists. The authorized Pages export
uses separately licensed, hash-pinned font subsets on `pages-content`; see `docs/pages.md`. Tests using local work skip
when it is absent, so a published clone still tests the pipeline and synthetic fixtures.

## Publishing readers

Reader-only exports to `pages-content` are an explicit, reviewed exception to the main-branch
boundary, not permission to commit any canonical source material. Follow `docs/pages.md`;
check the inventory, local links and absence of source files before pushing. The Pages
workflow validates again before uploading its artifact. Rights-holder permissions and
third-party font licenses remain necessary.

## Adding projects

Create `dist/<slug>/work/paper.json` and section Markdown files. Slugs are lowercase English
identifiers matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`. See `docs/architecture.md` for the schema.
No per-project tool constants are needed.

For the survey, add `survey/papers/<slug>/{meta.json,abstract.md}` and a hub
`{{paper:<slug>}}` marker. Cards and detail pages share metadata; missing and orphaned works
fail loudly. Unverified citation counts remain `null`; verified counts carry `cites_asof`
and `cites_source`. Preserve original translations and verified metadata during tool cleanup.

## Pull requests and bugs

Only pipeline changes are committable. State what changed, how it was verified, and relevant
terminology or rendering decisions. Local checks must pass: tests, lint, format, affected
builds and a clean secret scan. Report bugs with a slug, section/page, observed behavior and
expected behavior; capture layout screenshots under `$ProjectTemp/reports`.
