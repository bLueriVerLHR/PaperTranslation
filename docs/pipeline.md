# 工具、接口与发布

本文合并了流水线接口与发布流程：目录与数据模型、写作 skill 的入口、Pages 内容导出与校验、以及任务工作流的检查边界。本地执行工具位于仓库之外的流水线目录，仓库只保留文档、技能与渲染资源。

## 本机当前形态（与下文冲突时以本节为准）

- 仓库保存源文档、页面组成与技能：`papers/<slug>/`（`meta.json`、`content/*.md`、`assets/figures/`、`reader.json`、`glossary.md`、`reader-meta.md`）、`src/`（模板、样式、脚本）、`docs/`、`.agents/skills/`。
- 渲染、抽取、校验与发布在 `%TEMP%\PaperTranslationWork\pipeline\` 执行。该目录用目录联接把仓库的 `src/` 与数据根的 `dist/`、`repositories/` 挂进去。
- 渲染一篇页面：`python "$env:TEMP\PaperTranslationWork\pipeline\tools\dev.py" run -- "$env:TEMP\PaperTranslationWork\pipeline\tools\render.py" --work "<仓库>\papers\<slug>" --out "<数据根>\dist\<slug>" --library-root "<数据根>\dist"`。输出与发布版本逐字节一致。
- 发布使用 GitHub Pages 的分支部署：Source 选 `pages-content`、目录 `/ (root)`。仓库里没有 `.github/workflows`，也没有 CI 校验；导出、字体子集化、`--check` 与 `pages_verify` 全部在本地执行后再推送。发布脚本需要 Git 远端，用 `PT_REPO` 指定仓库根。
- 下文描述的工具名、参数与接口仍然有效；它们的执行位置、命令前缀与部署方式以本节为准。



<!-- merged from architecture.md -->

## What this repository is

A small, reproducible pipeline that turns a research paper into an offline-readable HTML page
in Simplified Chinese. HTML-first screen-layout guidance belongs to [reader.md](reader.md);
browser print styles do not define the screen reading width. It is deliberately not a general
translation engine: translation is authored by an agent one section at a time, while the pipeline
guarantees that the mechanical
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
Actions performs that composition from main at deployment, without publishing new prose.
The builder and explicit runtime refresh also share `tools/source_cards.py`: a bounded,
idempotent compatibility adapter for complete fixed-version excerpt captions. It checks
permalink/locator/line-count agreement and retains the original code subtree; it does not
fetch source, infer missing metadata or introduce a new manuscript directive. See
[reader.md](reader.md#compact-source-code-presentation) for the presentation contract.
Adding a paper therefore means
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
and header-only reading notes remain in `work/reader.json` and `work/reader-meta.md`.
An opt-in `show_glossary` profile renders the reader-facing `work/glossary.md` in the title's
source notes, not in manuscript sections or the body TOC. It is a hashed `reader_inputs`
dependency, never a duplicate terminology source. Authoring instructions and chapter-title
maps belong in non-rendered maintenance files, not this glossary. See [reader.md](reader.md).

Each project has an independent slug, section inventory, source directory and `index.html`.
Sharing the reader runtime does not merge manuscripts or require an aggregate survey hub.
Nested source readers can pass an explicit `library_root` to the shared builder; output must
remain inside that root. Runtime references are derived from the actual page depth, while
figures stay beside their reader. Canonical translations retained as research sources are
not original review prose and do not inherit publication approval from their parent project.
Use explicit local-only flags in the canonical reader profile and generated manifest for
unapproved drafts; presentation kind does not establish publication approval.
Evidence organization, source comparison and review procedures for original reviews are
specified in [review-method.md](method.md); these research notes are separate from
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
dist/<slug>/work/content/NN-name.md             per-section Markdown, selected renderer's math syntax
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

## Document renderer boundary

`work/reader.json` may select `"renderer": "pandoc"`; omitted/`python-markdown` preserves the
existing parser. Both use `tools/build.py`, canonical section includes, the page template,
shared runtime and publication boundary. The optional Pandoc executable owns document syntax,
math conversion, figures, tables, footnotes and highlighting. `tools/pandoc.py` only groups
inputs for one conversion and adapts fragments/headings to the existing reader interface;
it does not implement another Markdown parser or a general plugin system. The manifest records
Pandoc's actual version, which contributes to the content hash.

Header notes/glossary and body chapters share one conversion namespace; generated endnotes
follow the last chapter. Explicit author headings remain body structure instead of triggering
legacy metadata/contents heuristics. See [Markdown authoring](reader.md) for selection,
source syntax, dependency setup and limitations. No existing manuscript is silently switched.
The parser-specific decisions below describe the Python-Markdown compatibility path.

## Key decisions

**MathML instead of runtime LaTeX or images.** The destination format is a mobile-friendly HTML
page, so existing content files author MathML directly; the explicit Pandoc path can instead
convert documented mathematical source syntax during building. Browsers render
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
translation keeps the links the original wrote between its parts — “继续阅读第 1 部分……”,
“上一部分”, “术语表” — and those URLs leave a page built to open from `file://` without a
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
expansion. Dependencies enter the content hash and manifest. Coverage checks use the same
expansion for structural markers and language scanning; passing these checks is not semantic
review. See [source-analysis.md](method.md)
for syntax, source excerpt provenance and design-comparison requirements.

**CJK-safe heading anchors.** The stock `toc` slugify in python-markdown strips non-ASCII
characters, which would collapse every Chinese heading to an empty anchor. `tools/build.py`
registers a slugify that keeps `\w` (which includes CJK) and falls back to `section`.

**Offline fonts and Pages fonts are separate.** The shared stylesheet requests installed
Times New Roman, Source Han Serif SC and Maple Mono, with system fallbacks. Default offline
builds and optional packed files contain no downloaded fonts. The authorized Pages export
adds self-hosted OFL WOFF2 faces from hash-pinned sources, including a Times-compatible
Tinos fallback for phones and a dedicated Paper Math face. Text/code faces are used-glyph
subsets; math retains complete glyph/feature coverage and its OpenType MATH table. Font
binaries never enter main; original licenses accompany the renamed faces on pages-content.
See [pages.md](pipeline.md#fonts) for the publication and conversion steps.

**Highlighting is offline.** Explicit-language Markdown fences receive Pygments token
spans at build time while retaining their `pre/code` and language classes. Unknown languages
remain escaped plaintext; shared CSS uses the reader's light/dark palette. No runtime
highlighter or network resource is loaded. Existing semantic pseudocode classes
(`alg-keyword`, `alg-comment`, …) remain supported.

**Code and mathematics use different font paths.** The monospace stack includes CJK fallbacks
for code comments. MathML uses a dedicated math font: installed faces offline, the pinned
renamed face on Pages. Missing glyphs are not permission to change mathematical meaning.

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
| A translated section repeats the source's own table of contents | `build.py`'s `_DropBodyToc` preprocessor removes a heading that introduces a list of headings, so the folded TOC is the only one and the section headings it was burying become navigation entries again |
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

`tools/dev.py` owns the portable external-venv, pip setup and child-process environment;
see [setup and commands](../README.md#setup). Python/pytest/ruff/pip caches, task presets,
reports, logs and experiments live under system TEMP, not beside source code. Its JSON
`project_temp` identifies the `tasks/`, `reports/` and `scratch/` directories; paths must be
absolute. The Windows adapter delegates to Python and exposes the legacy `$Python` and
`$ProjectTemp` variables without duplicating the environment policy. The harness's `.pi/tasks` is a
junction whose target is in system TEMP. These locations are disposable, unlike retained
`dist/<slug>/work/` inputs and references. Legacy ignore entries are safeguards only, not
active storage rules. Migration recovery archives in TEMP are not permanent source locations.


<!-- merged from authoring-skills.md -->

Skills 把现有规范连接成可执行的任务入口，不增加第二套写作标准，也不是文章模板。
它们适用于本项目的规范 Markdown → 原生 MathML／共享资源 → 离线 HTML 流程；不依赖云文档、
文献付费服务或第三方安装脚本。文体、证据、源码与归属规则仍分别由
[写作规范](writing.md)、[综述方法](method.md)、[源码规范](method.md)
和 [工作流](pipeline.md) 维护；使用 Skill 不免除完整阅读适用规范。

## 选择入口

| 请求 | Skill | 不应误用为 |
| --- | --- | --- |
| 原创技术章节、技术方案、源码书稿及其中文精修 | [chinese-technical-writing](../.agents/skills/chinese-technical-writing/SKILL.md) | 给现有译文补写论证或机械套架构模板 |
| 论文／随笔／RFC／技术文档的原文对照翻译与译文精修 | [technical-translation](../.agents/skills/technical-translation/SKILL.md) | 重组原作、统一论文腔或展示译者工作记录 |
| 多来源原创综述、研究脉络、方法与证据比较 | [technical-review](../.agents/skills/technical-review/SKILL.md) | 逐篇摘要列表、市场预测模板或实验执行许可 |

“润色中文”不是一种独立体裁：已有译文走翻译入口，原创综述走综述入口。
源码分析可以是原创章节，也可以是综述的一部分，两者都完整加载源码规范。
混合任务先确定各段身份，不把三个 Skill 机械串成重复加工的流水线。
一般的工具修复、CSS 修改、发布或引用格式修复不因此变成整篇重写任务。

## 发现与显式调用

项目把便携目录放在 `.agents/skills/<name>/SKILL.md`，不使用被忽略的 `.pi/` 保存共享指令。
名称和目录一致；frontmatter 的 description 说明任务触发条件，详细步骤按需读取。
各 Skill 的文件链接相对于它自己的目录，工具命令从仓库根目录运行。

Pi 支持该位置的项目级发现。新建或修改后，在项目内按需处理项目资源信任提示并执行 `/reload`，
或开启新会话；检查资源诊断与显式命令，不能以文件存在冒充已经加载。
不要为加载项目 Skill 修改全局信任策略。其他支持 Agent Skills 的客户端仍须核对其发现位置。

```text
/skill:chinese-technical-writing 精修指定项目的缓存生命周期一节，保留固定版本摘录，不运行上游。
/skill:technical-translation 对照既有底本校对当前一节，保留随笔语气，不新增章节。
/skill:technical-review 按现有来源比较两类缓存策略，无法对齐的测量条件分别陈述。
```

指令中的“指定项目／当前一节”必须由实际任务提供；若有多个候选而未指定，则先澄清。
未自动触发时可显式调用，不应把关键词命中率当成已验证的写作效果。

## 借鉴的方法与不适配的默认行为

以下是原创适配的来源归属，不是外部 Skill 的安装清单，也不证明用户在其他产品会话里已连接这些工具。
固定版本表示检查过的材料身份，不表示持续跟踪其最新功能。

| 来源 | 采纳 | 不照搬 |
| --- | --- | --- |
| [Anthropic doc-coauthoring](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/doc-coauthoring/SKILL.md) | 上下文准备、分节修订、读者问题检验 | 每节固定访谈与大量脑暴、默认新代理、云文档连接、正文附上聊天记录 |
| [Anthropic skill-creator](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/skill-creator/SKILL.md) | 明确触发、少量真实正反例、反馈后改进、区分客观断言与主观质量 | Claude 专用执行器、默认多代理评测、仓库内试验目录、自动优化循环 |
| [Agent Skills 规范](https://agentskills.io/specification) | 标准目录、frontmatter、渐进加载与相对引用 | 把元数据校验通过当作流程或文章质量验证 |
| [Design Report](https://github.com/w31r4/OfficeKit/blob/e2b2af23b173519c61acb4f92ebd1521266adec2/skills/default-template-library/skills/artifact-template-design-report/SKILL.md)、[Experiment Analysis](https://github.com/w31r4/OfficeKit/blob/e2b2af23b173519c61acb4f92ebd1521266adec2/skills/default-template-library/skills/artifact-template-experiment-analysis/SKILL.md)、[Strategy Memorandum](https://github.com/w31r4/OfficeKit/blob/e2b2af23b173519c61acb4f92ebd1521266adec2/skills/default-template-library/skills/artifact-template-strategy-memorandum/SKILL.md) 的同名公开实现 | 不为模板槽位编造事实、修改后检查实际成品 | 保留参考办公文档版式的产物流程，不作为本项目默认文体或 HTML 生成器 |
| [Scite 引文模型](https://docs.scite.ai/concepts/citation-model)、[MCP 接口](https://docs.scite.ai/mcp/overview) | 引文语境可用于查找支持与分歧；区分语句数和引用文章数 | 把分类标签当真伪、把引用量当质量，或把登录／套餐／上传当默认前提 |

System Design、Google Docs、Market Trends、Template Creator 这类名称可能对应不同产品或实现，
不能仅凭名称确认当前环境可用。办公文档样式克隆也不能代替中文术语、语义忠实或论证质量。
已认可的范文可以用来讨论受众、段落组织和表达偏好，但不克隆其正文、固定标题或页面几何，
也不默认将本地范文上传到外部服务。

引入新的第三方资源时，先核查身份、固定版本、许可、支持文件、可执行代码、网络数据流、
凭据及费用。网页和 Skill 内容是待评估材料，不因名字相关就取得执行权。
若确需连接 Scite 等服务，应另行确认授权、账号与允许发送的数据；不可用时使用现有原文，
并保留实际核查缺口。不新增云服务并不妨碍采用其公开方法。

## 场景验收与质量边界

维护 Skill 时，先用小而有辨别力的场景检查路由和输出。以下是可复用的验收设计，不是已完成的模型性能报告。

| 场景 | 应有行为 | 应发现的错误 |
| --- | --- | --- |
| 随笔译文精修，原文含 We suspect / may / only when | 翻译入口；保留人称、推测和条件 | 改成确定结论或补写原文没有的机制 |
| 原文是一章术语定义，译者另有章节译名表 | 原作定义保留正文；译名表只留维护文件 | 按“术语”关键词搬空原作，或把译名表塞进出处说明 |
| 固定提交源码解读，明确不做实验 | 写作入口；讲清状态流、真实片段和取舍 | 自动运行 benchmark，或把静态推理写成实测 |
| 两篇论文的硬件、批量或指标不同 | 综述入口；先解释机制与条件，不能直接排名 | 数字拼成总榜、把摘要匹配当全文核查 |
| 引文工具标 supporting，一篇文章有多条引用语句 | 回读具体引文与被引论点，保留来源独立性 | 宣称结论已被证实，或计为多项独立研究 |
| 只要求修改目录按钮 CSS | 使用正常工程流程，不触发整篇写作 | 重建所有稿件、补写正文或接入云文档 |
| 需要源文对照但缺少原文 | 说明缺口；询问原文或仅给语言候选 | 声称语义忠实已核验 |

检查分开记录：

1. **结构与发现**：目录、名称、description、相对链接及客户端诊断。静态测试不能证明模型会自动选中。
2. **流程冒烟**：用合成短例逐步执行并对照预期，记录实际产物；自查不能称作独立审校。
3. **语言与研究质量**：人工阅读完整段落及必要来源；保持语义、证据、机制解释和中文可读性。
4. **效果评测**：若要声称改善某一较弱模型，应另设计有无 Skill 的对照、真实任务和人工盲评，
   记录实际模型、输入、产物、失败与费用。未运行就不报告提升率；额外代理调用仍须授权。

固定的合成回归用例可以进入 `tests/`；任务试验、生成稿、抓取响应、评测日志和报告在绝对系统 TEMP，
有用的项目研究证据留在该项目 `work/`。测试或 Skill 的加载不授予发布稿件、上传全文或执行上游实验的权限。


<!-- merged from pages.md -->

## Design

- **`main`**: pipeline, tests, stylesheet/script, font source lock and Actions workflow.
- **`pages-content`**: rendered HTML, recognized public assets, font license notices and
  `site-manifest.json`, plus one deployment workflow bootstrap. No Python/PowerShell pipeline
  scripts, source Markdown, `work/`, PDFs, extraction data,
  local paths from paper manifests, or survey source tree.
- **Actions**: checks out the pipeline from main, validates the separate content branch,
  stages it without `.git` or `.github`, uploads the Pages artifact, and deploys with Pages/OIDC permissions.
  `tools/pages_deploy.py` consumes the uploader's exact artifact ID, validates its name,
  run identity, expiry and size through the single-artifact REST endpoint, then creates one
  deployment using the normal job token and OIDC. It does not trust artifact-list counts
  or rediscover an upload by name. Missing read-only metadata gets a bounded readiness
  check; deployment creation is never automatically replayed. Deployment status is observed
  with a deadline, cancelling only that invocation's own deployment on timeout. The job
  grants `actions: read` plus scoped Pages/OIDC write permissions; credentials are not logged.
  No PAT, third-party hosting or external runtime asset CDN is required. The same workflow
  bootstrap is copied to pages-content because GitHub push events load workflows from the
  pushed branch; the bootstrap always checks out trusted pipeline code from main.
- **Home**: project cards, progressive title search and centered modal cards for detail-page
  links. Each modal scrolls internally, locks background scrolling, and closes by backdrop
  click, close button or Escape; it restores the homepage scroll position and trigger focus.
  Native dialogs trap focus. Without JS/dialog support, a single original details list remains
  accessible. Shared theme and plain relative links are preserved. There is no SPA router or server requirement;
  links work under a repository Pages prefix and with JavaScript disabled.

Publishing derivative works still requires the relevant rights/permissions. The pipeline's
MIT license does not license translations or figures. Source materials remain ignored in main.
Snapshot approval does not establish the original authors' adaptation/distribution permissions.
Review licenses separately and retain required notices.

## Source and publication review

Publication boundaries use project metadata, not a maintained `.pagesignore` list.
Before translating a rights-restricted published article, first seek its corresponding arXiv
preprint and check identity, fixed
version and license. Translate the verified preprint version; cite the published paper for
revisions without reproducing its full text by default. Being a preprint does not itself
authorize adaptation or publication.

Public snapshots still require explicit review and approval. A personal knowledge library on
GitHub Pages is publicly accessible unless the hosting configuration actually restricts it.
Translation-only publication and learning-use notices do not grant extra rights.

**Paper translations are local-only.** The exporter excludes projects registered with
`work/paper.json`, and profiles whose kind is `translation` (also the default when a profile
omits kind), even with an obsolete `"public_export": true`. HTML, figures and conventional
root-level packed `<slug>.html` copies are excluded together. Mark canonical translation
profiles `"public_export": false` as well; no flag grants permission to publish translations.

For other local-only projects, set `"public_export": false` in canonical
`dist/<slug>/work/reader.json`. Generated project `manifest.json` also carries an explicit veto
when appropriate: the legacy survey builder propagates its canonical identity's flag and
defaults to local-only. These metadata fields define export eligibility; they do not record
approval history, deployment status or a current website inventory.

Publication metadata must use boolean flags and unique JSON keys. Duplicate fields or
nonboolean values stop export rather than allowing a later value to override a veto.

These filters are not semantic detection of arbitrary renamed or unregistered HTML copies,
and are not substitutes for reviewing every staged file. Missing/true flags on nontranslation
projects do not grant approval or rights. Changing metadata does not remove an already-live
snapshot; existing historical readers and withdrawals follow the procedure below.

`.gitignore` alone cannot withdraw an existing deployment or tracked historical content.
An already-published withdrawal needs a replacement snapshot and live verification; historical
removal or artifact deletion additionally requires explicit owner authorization. Never silently
rewrite a branch. Third-party clones and caches cannot be recalled by a Git rewrite.

A removal-only release must copy the existing public snapshot, omit the withdrawn trees and
refresh its homepage/inventory, preserving every remaining reader/asset. Do not mix it with
local reader redesigns or newly translated material awaiting publication approval.

Reader presentation, metadata migration and citation mapping are documented in
[`reader.md`](reader.md).

## Mobile reader

17px default prose, relaxed line spacing and ragged-right paragraphs avoid cramped or uneven
phone text. Tool buttons have 44px minimum hit areas. The mobile toolbar occupies its own
sticky row, rather than floating over the title. Font-size preferences and theme persist when
storage is available; TOC access is one tap. Long URLs wrap; tables, display MathML and code
scroll independently without widening the document. Safe-area padding accommodates notches,
reduced-motion preferences are respected, and print still uses A4.

## Fonts

Default offline builds continue to request installed fonts. The Pages exporter adds:

- Chinese: **Source Han Serif SC / 思源宋体 2.003** (regular and bold).
- Code, including Chinese comments: **Maple Mono CN v7.9**, regular/bold/italic/bold italic.
- English: locally installed **Times New Roman** first; **Tinos** as a self-hosted,
  Times-compatible substitute when Times New Roman is absent (usual on phones).
  This is not an identical Microsoft face; no Microsoft font files are redistributed.
- Native MathML: **STIX Two Math 2.13b171**, pinned to commit
  `744a22a4dd626cd14d75728aef34fc8ad7c85db0`, renamed **Paper Math**. Its complete
  glyph coverage, layout features and OpenType MATH table are retained: implicit math
  alphabets, radicals and stretchy assemblies are not determined by visible text alone.

Sources and SHA-256 checksums are pinned in `tools/font-sources.json`. Originals download
only into system TEMP; failed hashes stop the export. Text/code WOFF2 subsets contain actual
used glyphs; Chinese text is split into frequency-ordered chunks, and code fonts contain only
used code characters. The separate math WOFF2 face deliberately retains complete coverage. `font-display: swap` keeps text immediately readable. Files are real, same-origin
assets, not data URIs. Subsets are renamed to respect OFL Reserved Font Names; original
copyright and full SIL OFL 1.1 licenses accompany them in `assets/fonts/`.

The website fetches its own font assets on first load; default local offline readers do not.
There is no service worker/offline-after-first-visit promise. Downloading the complete exported
site still permits local reading.

## First deployment

In GitHub **Settings → Pages → Build and deployment**, set **Source: GitHub Actions**.
Ensure Actions is enabled and the `github-pages` environment allows `main` and `pages-content`
(or all branches). Protect main as desired; do not make pages-content the default branch.

Use an empty absolute TEMP directory to prepare publication:

The commands below do not require PowerShell or shell activation. Run `env` to find the
external `project_temp`; replace `ABS_TEMP_SITE`, `ABS_TEMP_CACHE` and `ABS_TEMP_CHECKOUT`
with actual absolute paths under system TEMP. Choose an unused site directory and build only
explicitly approved original readers before staging. Repeat `--project` for multiple approvals.

```text
python tools/dev.py setup --pages
python tools/dev.py env
python tools/dev.py run -- tools/pages.py --project my-review --out "ABS_TEMP_SITE"
python tools/dev.py run -- tools/pages_fonts.py --site "ABS_TEMP_SITE" --cache "ABS_TEMP_CACHE"
python tools/dev.py run -- tools/pages.py --check "ABS_TEMP_SITE"
```

Inspect `ABS_TEMP_SITE/site-manifest.json` and preview on a phone-sized browser. It enumerates every
page and hashes all public files. The exporter copies only HTML outside private directories
and recognized asset types; it refuses symlinks, non-empty output directories, and non-TEMP
output. Public copies anonymize Windows user-specific repository paths under Documents
as `$LOCAL_REPOS/…`, leaving original prose and exact inspected commits intact locally.
The validator rejects sources, PDFs, unexpected file types, broken/escaping links,
root-relative links and external HTML render dependencies. It never cleans dist.

Then commit/push main normally and publish the reviewed content:

```text
python tools/dev.py run -- tools/publish_pages.py --site "ABS_TEMP_SITE" --push
```

The legacy `publish-pages.ps1 -Site ... -Push` command forwards to this Python entry point.

The helper creates a fresh TEMP checkout based on the remote content branch (or a new,
parentless branch initially), replaces only that disposable checkout's public files, validates
again, commits and pushes without force. It never adds dist to main.

Public text (HTML, CSS, JS, JSON, notices, workflow YAML and SVG XML) is normalized from
CRLF to LF **before** inventory hashes are computed. This finalization is restricted to
validated absolute TEMP snapshots; Git internals, canonical manuscripts and binary assets
are not rewritten. Text must be UTF-8. New text/font stylesheet writers also emit LF directly.
The fresh publication checkout sets local `core.autocrlf=false` and `core.eol=lf`, so Git
stages the already-approved bytes instead of converting them after hashing. No global Git
configuration changes or content-branch `.gitattributes` exception are needed. The verifier's
CRLF/LF allowance remains for older snapshots; newly finalized snapshots should require
zero newline exceptions, with fonts and raster images still byte-exact. Omitting `--push` prepares
a commit for inspection and prints its checkout path. A non-fast-forward push fails safely;
re-run from the latest remote branch rather than forcing.

## Update selected readers without replacing other projects

Use the existing public branch as the baseline; do not export every local reader when only
one project is approved. Both baseline and output are disposable absolute TEMP directories.
The selected project must still pass the normal source/rights eligibility filters.

Read the configured origin with `git remote get-url origin`; substitute that value for
`ORIGIN_URL` and choose a fresh absolute `ABS_TEMP_BASELINE` alongside the output site.

```text
git clone --config core.autocrlf=false --config core.eol=lf --depth 1 --single-branch --branch pages-content "ORIGIN_URL" "ABS_TEMP_BASELINE"
python tools/dev.py run -- tools/pages.py --project my-review --baseline "ABS_TEMP_BASELINE" --out "ABS_TEMP_SITE"
python tools/dev.py run -- tools/pages_fonts.py --site "ABS_TEMP_SITE" --cache "ABS_TEMP_CACHE"
python tools/dev.py run -- tools/pages.py --check "ABS_TEMP_SITE"
```

`--project` can be repeated. The exporter replaces only those project trees in the TEMP
snapshot, updates its homepage/inventory and installs the shared runtime; other project
readers and assets are preserved. It never deletes canonical work or grants publication rights.

## Verify push and selected live files

After `publish_pages.py --push`, the helper verifies the remote content commit against the
approved site automatically. Reuse its printed `Content checkout` path; do not clone again just
to check the same push. For live verification, inspect only the requested paths:

```text
python tools/dev.py run -- tools/pages_verify.py --checkout "ABS_TEMP_CHECKOUT" --site "ABS_TEMP_SITE" --base-url "https://example.github.io/library/" --path "my-review/index.html"
```

The verifier checks Git object bytes, allowing only text CRLF/LF normalization, and requires
binary assets to match exactly. Live verification predicts canonical LF bytes for text
(including legacy CRLF Git blobs), then compares exact HTTP body hashes with normal TLS;
received bodies are not normalized to hide mismatches.
Verification is one-shot, without an Actions API dependency or retry loop. A mismatch after a verified
push may indicate pending deployment: do not repush automatically. Optional detailed evidence
uses `--report` with an absolute TEMP path; default output is a compact summary.

## Updates and limitations

Content changes: rebuild locally, repeat the export/font subsetting, review and push.
Actions cannot rebuild translations absent from main. It composes the explicitly approved
content snapshot with one current `assets/{styles,scripts}/` runtime from main, validates the
result, and deploys from system TEMP. Thus a shared UI fix on main updates every reader without
rebuilding/re-exporting any article or copying code to project folders. Page text, figures and
licensed fonts remain in the approved content snapshot; no new translation is published by a UI push.

Local runtime refresh: `python tools/dev.py run -- tools/assets.py`. To migrate or update a
reader-only TEMP snapshot explicitly, run `python tools/dev.py run -- tools/pages.py
--refresh-shared "ABS_TEMP_SITE"` on one command line. The first migration
rewrites standard resource URLs, removes duplicate generated copies and upgrades complete,
verified-locator legacy source captions into native source cards without changing code.
Already converted cards are unchanged; other prose is not rebuilt or replaced. Later
refreshes update root assets/inventory. The validator rejects reintroduced copies/noncanonical URLs.
Pushes to either branch and manual workflow dispatch deploy the latest approved snapshot.
The deployment is serialized; deployment failure leaves the previous live version untouched.

The content branch's Git history remains public even if a later export removes a page. Never
put a source or sensitive file there. If disclosure occurs, removal in a new commit is not
sufficient; contact the repository owner to plan history cleanup.

Validation: `python tools/dev.py run -- -m pytest`, `python tools/dev.py run -- -m ruff check .`,
`python tools/dev.py run -- -m ruff format --check .`, plus the mandatory exported-site `--check`.
Optional modal browser regressions use Playwright with an installed local Chrome/Chromium,
not a signed-in profile or a downloaded browser. Run `python tools/dev.py setup --browser`
to install the pinned optional package, optionally set `PAPER_BROWSER_EXECUTABLE`, then run
`python tools/dev.py run -- -m pytest tests/test_library_browser.py`. Tests cover 320/390/1280px layouts,
internal scrolling, all three close paths, focus/scroll restoration, detail-title search,
navigation and no-JS/no-dialog fallbacks. They skip when optional tooling is absent.


<!-- merged from workflow.md -->

This is the operational entry point. Content quality belongs to the writing/review standards;
publication boundaries belong to `pages.md`. It does not waive either set of requirements.

## 1. Prepare once for the task

Identify the requested change and its boundary. For manuscript work, read the applicable
standards in full and the complete affected sections, project maintenance notes and terminology.
Keep this preparation for the batch; do not restart it for every question while scope and
standards are unchanged. Read an architecture/schema section only when changing that interface.

Before drafting, classify each affected block as manuscript body, reader-facing header notes,
or non-rendered maintenance material; use the ownership examples in
[chinese-writing.md](writing.md#正文与维护材料的边界). A translation retains its source's
genre and argument. Making terminology visible means source notes, not a new first chapter;
a chapter-title translation map is maintenance data. Do not apply those exclusions to the
source author's own definitions or technical discussion.

Use existing source inventories and local references. Do not regenerate manual coverage
records, rescan unrelated projects, refetch available material or read entire repositories
just to confirm a localized assertion. Canonical work/reference material is not disposable.

## 2. Read content before its representation

- Markdown/text: inspect the complete relevant paragraph or answer with necessary context.
- HTML: use `tools/read_source.py` to remove page chrome and expose prose, code and tables.
  Locate by heading or a literal phrase, then read the relevant blocks. Use raw HTML only for
  math structure, ambiguous extraction or markup/rendering defects.
- JSON/manifests: select the needed key or emit a small summary. Full schema examples belong
  in interface documentation, not repeated working context.
- Code: locate the relevant symbol, then read its complete control flow and required callers.
  A directory/file list is not implementation evidence.

```powershell
. .\tools\dev-env.ps1
& $Python tools\read_source.py C:\path\to\saved.html --outline
& $Python tools\read_source.py C:\path\to\saved.html --find "macro definitions"
& $Python tools\read_source.py C:\path\to\saved.html --start 20 --count 8
& $Python tools\read_source.py C:\path\to\saved.html --id "intrusive_ptr"
```

The view is local and read-only: it does not fetch URLs, execute page scripts or overwrite
snapshots. Blocks are extraction positions, **not source line numbers**. Code whitespace and
MathML structure are retained; SVG/image-only mathematics still needs the original source or
visual inspection. Search, scope selection, suppressed page chrome and output limits are
explicit; an excerpt or extracted view never proves full reading, coverage or correctness.
Increase the character limit or follow the printed continuation when a block is incomplete.

### Reusable evidence lookup

`tools/knowledge.py` uses installed SQLite FTS5, without new packages or network services.
The database is an absolute TEMP cache; canonical snapshots and source identities stay in
`work/reference/` and the independent checkouts. Build it once, then update changed bytes:

```powershell
$DB = Join-Path $ProjectTemp 'scratch\evidence.sqlite'
& $Python tools\knowledge.py --db $DB build --archive dist\my-review\work\reference\technical-docs\index.json `
    --reader dist\my-review\work\reader.json
& $Python tools\knowledge.py --db $DB build --repo repos\cpp-draft --file source/containers.tex `
    --reader dist\my-review\work\reader.json
& $Python tools\knowledge.py --db $DB search "already contains equivalent" --source containers.tex --limit 2
& $Python tools\knowledge.py --db $DB show --doc 12 --block 5 --count 3
```

Source files come from the resolved Git commit, not uncommitted working bytes. `--revision`
can select another local revision. Results distinguish HTML extraction blocks from real
source-line windows and identify partial representations. `--ref` searches only the reference
URL's declared line range or HTML element; missing/unsupported locations fail closed. It does
not infer additional ranges from prose notes or certify claim support. `--linked-ref` is the
explicit broader snapshot/file discovery filter, not an evidence-scope filter. Continue a
scoped result with `show --ref` as printed. Snapshot hashes and commits are identities, not
product editions. Cache migration/parser changes require rebuilding, even for unchanged input
bytes. Search hits do not complete an audit; read required adjoining context, especially code
and math. New dependencies are justified only
by an actual format/lookup gap, not by a preference for building a larger platform.

## 3. Review assertions, not source volume

Work by topic, usually 10–20 questions per batch. For each answer determine:

1. Are all requested subrequirements actually answered, including merged/split mappings?
2. Are the conclusions correct, with version, complexity, concurrency and exception conditions?
3. Does each relevant citation support the adjacent claim rather than merely the topic?

Choose the smallest sufficient evidence path:

| Situation | Evidence path |
|---|---|
| Basic assertion already supported locally | Complete answer plus existing evidence; no new search |
| Condition-sensitive or implementation-specific claim | One directly relevant primary source at a fixed scope/version |
| Genuine disagreement or source/rights ambiguity | Compare the conflicting sources; add another only to resolve the identified gap |

Before searching, state the exact unresolved assertion. A useful default time box is five
minutes per difficult point; if unresolved, record it as pending and continue the batch.
Do not use the time box to mark an unchecked requirement complete. Downloads, hash counts,
candidate matches and document tests are never semantic coverage proof.

Batch the edits and record only the conclusion, stable answer ID, evidence locator and
remaining gap. Reuse verified evidence within its actual scope instead of rereading the same
manual for each related answer. Source identity, reading scope and answer coverage stay separate.

### Record per-question time without new task scripts

`tools/review_log.py` appends actual timestamps to a new absolute TEMP log for each batch.
Mark `prepare`, then each stable `qa-...` ID, then `edit`, `validate` and finally `done`.
The next mark closes the previous interval; revisit an ID if more work is needed. Only mark
`done` after the checks finish. Summary reports keep measured question intervals separate
from equal-share estimates of common editing/checking time; preparation remains separate.

```powershell
$Log = Join-Path $ProjectTemp 'reports\batch-unique.jsonl'
& $Python tools\review_log.py --log $Log mark prepare
& $Python tools\review_log.py --log $Log mark qa-example
# Other questions, then shared edit/check phases; never infer completion from time alone.
& $Python tools\review_log.py --log $Log mark edit
& $Python tools\review_log.py --log $Log mark validate
& $Python tools\review_log.py --log $Log mark done
& $Python tools\review_log.py --log $Log summary --out "$ProjectTemp\reports\batch-unique.md"
```

## 4. Validate at the relevant boundary

| Change | Checks |
|---|---|
| Prose/references | Affected build, anchors, citations and declared coverage expectations; run the typography/terminology triage and read the flagged paragraphs |
| Parser/builder/runtime | Targeted synthetic tests during implementation; full tests/lint/format before commit |
| Interaction/layout | Browser regression on the affected reader or publication candidate |
| Publication | Reader-only export validation, preserved-project comparison, remote commit and selected live files |

Do not rebuild all readers or run the full suite after every answer. Preserve code, formulas,
rights and source conditions when polishing. Engineering results and content-audit results
must be reported separately, with actual failure/partial states.

### Standalone reader check

After a coherent section is revised, inspect it as a reader who has not seen the task dialogue.
Use only the section and its explicit dependencies. Choose a few concrete questions appropriate
to its genre: what is the object, how does the mechanism work, what conditions limit the claim,
and which source supports the conclusion? For a translation, check whether the source author's
meaning and uncertainty survive rather than inventing answers absent from the source.

A missing definition, unsupported transition or dependence on chat context is a revision target.
Fix the canonical prose or its necessary links, not by appending instructions, task history or
an interview transcript. This adapts the reader-testing method cited in
[authoring skills](pipeline.md); self-review is not an independent reader study.
A fresh model/reviewer can be useful only when authorized; availability alone does not authorize
new agents, cloud uploads or additional experiments. Report what was actually checked.

## 5. Publish with maintained entry points

Use the staging/font/push commands in [pages.md](pipeline.md), not a new script for each release.
`tools/pages_verify.py` checks a published TEMP checkout against the approved site, accounting
only for Git text newline normalization; binaries must match exactly. It can check selected
live paths by HTTP hash without inspecting unrelated accounts or querying the Actions API.

```powershell
& $Python tools\pages_verify.py --checkout $Checkout --site $Site
& $Python tools\pages_verify.py --checkout $Checkout --site $Site `
    --base-url "https://example.github.io/library/" --path "my-review/index.html"
```

Verification prints a brief result; detailed machine evidence is optional via `--report`
under system TEMP. A live mismatch may mean deployment is pending: inspect that result,
not the already-successful push. No automatic push, retry loop, weakened TLS or history rewrite
is part of either reading or verification. For authorized GitHub metadata/PR/Actions queries,
prefer an installed and authenticated `gh` CLI to one-off API scripts. For example,
`gh run list --workflow pages.yml --branch pages-content --limit 3` shows deployment runs;
its success does not replace remote or live content checks. Availability does not authorize
pushing, rerunning production jobs or changing account settings.
