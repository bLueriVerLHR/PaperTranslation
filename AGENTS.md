# AGENTS.md

Operating manual for coding agents in this repository.

## What this repository is

A writing-standards repository: prose conventions, research and source-code analysis methods,
reader presentation rules, three authoring skills and the reader's templates/styles/scripts.
It contains **no Python, no build scripts, no data and no manuscripts**. Anything executable
lives outside the checkout, under `%TEMP%\PaperTranslationWork\`:

| Path | Content |
|---|---|
| `pipeline\tools`, `pipeline\tests` | Python tools, tests, `pyproject.toml`, dependency pins |
| `pipeline\src` | junction to this repository's `src/` |
| `pipeline\dist`, `pipeline\repos` | junctions to the data root's `dist/` and `repos/` |
| `dist\<slug>\work` | canonical per-project content, glossary, figures and metadata |
| `repos\<name>` | fixed-commit source checkouts used by source-code analyses |
| `sources\` | external originals (papers, books) |

TEMP is disposable and there is no second copy. Never treat `dist/`, `repos/` or `sources/` as
reproducible from this repository, and never delete them as cleanup. Project rebuild scripts
locate the pipeline through `PT_PIPELINE`, a sibling `pipeline/` directory, or by walking up for
`tools/build.py`.

## Publication boundary

The site is published from the `pages-content` branch by GitHub Pages branch deployment; this
repository holds no workflow and runs no CI. Local export, validation and push are documented in
`docs/pipeline.md`. `pages-content` carries rendered HTML, fonts and licence notices only: no
`work/` trees, source documents, extraction data, local paths or pipeline scripts. Translations
and their figure crops remain local-only; public snapshots are explicitly approved original
reviews and source-code books, and they are never published under the MIT licence. Withdrawal
needs a replacement snapshot plus live verification; history rewriting or artifact deletion needs
separate owner authorization.

## Mandatory reading before manuscript work

Read the owning document in full before drafting or revising, and follow it throughout review:

- All manuscript work: `docs/writing.md` for genre, mechanism depth, numbers, terminology,
  typography and paragraph-level review.
- Original reviews and source-code analyses: also `docs/method.md` for source identity,
  claim-to-evidence mapping, fair comparison and implementation analysis.
- Presentation, Markdown syntax, glossaries, question pages: `docs/reader.md`.
- Publishing, directory layout, interfaces, task workflow: `docs/pipeline.md`.

Before changing an existing manuscript, read its canonical `work/README.md`, glossary, source map
and the complete affected sections from the data root.

## Content rules that survive any refactor

- Translate one section at a time in source order; never translate ahead of the source.
- Translations keep the source's genre, voice, argument and qualifications. Original reviews use
  academic prose and organize evidence by topic, not paper by paper.
- Explain mechanisms, their prior constraints, why benefits can arise, and what they cost.
  Separate mathematical properties, explanatory inference and reported experiments.
- Deliver math as native MathML with no runtime renderer; keep real relative files for figures,
  styles and scripts; no `data:` image URIs and no font redistribution in this repository.
- References and author lists are not translated; bibliography data stays local even when the
  reader replaces the visible list with citation links.
- Reader pages stand alone: no cross-project page references; restate a needed conclusion with
  its conditions and cite primary sources.
- Keep authoring instructions, chapter-title maps, batch records and review logs out of rendered
  prose; they belong in maintenance files or task state under TEMP.
- Do not run upstream projects, tests, benchmarks or experiments for research without separate
  explicit authorization. Read-only source inspection and reader builds are distinct.

## Change discipline

- `src/` is the only source of reader presentation. Change styles or behaviour there, never in a
  built page or in a project folder.
- Additive changes keep existing readers buildable. Generated HTML is never committed here.
- Temporary plans, reports, logs and experiments use absolute paths under the managed project
  TEMP; keep no cache directory in this checkout.
- `docs/` describes durable behaviour only: no task progress, approvals or execution history.
  Version changes belong in `CHANGELOG.md`.
