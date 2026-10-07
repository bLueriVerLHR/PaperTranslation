# Contributing

## Start here

Use the environment and commands in [README.md](README.md), then select the relevant path in
[docs/workflow.md](docs/workflow.md). Documentation ownership and task-specific specifications
are indexed in [docs/README.md](docs/README.md); agent constraints are in [AGENTS.md](AGENTS.md).

`main` accepts pipeline changes only. Canonical manuscripts, reference material, external
source PDFs, independent source checkouts and survey inputs are local-only. Never force-add
ignored material, weaken the ignore rules or delete `dist/` during cleanup. Publication is a
separately authorized reader-only operation, not part of an ordinary code contribution.

## Make a focused change

1. Initialize `. .\tools\dev-env.ps1`; use `$Python` and system TEMP for disposable state.
2. Create a focused branch such as `feature/readable-source`.
3. Inspect the affected interface and complete relevant paragraphs. Keep one owner for each
   rule; link to existing specifications instead of copying them into another guide.
4. Change only the requested scope. Preserve source-of-truth content, existing reader builds,
   version/rights notes and verified metadata. No upstream execution is implied by research.
5. Add synthetic regression cases for normal and failure paths. Tests must not depend on
   private manuscripts, live services, authenticated accounts or downloaded browsers.

For manuscript work, read the applicable writing standards in full at the start of the task,
retain the project's terminology and modify canonical Markdown rather than generated HTML.
A batch within that task does not require repeating unchanged preparation for every question.

## Verify and submit

Run targeted tests while implementing; before committing pipeline changes run:

```powershell
& $Python -m ruff format .
& $Python -m ruff check .
& $Python -m pytest
```

Inspect `git diff --check` and the staged paths. `git ls-files dist repos survey` must be empty.
Use Conventional Commits, for example `feat(tools): add bounded source reading`.
Describe the changed behavior, actual checks and remaining limitations in the pull request;
keep run logs and screenshots under `$ProjectTemp/reports`, not in maintained documentation.

Only run affected manuscript builds when the builder/runtime change requires them; do not
rebuild every local reader or run a full suite after each individual answer edit. Check the
appropriate coverage expectations separately from document-engineering tests.

## Reader publication and bug reports

Authorized publication follows [docs/pages.md](docs/pages.md), preserving unmodified public
projects and excluding private sources. Font binaries belong on the content branch only.
A successful push and a verified live update are different results; do not force a rejected
push or repeat a successful push just because deployment is pending.

Report bugs with the affected interface or reader, reproduction, observed/expected behavior
and relevant version. Capture only the necessary evidence; do not attach private source
material, credentials or an entire reference archive.
