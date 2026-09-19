# Paper Translation Project

This project is initially built for translate papers from websites or pure PDF.

## What this is

A reproducible pipeline that turns a research paper into a single self-contained A4-sized,
offline-readable HTML page in Simplified Chinese, plus the translated papers themselves.

The problem it solves: translating a long technical paper well needs many sessions, consistent
terminology, faithful math, and a layout that survives both a phone and a printed page. Doing
that by hand in one document is error-prone, so each paper's source is split into one Markdown
file per section, the mechanical parts (extraction, MathML, layout, packaging) are
automated, and a coverage checker proves nothing was dropped.

## What this repository publishes

**The pipeline, and nothing that came out of a paper.** Everything under `papers/` derives from
somebody else's work, so none of it is committed:

- no translated text — a translation is a derivative work of the original, and the rights stay
  with its authors;
- no figure crops — they are cut verbatim out of the source PDF;
- no source PDF, no extracted page text and no per-page rasters.

`papers/` is in `.gitignore` and must stay empty in the published repository, so a fresh clone
has the tools and no paper to run them on. Four papers were translated with this pipeline so
far — *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression* (DeepSeek-AI), *A
comprehensive survey and taxonomy of mamba: Applications, Challenges, and Future Directions*
(Miao et al., *Information Fusion* 130, 2026, 104094), *Neural Text Degeneration with
Unlikelihood Training* (Welleck et al., ICLR 2020; preprint 2019) and *On-device large language
models: a survey of model compression and system optimization* (Chen et al., *Artificial
Intelligence Review* 59:191, 2026) — and their content, glossaries, manifests and figures exist
only on the machine that produced them. Read `NOTICE.md` before publishing any
of it.

To translate a paper locally you create `papers/<slug>/paper.json` yourself; the manifest is the
only thing that differs between papers, and `docs/architecture.md` documents its schema.

## Quickstart

```powershell
py -3.14 -m venv .local/venv          # Python 3.12+ works; 3.14 is what the pins are verified on
.\.local\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Neither the papers nor the source PDFs are committed. Each paper's manifest names where it
expects its PDF, under `.local/source/<slug>/`:

```
.local/source/deepseek-v41-flash/DeepSeek_V41_Tech_Report.pdf
.local/source/mamba-survey/paper.pdf
.local/source/unlikelihood-training/paper.pdf
.local/source/on-device-llm-survey/paper.pdf
```

Then, per paper:

```powershell
$P = "deepseek-v41-flash"   # or: mamba-survey, unlikelihood-training, on-device-llm-survey

.\.local\venv\Scripts\python.exe tools\extract.py --paper $P   # PDF -> page text, rasters, figure crops
.\.local\venv\Scripts\python.exe tools\build.py   --paper $P   # content -> dist/<slug>/index.html
```

The deliverable is one folder per paper: `dist/<slug>/index.html` beside a real
`assets/` tree (`assets/styles/reader.css`, `assets/scripts/reader.js`, `assets/figures/*.png`).
Everything is reached by relative path, so the folder can be copied to a USB stick or another
machine and opened by double-clicking `index.html`, with no server. Print the page to get an A4
PDF. The folder keeps figures as ordinary image files rather than base64 payloads, which saves
roughly a third of the bytes and keeps every asset inspectable and cacheable.

If you really need a single file - to mail one attachment, or to open the page on a device that
cannot follow relative paths - fold the folder on demand. This is an export, not the shipped
format:

```powershell
.\.local\venv\Scripts\python.exe tools\pack.py --paper $P --out dist\$P.html
# add --figures-as-files to inline only the CSS and JS and leave figures beside the page
```

Fonts are **not** embedded, in the folder or in an exported file. The stylesheet only names font
families in priority order, so the browser resolves every glyph from the fonts installed on the
reading machine; nothing is fetched and nothing is redistributed. That keeps each deliverable
roughly a megabyte smaller than bundling a CJK subset would, at the cost of exact glyph
fidelity. See `NOTICE.md` for the font policy.

## Quality gates

```powershell
.\.local\venv\Scripts\python.exe -m pytest                      # unit tests
.\.local\venv\Scripts\python.exe -m ruff check .                # lint
.\.local\venv\Scripts\python.exe tools\coverage.py --paper $P   # every section/figure/table/equation present, no English prose left
```

## Repository layout

| Path | Purpose |
|---|---|
| `papers/<slug>/paper.json` | The manifest: title, author, source PDF, printed section map, coverage expectations (local only) |
| `papers/<slug>/content/*.md` | The translation, one Markdown file per section, source of truth (local only) |
| `papers/<slug>/glossary.md` | Binding terminology table shared across that paper's sections (local only) |
| `papers/<slug>/assets/figures/` | Figure crops extracted verbatim from that paper's PDF (local only) |
| `src/templates/`, `src/styles/`, `src/scripts/` | Page template, theme/print CSS, reader enhancements (shared) |
| `src/templates/survey-*.html`, `src/survey/survey.css` | Survey hub/detail templates and survey styling (shared) |
| `tools/paper.py` | Manifest loading and every path derived from a paper slug |
| `tools/` | `extract.py`, `build.py`, `coverage.py`, plus `pack.py` for the optional single-file export and `survey.py` for the survey |
| `survey/` | Survey source: narrative, one folded paper per surveyed work, and the `curation/` provenance and audit scripts (local only) |
| `dist/survey/` | Survey deliverable folder (generated, ignored) |
| `tests/` | pytest suite, including a sample fixture that exercises every rendering path |
| `docs/` | Architecture and design notes |
| `dist/<slug>/` | Per-paper deliverable folder (generated, ignored) |
| `.local/` | Isolated venv and source PDFs (ignored) |

Every `papers/` row above is `git`-ignored on purpose and never published; see `NOTICE.md`. The
`survey/` rows are ignored for the same reason.

Adding a paper means creating `papers/<slug>/paper.json` with its title, source PDF, section
map and expectations; no tool code changes. The slug is also the deliverable folder name
`dist/<slug>/`, so it must be a lowercase English identifier — the Chinese title lives in the
manifest's `title` field, which is only used for display.

## The survey

`tools/survey.py` is a second product with the same reader styling. Where `build.py` renders one
translated paper, the survey renders one **narrative** that puts many papers in context, with a
detail page for each surveyed work. The local survey covers seven directions: machine-learning
systems, long-context architectures (including linear attention), on-device, distributed,
multimodal, VLA and Agent applications. Each direction starts with production problems,
explains mechanisms and trade-offs, and links representative papers with translated abstracts.

```powershell
.\\.local\\venv\\Scripts\\python.exe tools\\survey.py     # survey/ -> dist/survey/
```

The deliverable is `dist/survey/index.html` plus `dist/survey/papers/<slug>.html` and an asset
tree, using the same offline relative-path rule as a paper folder. Directions are declared in
`survey/survey.json`; adding a direction requires prose and paper folders, not tool changes.

Source layout:

| Path | Purpose |
|---|---|
| `survey/survey.json` | Title, subtitle, author and the direction list |
| `survey/hub/NN-*.md` | The narrative, in reading order; a line `{{paper:<slug>}}` expands to that paper's card |
| `survey/papers/<slug>/meta.json` | Metadata: titles, authors, venue, year, stage, citations with an "as of" date, links, motivation, approach, notes |
| `survey/papers/<slug>/abstract.md` | Translated original abstract |

The card on the hub and the detail page are both rendered from `meta.json`, so the short and
long forms of one paper cannot drift apart. The build fails loudly if the narrative references a
paper that has no folder, or if a surveyed folder is never referenced — nothing can be silently
orphaned. Surveying another paper means adding one folder and one marker; the tool is
direction-agnostic by design. Repeated cards have unique anchors across sections, but share a
single detail page and navigation entry. Detail-page notes distinguish editorial caveats from
the translated abstract. The content hash covers identity, metadata, narrative and abstracts;
stale generated detail pages are removed on rebuild.

Verified citation counts carry a date (`cites_asof`) and source (`cites_source`). Missing counts
are stored as `null` and shown as unverified, never silently converted to zero. A verified zero
is displayed explicitly. Abstracts are checked against primary sources; version-specific links
and editorial notes can record differences between preprints and proceedings. New preprints
are distinguished from established work rather than ranked by invented citation counts.

Like `papers/`, the whole of `survey/` is local-only and never committed: the prose is ours, but
the translated abstracts are derivative works, and the two are interleaved in the same files.

## Destination Format

- A HTML page with A4 paper size.
- Pure reading experience with light/dark mode.
- Equations and formulas are written in HTML not latex for adapting mobile view.
- Default font for alphabet is Times New Roman.
- Codes and pseudo codes using monospace font with syntax highlights.
- Chinese font use Source Han Sans, Noto Sans SC, Microsoft YaHei or PingFang SC, whichever the
  reader has installed first. Nothing is embedded or downloaded at page load.
- Citations, Reference, Acknowledgement and format stuffs are not needed to be translated.
- Need a table of content which is folded by default.

If you find anything missing and need an installation, make list and the user will install it in
the best way. Keep isolation environment.

## While Translating

- Translate sections one by one, step by step avoiding translate as a whole.
- You are allowed to fix previous mistakes if new evidence appears in the following contents.
- Do not spoil.
- Follow the tongue.

## Licensing

Everything committed here — the pipeline under `tools/`, the tests, the template, styles and
script directories, and the documentation — is MIT-licensed; see `LICENSE`. The translated text
and the figures this pipeline produces are **not** part of the repository and are **not**
covered by that grant: they reproduce material from the original papers and remain the rights
holders' property. Read `NOTICE.md` before redistributing anything.
