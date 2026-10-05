# Architecture

## What this repository is

A small, reproducible pipeline that turns a research paper into an A4-sized HTML reading page
in Simplified Chinese. It is deliberately not a general translation engine: translation is
authored by an agent one section at a time, while the pipeline guarantees that the mechanical
parts — source extraction, layout, math markup and packaging — are deterministic and
re-runnable for every registered paper.

## The published boundary

The main branch ships the pipeline only. A separately authorized reader-only export lives
on `pages-content` and is deployed by `.github/workflows/pages.yml`; see `pages.md`.
Canonical work and survey source material are never included in that export. A translation is a derivative work of the paper it
translates and a figure crop is a verbatim extract from that paper's PDF, so the whole of
`dist/`, including retained `work/` materials, is `git`-ignored: a fresh clone has no content. The source PDF, the
per-page rasters, the extracted section text and the finished translation all stay on the
machine that produced them, and `tools/extract.py` rebuilds the mechanical parts from a PDF the
user supplies. That keeps the MIT grant in `LICENSE` honest — it covers code and documentation,
not other people's papers — and it means the figures a page references may not exist yet in a
clone, which is why `build.copy_assets` skips a missing directory instead of failing.

The same rule covers the survey under `survey/`. Its narrative prose is original, but each
surveyed paper's detail page carries a translated abstract, and prose and translation sit
interleaved in the same Markdown files, so the whole tree is ignored rather than a fragile
subset of it. Note the ignore rule is anchored (`/survey/`): a bare `survey/` pattern matches at
any depth and would also swallow the tracked `src/survey/`.

## Papers are data, not code

The pipeline serves any number of papers. Everything that differs between them lives under
`dist/<slug>/work/`:

```
dist/<slug>/work/paper.json          identity, source kind, section map, coverage expectations
dist/<slug>/work/content/*.md        the translation, one file per section
dist/<slug>/work/glossary.md         binding terminology for this paper
dist/<slug>/work/assets/figures/     figure crops (local only, never committed)
dist/<slug>/work/reference/          useful extracted source text, rasters and inventory
```

`work` has no leading underscore. It is the canonical rebuilding source, not disposable output.
Never delete `dist/` to clean a build: update generated page/assets in place, preserving `work/`.
Source PDFs remain external originals and are read in place, not copied into the workspace.

Everything identical across papers stays shared under `src/`: the page template, the theme and
print stylesheet, and the reader script. The output graph is shared too: every paper, analysis,
survey detail and homepage references the one `dist/assets/{styles,scripts}/` tree. No per-project
runtime copies exist. `tools/assets.py` refreshes that tree independently of article building;
`tools/pages.py --refresh-shared` composes the same runtime into an approved public snapshot.
Actions performs that composition from main at deployment, without publishing new prose. Adding a paper therefore means
writing a manifest — no tool changes, no new constants. `tools/paper.py` loads the manifest and
derives every path (`content_dir`, `figures_dir`, `output_dir`, `output_path`, …), so tools
select registered paper inputs by slug rather than per-paper constants.

Because the slug is also the deliverable folder name, `paper.load` validates it against
`SLUG_RE = ^[a-z0-9]+(?:-[a-z0-9]+)*$` and raises `PaperError` otherwise. Folder identity is
ASCII and path-safe; the Chinese title remains a separate metadata field.

The manifest schema:

```json
{
  "title": "文档标题",
  "subtitle": "副标题",
  "author": "作者",
  "source": {"pdf": null},
  "sections": [{"name": "00-front", "first": 1, "last": 3}],
  "expectations": {"headings": ["## 摘要"], "figures": [1], "tables": [1], "equations": [1]}
}
```

`sections` drives extraction (printed page ranges of the source PDF). `expectations` drives the
coverage checker (what the finished translation must contain). Both are validated on load, so a
typo fails loudly with the paper and field named.

A null `source.pdf` records a PDF source without keeping a file path. Building uses the
retained work materials and needs no PDF. Re-extraction requires
`tools/extract.py --paper <slug> --pdf C:\path\to\original.pdf`; alternatively, a manifest may
record the external original's path. Neither extraction nor building copies the PDF.

## Self-authored projects

Original reviews and source-code analyses use canonical `work/meta.json` rather than a
fictional PDF/web `paper.json`. A local `work/rebuild.py` passes project metadata and its own
`work/content/` to `tools.build.build`. Reviews use `kind: review`; analyses use
`kind: analysis` and retain their inspected repository and commit. Presentation profiles
and header-only reading notes remain in `work/reader.json` and `work/reader-meta.md`. An opt-in `show_glossary` profile renders the
canonical `work/glossary.md` before manuscript sections; it shares their TOC and content hash
rather than creating a second terminology source. See [reader.md](reader.md).

Each project has an independent slug, section inventory, source directory and `index.html`.
Sharing the reader runtime does not merge manuscripts or require an aggregate survey hub.
Nested source readers can pass an explicit `library_root` to the shared builder; output must
remain inside that root. Runtime references are derived from the actual page depth, while
figures stay beside their reader. Canonical translations retained as research sources are
not original review prose and do not inherit publication approval from their parent project.
Use explicit local-only flags in the canonical reader profile and generated manifest for
unapproved drafts; presentation kind does not establish publication approval.
Evidence organization, source comparison and review procedures for original reviews are
specified in [review-method.md](review-method.md); these research notes are separate from
reader prose and do not require installation of an external research agent.

## Source kinds: PDF or web page

A paper has exactly one source, named by `source.pdf` or `source.web`; a manifest that names both
or neither is rejected. A web-sourced paper replaces the printed page range with a page URL:

```json
{
  "source": {"web": {"base": "https://example.org/paper/", "index": "https://example.org/search.json"}},
  "sections": [{"name": "00-front", "url": "index"}, {"name": "01-intro", "url": "intro"}]
}
```

`SectionRange.url` may be relative; `WebSource.absolute()` resolves it against `base`. The section
`name` keeps the same `NN-name` shape in both worlds, because it is what `content/*.md` and
`dist/<slug>/work/reference/sections/*.txt` are named, so the build, the coverage checker and the
figure listing do not care where a section came from. `Paper.is_web` and `SectionRange.is_web`
are the only switches: `tools/extract.py` reads a PDF, `tools/web.py` reads a page, and each
refuses the other's paper with a message naming the right tool.

The web extractor writes the same outputs as the PDF one — per-section text plus a `report.json`
inventory — so a new source kind is additive rather than a second pipeline. Two details are
specific to reading a rendered page rather than a PDF:

- **Math is recovered, not transcribed.** The target site pre-renders equations to vector art,
  but the renderer leaves `data-mml-node` on each element and a codepoint on each glyph, so
  walking that structure reconstructs the MathML tree the pipeline needs. Codepoints arrive in
  their styled form, so they are folded back to plain letters and the styling is recorded as
  `mathvariant` — which is what the source LaTeX meant and what a browser renders from a system
  font. No LaTeX parser and no runtime renderer enters the deliverable.
- **Figure payloads are sanitised.** Hand-drawn SVG diagrams can carry an embedded web font and
  the editor's original document in their markup. `sanitize_svg` strips both before a figure is
  written: source figures must not bring their own fonts or editor source data into an export.
- **A strike-out is recovered from the drawn line.** A source page struck through a term with a
  `<line>`, never with a `notation` attribute, so `_strike_notation` reads the two endpoints back.
  MathJax's SVG y-axis points up (the document is wrapped in `scale(1,-1)` to reach screen space),
  so a line whose y increases rises left-to-right and is recorded as `updiagonalstrike`. A
  `menclose` that carries no diagonal line — a box or a circle — gets no notation rather than an
  invented one.

Numbers are assigned by the extractor, not read from the source: a page may show the same asset
on several pages, a figure may carry no caption at all, and a table may have none either. The
counter issues one number per distinct asset (so a repeated diagram keeps a single identity) and
the translation keeps `图 N` bare where the source gives no caption, rather than inventing text.

## Data flow

```
C:/external/original.pdf                       external original, read in place
        |
        |  tools/extract.py --paper <slug> --pdf C:/external/original.pdf
        v
dist/<slug>/work/reference/pages/page-NN.txt    per-page text, reading order
dist/<slug>/work/reference/pages-png/page-NN.png  rasters for formula reading
dist/<slug>/work/reference/sections/*.txt       section-level text
dist/<slug>/work/assets/figures/figure-NN.png   local-only figure crops
        |
        |  authored translation
        v
dist/<slug>/work/content/NN-name.md             one file per section, MathML inline
dist/<slug>/work/glossary.md                    shared terminology
        |
        |  tools/build.py --paper <slug>
        v
dist/<slug>/index.html                          reader page (the deliverable)
dist/<slug>/assets/figures/                    page-specific figure files
dist/assets/{styles,scripts}/                  single shared runtime for the whole library
dist/<slug>/manifest.json                       content hash + asset inventory
        |
        |  tools/pack.py --paper <slug> --out <file>      (optional single-file export)
        v
<file>                                          one self-contained file, for mailing a copy
```

**Papers are data, not code (and so is the survey).** Surveying a paper means adding
`survey/papers/<slug>/meta.json` and `abstract.md` plus a `{{paper:<slug>}}` marker in the hub
prose — never editing `tools/survey.py`, which knows nothing about any particular direction,
paper or count.

## The survey

The legacy `tools/survey.py` supports a narrative with per-work detail pages, using the shared
reader styling. Its direction list and reading order come from input metadata, not a fixed
set of research topics. This schema is distinct from independent self-authored review projects;
it does not require those projects to share a hub, publish translated abstracts or recreate
a particular dataset.

```
survey/survey.json                    title, subtitle, author, declared directions
survey/hub/NN-direction.md            narrative in reading order; `{{paper:<slug>}}` -> a card
survey/papers/<slug>/meta.json        identity, venue, year, stage, citations + "as of" date, links, motivation, approach, notes
survey/papers/<slug>/abstract.md      translated original abstract
survey/curation/                      local provenance scripts: archive primary sources, materialize
                                      metadata, apply verified citations, audit the built site
        |
        |  tools/survey.py
        v
dist/llm-survey/index.html            the LLM hub: prose with inline paper cards
survey/papers/<slug>/meta.json   -->  dist/llm-survey/papers/<slug>.html   detail pages
        + dist/assets/{styles,scripts}/             shared reader.css, survey.css, reader.js
```

The important invariant is that a paper's hub card and its detail page are rendered from the
**same** `meta.json`, so the summary a reader skims and the page they open cannot disagree. The
build also refuses to produce a half-built survey: it raises on a marker whose slug has no
folder, and on a surveyed folder the narrative never references, so nothing is silently orphaned
in either direction. Adding a surveyed paper therefore means adding one folder and one marker.

Two further invariants matter once a paper is referenced more than once. `reading_order`
deduplicates, so the same `{{paper:slug}}` may appear in several sections without creating a
second nav entry or a broken prev/next chain; only the HTML `id` is disambiguated, as
`paper-<slug>` then `paper-<slug>--2`, and both cards still link to the one detail page. And
the content hash covers identity, metadata, narrative and abstracts, so an edit to any of them
changes it; `build` deletes generated detail pages that no longer match a folder.

Choices worth recording:

- **Problem-first, inside each direction.** A direction opens with the production problems that
  motivate it and the methods are grouped by which stage of the pipeline they intervene in. The
  reason this is safe is the deduplication above: repetition, for instance, manifests at inference
  but is addressed in pretraining, post-training and the serving system, so its papers are cited
  from more than one place rather than filed under one.
- **Unknown is not zero.** `cites` is nullable; a paper whose count was not verified renders as
  未核实, and a verified zero renders explicitly. A missing fetch must never read as a claim that
  nobody cited the work.
- **Notes carry the caveats, the abstract carries the paper.** Editorial warnings — a number
  that holds only under matched-quality assumptions, a new preprint whose figures must not be
  multiplied, a conference year that differs between preprint and proceedings — live in
  `meta['notes']` and render in a separate 阅读说明与边界 aside, never mixed into the translated
  abstract.
- **Narrative plus inline cards.** Prose explains the background and mechanism; cards provide
  the corresponding source identity and detail-page link at the relevant point in the argument.
- **Every surveyed paper gets a detail page.** Each metadata record has one detail-page target,
  independent of how often its card appears in the narrative.
- **Citation counts are date-stamped.** `cites_asof` records when the count was read, because a
  bare citation figure is the part of a survey that rots fastest and silently. The API that
  produced it is named in `cites_source`.
- **Provenance is explicit.** Acquisition scripts record the service, matched identity, version
  and retrieval date. Title-search results require identity review; merged and version-specific
  citation counts are not interchangeable. The builder consumes retained metadata without
  depending on a particular live bibliographic API.
- **A 4px accent left border on a card.** Cheap, and it keeps a card visually distinct from the
  prose around it without introducing a second content system.

## Key decisions

**MathML instead of LaTeX or images.** The destination format is a mobile-friendly HTML
page, so equations are authored as MathML directly in the content files. Browsers render
`<math>` natively, no JavaScript math renderer is loaded, and the markup stays selectable
and accessible. Display equations are wrapped in `<div class="equation">` with a sibling
`<span class="eqno">` so the printed number aligns to the right margin.

**An equation is span-level, and `build.py` owns the blank lines.** MathML has no block-versus-inline
distinction of its own — the `display` attribute carries that — but `md_in_html` treats a
block-level tag at the start of a line as the end of the running paragraph, so a `math` that
opens a source line would be lifted out of its sentence and emitted as a sibling block. `math`
is therefore dropped from the parser's block-level set, and `_MathProtection` reconciles the tag
with Markdown's block rules instead: a line holding nothing but an equation whose `<math>` wraps
an `mtable` (or carries `display="block"`) is surrounded with blank lines, so it becomes its own
block, and every other equation rejoins the prose it was written in. A content file never has to
think about blank lines to get its layout right.

The same pass escapes the characters Markdown would otherwise pair into markup. An inline
`<math>` sits in a paragraph's text, so `md_in_html` hands its contents to the inline patterns,
which are free to turn `a*b*c` into emphasis or `[a](b)` into a link. Characters that a rule can
actually pair (`*`, `_`, `` ` ``, `[`, `]`, `|`, `\`) are written as numeric references inside
math — the same character to MathML, no longer a pattern to the parser. The content files keep
writing `64*128*2` and `M[i][j]`, and the escaping happens where the parser can see it.

**One rendered table of contents.** `_DropBodyToc` recognizes a source-body contents list by
shape: a heading followed by a list whose first item is itself a heading. The rendered reader
uses its generated TOC instead of duplicating that list. Lists of plain items remain intact.
This presentation transformation belongs in the shared builder; canonical translated source
retains the original material.

**A cross-reference to the source's own pages is aimed at this page's sections.** A web-source
translation keeps the links the original wrote between its parts — 「继续阅读第 1 部分……」,
「上一部分」, 「术语表」 — and those URLs leave a page built to open from `file://` without a
server. `build.rewrite_source_links` maps every section's source URL (from `paper.json`, via
`source_web.absolute`) to `#sec-<name>` and rewrites only links whose URL names one of those
pages, so a link to the paper's repository or a citation is untouched and a PDF paper — which
has no section URLs — gets an empty map and a no-op. A source-site anchor
(`Part-3#kernel-1`) cannot be translated, because the built page never recorded the source's
heading anchors; such a link lands at the top of the containing section, which is the closest
truthful target.

**Top-level sections with explicit subdocuments.** Per-section files keep translations
resumable; larger original reviews and analyses can use standalone `{{include:path.md}}`
directives to compose focused project/topic subdocuments. Only top-level `content/*.md`
files become sections, in filename order. `tools/manuscript.py` expands relative Markdown
includes inside the content root, rejecting escapes, cycles, missing files and excessive
expansion. Dependencies enter the content hash and manifest. See [source-analysis.md](source-analysis.md)
for syntax, source excerpt provenance and design-comparison requirements.

**CJK-safe heading anchors.** The stock `toc` slugify in python-markdown strips non-ASCII
characters, which would collapse every Chinese heading to an empty anchor. `tools/build.py`
registers a slugify that keeps `\w` (which includes CJK) and falls back to `section`.

**Offline fonts and Pages fonts are separate.** The shared stylesheet requests installed
Times New Roman, Source Han Serif SC and Maple Mono, with system fallbacks. Default offline
builds and optional packed files contain no downloaded fonts. The authorized Pages export
adds self-hosted OFL WOFF2 subsets from hash-pinned sources, including a Times-compatible
Tinos fallback for phones. Font binaries never enter main; original licenses accompany the
renamed subsets on pages-content. See `pages.md` for the publication and subsetting steps.

**Highlighting is offline.** Explicit-language Markdown fences receive Pygments token
spans at build time while retaining their `pre/code` and language classes. Unknown languages
remain escaped plaintext; shared CSS uses the reader's light/dark palette. No runtime
highlighter or network resource is loaded. Existing semantic pseudocode classes
(`alg-keyword`, `alg-comment`, …) remain supported.

**Code and mathematics use different font paths.** The monospace stack includes CJK fallbacks
for code comments. MathML uses a dedicated math font. Glyph availability depends on installed
fonts; do not silently change mathematical meaning to accommodate a missing code glyph.

**Inline math convention.** Inline MathML is used whenever the expression has structure
(subscripts, superscripts, fractions, operators); a bare single variable may be written as
`<i>X</i>`. This keeps the content files readable without weakening the output.

**A coverage checker, not hope.** `tools/coverage.py` takes the expectations from the paper
manifest and checks them against that paper's content directory: every section heading, every
figure (the union of the manifest's list and the extractor's report, so a stale report cannot
hide a missing figure), every table caption and every numbered equation must appear, and no
paragraph outside math/code blocks may still be English prose. It exits non-zero, so it can gate
a release.

**Real files and one shared runtime.** Each `dist/<slug>/index.html` references its own
`assets/figures/` and the library-root `dist/assets/{styles,scripts}/` via relative URLs.
Nested readers use depth-correct URLs to that same root. Figures remain byte-identical to the
retained crops, while shared CSS/JS are independently cacheable. A complete offline copy
includes the reader, its figures and the shared runtime; it opens from `file://` without a server.
Base64 would inflate embedded bytes by about a third and turn a small image change into a
whole-document rewrite, so it is reserved for the optional packer.

For the case where a folder is genuinely awkward — mailing one attachment, or a device that
cannot follow relative paths — `tools/pack.py` folds the folder into one file on demand:
`--out` is required, the stylesheet and reader script are inlined, and figures are embedded as
`data:` URIs. It compares a lossless WebP re-encode against the original and embeds whichever is
smaller, so a tiny PNG stays a PNG. `--figures-as-files` inlines only the CSS and JS and leaves
the images in a sibling `figures/` folder. The packer refuses to write a file that still
contains a non-`data:` resource reference, so a stray `assets/` path fails loudly instead of
shipping a page that silently renders unstyled. Ordinary hyperlinks in the prose are
deliberately left as links, since they cost nothing offline. Fonts are never embedded, in the
folder or in an export.

`build.copy_assets` deletes any file in the target asset directory that this build did not just
write, so a figure dropped from `dist/<slug>/work/assets/figures/` cannot linger in the shipped
folder and ship an image the page no longer references.

## Failure modes and guards

| Failure | Guard |
|---|---|
| A translated section repeats the source's own table of contents | `build.py`'s `_DropBodyToc` preprocessor removes a heading that introduces a list of headings, so the folded TOC is the only one and the section headings it was burying become sidebar entries again |
| A cross-reference to another part of the source leaves the offline page | `build.rewrite_source_links` aims each source-site URL at `#sec-<name>` of the section that now holds it; a link to any other host is left as written, and a PDF paper has no map at all |
| A source-site deep link (`Part-3#kernel-1`) cannot become a page-internal one | Nothing to guess from: the built page never recorded the source's anchor names, so the link lands at the top of the containing section instead |
| Content uses a CJK glyph the reader's fonts lack | Nothing to guard: glyphs come from the reader's system, and the browser falls back on its own |
| Template placeholder left unresolved | `build()` raises `ValueError` listing the placeholders |
| Figure crop includes body text or clips a label | `tools/extract.py` grows the crop around drawing/image bounds; crops are reviewed once against page rasters |
| A manifest is malformed or a page range is impossible | `tools/paper.py` raises `PaperError` naming the paper and the field |
| A tool is run without a slug while several papers exist | `paper.resolve()` refuses and lists the registered slugs |
| Translation skips a paragraph or equation | `tools/coverage.py` cross-check against the manifest plus `dist/<slug>/work/reference/report.json` |
| Wide table overflows the page on a phone | `build.py` wraps every `<table>` in a scrollable `.table-wrap`; narrow viewports give the table its intrinsic width |
| Markdown pairs two characters inside an equation into markup | `build.py` `_MathProtection` writes them as numeric references inside every `<math>` before the parser runs |
| A short label introducing a display equation is justified letter-by-letter | `build.py` `_MathProtection` isolates a lone display equation with blank lines, so it does not merge into the label's paragraph |
| A browser draws no strike-out for a cancelled term | `chromium` implements neither `menclose` nor its `notation`, so `reader.css` draws the diagonal as a gradient across the element's box |
| A display equation keeps a scroll container in print | The print stylesheet sets `.equation { overflow: visible }`, beside the `.table-wrap` rule: otherwise the printer draws a scrollbar over the equation number and clips wide formulas |
| A packed file still references `assets/` | `tools/pack.py` raises `ValueError` listing the uninlined resource references |
| A figure dropped from the sources lingers in the deliverable | `build.copy_assets` removes target files this build did not write; `tests/test_pack.py::test_build_removes_stale_figure_crops` covers it |
| A slug is not a legal English folder name | `paper.load` rejects it against `SLUG_RE` with `invalid paper slug ...` |
| A translation, figure crop or manifest is committed | `.gitignore` ignores all of `dist/`, including `work/`; reviews keep `git ls-files dist` empty |
| A survey card and its detail page disagree | Both render from the same `survey/papers/<slug>/meta.json`; there is no second copy to edit |
| A paper referenced twice gets duplicate HTML ids or two nav entries | `expand_cards` threads a shared counter to suffix only the id (`paper-<slug>` then `paper-<slug>--2`); `reading_order` deduplicates; `tests/test_survey_integrity.py` asserts both |
| A stale generated detail page survives a rename | `survey.build` deletes `dist/llm-survey/papers/*.html` outside the expected set |
| An unverified count is silently reported as zero | `Paper.cites` is nullable; `citation_label` renders 未核实 for a missing count and shows a verified zero explicitly |
| The hub references a paper that has no folder, or a folder is never referenced | `survey.build` raises `SurveyError` listing the orphans, in both directions |
| A survey template placeholder is forgotten | `survey.render` raises `SurveyError` listing the unresolved placeholders |
| A survey stylesheet ships inside a translated paper's `assets/` | `survey.css` lives in `src/survey/`, not `src/styles/`, because `build.copy_assets` copies that whole directory; `tests/test_pack.py::test_build_manifest_lists_the_assets` pins it |
| The survey ignore rule swallows tracked source | The rule is anchored `/survey/`; a bare `survey/` also matches `src/survey/` and would silently drop the survey stylesheet |
| A font byte or `@font-face` sneaks into the default offline deliverable | `tests/test_pack.py` asserts the built page and the exported file have neither; `tests/test_build.py` asserts the copied stylesheet has no `@font-face` |
| Base64 payloads creep back into the built page | `tests/test_build.py` asserts the page contains no `base64` and no `data:image`, and that figures are referenced as `src="assets/figures/figure-NN.png"` |
| A ``` fence renders as an inline code run | `fenced_code` is in `build.make_markdown`'s extension list; `tests/test_build.py` asserts a fence yields a `<pre>` with its language class, including one placed directly under a caption comment |
| A web source downloads an SVG figure the checker does not look for | `tools/coverage.py` matches `figure-NN.<any extension>`, not a fixed `.png` |
| An SVG figure is packed as an unrenderable data URI | `tools/pack.py` maps `.svg` to `image/svg+xml`; a vector figure also skips the ffmpeg re-encode |
| A shared SVG figure ships an embedded font | `tools/web.py:sanitize_svg` strips `<style>` (the only place an SVG `@font-face` can live) and editor metadata, with the element prefix tolerated because editors namespace their tags |
| A manifest names a source that does not exist | `paper.load` raises unless exactly one of `source.pdf` / `source.web` is present, and `tools/web.py` refuses a PDF paper with the name of the tool to use instead |
| Absolute paths or machine-specific fonts leak into output | reader HTML references only relative `assets/` paths; local-only work metadata is not reader output |
| A rebuild cleanup destroys translation sources | update only generated page/assets; preserve `work/`; `test_build_preserves_work_and_rebuilds_without_pdf` covers it |

## Disposable development state

Initialize each PowerShell session with `. .\tools\dev-env.ps1`. The virtual environment,
Python/pytest/ruff caches, task presets, reports, logs and experiments live under system TEMP,
not beside source code. Use `$ProjectTemp/tasks`, `$ProjectTemp/reports` and
`$ProjectTemp/scratch`; temporary paths must be absolute. The harness's `.pi/tasks` is a
junction whose target is in system TEMP. These locations are disposable, unlike retained
`dist/<slug>/work/` inputs and references. Legacy ignore entries are safeguards only, not
active storage rules. Migration recovery archives in TEMP are not permanent source locations.
