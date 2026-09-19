# Contributing

## Environment setup

```powershell
git clone <repo-url>
cd PaperTranslation
py -3.14 -m venv .local/venv          # Python 3.12+ works; 3.14 is what the pins are verified on
.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Source PDFs are not committed. Each paper's manifest records where it expects its PDF; place
them under `.local/source/<slug>/` before running `tools/extract.py`:

```
.local/source/deepseek-v41-flash/DeepSeek_V41_Tech_Report.pdf
.local/source/mamba-survey/paper.pdf
.local/source/unlikelihood-training/paper.pdf
.local/source/on-device-llm-survey/paper.pdf
```

## What must never be committed

The published repository is the pipeline only. A translation is a derivative work of someone
else's paper and a figure crop is a verbatim extract from it, so `papers/` is `git`-ignored:
no manifest, no `content/*.md`, no `glossary.md`, no `assets/figures/`, and no extracted page
text or rasters. Work in `papers/<slug>/` freely â€” it stays on your machine â€” and check that
`git ls-files papers` is empty before you push. `.local/` holds the source PDFs and is ignored for
the same reason. If you publish a translation of your own, get the rights holder's permission
first; see `NOTICE.md`.

## Workflow

1. Pick or open a task in `.tasks/` (local only, not committed).
2. Create a branch: `feature/<short-description>` (Conventional Branch 1.1.0).
3. Translate/edit one section file under `papers/<slug>/content/` at a time, updating
   `papers/<slug>/glossary.md` when new terminology is introduced.
4. Build and inspect: `.\.local\venv\Scripts\python.exe tools\build.py --paper <slug>`, then
   open `dist/<slug>/index.html`. The built folder is the deliverable: `index.html` beside a
   real `assets/` tree, with no base64 payloads. `tools/pack.py --out <file>` is an opt-in
   single-file export for mailing one attachment, not the shipped format.
5. Run tests: `.\.local\venv\Scripts\python.exe -m pytest`.
6. Commit with Conventional Commits, e.g. `fix(print): stop clipping wide equations`.

Only pipeline changes are committable. A commit that adds translated content, a figure crop or a
manifest is a mistake: `papers/` is ignored, and the tests that read it skip when it is absent,
so the suite stays green in the published clone.

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
- Only pipeline changes are accepted upstream. Do not open a pull request that adds translated
  content, a figure crop or a paper manifest; `papers/` is ignored and `.gitignore` will not be
  relaxed to accept it.
- State what changed, how it was verified, and any terminology decisions.
- CI-equivalent local checks must pass: build, tests, and a clean secret scan.

## Reporting bugs

Open an issue with the paper slug, section/page, the observed rendering or wording, and the
expected result. Attach a screenshot for layout problems.
