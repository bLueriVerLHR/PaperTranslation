# AGENTS.md

Operating manual for coding agents in this repository.

## What this repository is

A library of reader sources, page composition and writing standards. `papers/<slug>/` holds each
reader's Markdown, figures and metadata; `src/` holds the templates, styles and scripts that turn
them into a page; `docs/` holds the standards and ` .agents/skills/` the authoring entry points.
Rendering, testing and publication run from an external temporary pipeline; this checkout stays
usable without it, and generated output never lands here.

| Path | Content |
|---|---|
| `pipeline\tools`, `pipeline\tests` | renderer, extractor, publication scripts, tests |
| `pipeline\src` | junction to this repository's `src/` |
| `pipeline\dist`, `pipeline\repositories` | junctions to the data root's `dist/` and `repositories/` |
| `dist\<slug>` | rendered pages built from `papers\<slug>` (disposable output) |
| `dist\<slug>\work\reference` | extracted third-party text and page rasters (local only) |
| `repositories\<name>` | fixed-commit source checkouts used by source-code analyses |
| `sources\` | external originals (papers, books) |

TEMP is disposable and there is no second copy of it. `papers/` and `src/` are the reproducible
part; `dist/`, `repositories/` and `sources/` are not, so never treat them as rebuildable from this
repository and never delete them as cleanup. Project work directories under `dist/<slug>/work`
keep only local reference material once the sources moved to `papers/`.

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

Before changing an existing manuscript, read its `papers/<slug>/README.md`, glossary, source map
and the complete affected sections in `papers/<slug>/content/`.

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

## Source, composition and rendering

- `papers/<slug>/` is the canonical source of a reader: `meta.json` declares title, genre and
  section order; `content/` holds one Markdown file per section; figures are real files under
  `assets/figures/`. Rendering reads only these paths.
- `src/` is the only source of reader presentation. Change styles or behaviour there, never in a
  built page or in a project folder.
- Rendering, extraction, checks and publication are executed from the external pipeline. A change
  here must not assume a local tool path exists; document the command in `docs/pipeline.md`
  instead of relying on one machine's layout.
- Generated HTML is never committed to this repository.
- Additive changes keep existing readers buildable. A source tree must stay self-describing:
  `meta.json` lists every section in order, and every referenced figure exists as a relative file.
- Temporary plans, reports, logs and experiments use absolute paths under the managed project
  TEMP; keep no cache directory in this checkout.
- `docs/` describes durable behaviour only: no task progress, approvals or execution history.
  Version changes belong in `CHANGELOG.md`.
