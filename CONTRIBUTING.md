# Contributing

## Environment setup

```powershell
git clone <repo-url>
cd PaperTranslation
py -3.14 -m venv .local/venv
.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Source PDFs are not committed. Each paper's manifest records where it expects its PDF; place
them under `.local/source/<slug>/` before running `tools/extract.py`:

```
.local/source/deepseek-v41-flash/DeepSeek_V41_Tech_Report.pdf
.local/source/mamba-survey/paper.pdf
```

## Workflow

1. Pick or open a task in `.tasks/` (local only, not committed).
2. Create a branch: `feature/<short-description>` (Conventional Branch 1.1.0).
3. Translate/edit one section file under `papers/<slug>/content/` at a time, updating
   `papers/<slug>/glossary.md` when new terminology is introduced.
4. Build and inspect: `.\.local\venv\Scripts\python.exe tools\build.py --paper <slug>`.
5. Run tests: `.\.local\venv\Scripts\python.exe -m pytest`.
6. Commit with Conventional Commits, e.g. `feat(content): translate section 2 architecture`.

## Adding a paper

Create `papers/<slug>/paper.json` with the title, subtitle, author, the source PDF path, the
printed section map for extraction, and the coverage expectations. The tools take the slug as an
argument, so no tool code changes; see `docs/architecture.md` for the manifest schema.

## Translation rules

- Simplified Chinese, written technical register; avoid translationese.
- Keep English in parentheses at first mention of a term of art; never translate acronyms.
- Do not translate references, the author list, URLs, model names, or benchmark names.
- Preserve numbers exactly as printed.
- Do not spoil later sections.

## Pull requests

- One section or one pipeline change per pull request.
- State what changed, how it was verified, and any terminology decisions.
- CI-equivalent local checks must pass: build, tests, and a clean secret scan.

## Reporting bugs

Open an issue with the paper slug, section/page, the observed rendering or wording, and the
expected result. Attach a screenshot for layout problems.
