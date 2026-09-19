# Architecture

## What this repository is

A small, reproducible pipeline that turns a research paper into an A4-sized HTML reading page
in Simplified Chinese. It is deliberately not a general translation engine: translation is
authored by an agent one section at a time, while the pipeline guarantees that the mechanical
parts — source extraction, layout, math markup and packaging — are deterministic and
re-runnable for every registered paper.

## The published boundary

This repository ships the pipeline only. A translation is a derivative work of the paper it
translates and a figure crop is a verbatim extract from that paper's PDF, so the whole of
`papers/` is `git`-ignored: a fresh clone has the tools and no content. The source PDF, the
per-page rasters, the extracted section text and the finished translation all stay on the
machine that produced them, and `tools/extract.py` rebuilds the mechanical parts from a PDF the
user supplies. That keeps the MIT grant in `LICENSE` honest — it covers code and documentation,
not other people's papers — and it means the figures a page references may not exist yet in a
clone, which is why `build.copy_assets` skips a missing directory instead of failing.

## Papers are data, not code

The pipeline serves any number of papers. Everything that differs between them lives under
`papers/<slug>/`:

```
papers/<slug>/paper.json          identity, source PDF, section map, coverage expectations
papers/<slug>/content/*.md        the translation, one file per section
papers/<slug>/glossary.md         binding terminology for this paper
papers/<slug>/assets/figures/     figure crops (local only, never committed)
```

Everything identical across papers stays shared under `src/`: the page template, the theme and
print stylesheet, and the reader script. Adding a paper therefore means
writing a manifest — no tool changes, no new constants. `tools/paper.py` loads the manifest and
derives every path (`content_dir`, `figures_dir`, `output_dir`, `output_path`, …), so a slug is
the only paper-specific argument any tool takes.

Because the slug is also the deliverable folder name, `paper.load` validates it against
`SLUG_RE = ^[a-z0-9]+(?:-[a-z0-9]+)*$` and raises `PaperError` otherwise. That keeps every
`dist/<slug>/` path an English, ASCII, path-safe folder name (the user's requirement), and it
removes the need for the earlier `safe_filename` helper that sanitised Windows-illegal
characters out of a Chinese title.

The manifest schema:

```json
{
  "title": "文档标题",
  "subtitle": "副标题",
  "author": "作者",
  "source": {"pdf": ".local/source/<slug>/paper.pdf"},
  "sections": [{"name": "00-front", "first": 1, "last": 3}],
  "expectations": {"headings": ["## 摘要"], "figures": [1], "tables": [1], "equations": [1]}
}
```

`sections` drives extraction (printed page ranges of the source PDF). `expectations` drives the
coverage checker (what the finished translation must contain). Both are validated on load, so a
typo fails loudly with the paper and field named.

## Data flow

```
.local/source/<slug>/<paper>.pdf                (external input, not committed)
        |
        |  tools/extract.py --paper <slug>
        v
.local/source/<slug>/pages/page-NN.txt          per-page text, reading order
.local/source/<slug>/pages-png/page-NN.png      per-page raster for formula reading
.local/source/<slug>/sections/*.txt             section-level text
papers/<slug>/assets/figures/figure-NN.png      figure crops (local only, never committed)
        |
        |  authored translation
        v
papers/<slug>/content/NN-name.md                one file per section, MathML inline
papers/<slug>/glossary.md                       shared terminology
        |
        |  tools/build.py --paper <slug>
        v
dist/<slug>/index.html                          reader page (the deliverable)
dist/<slug>/assets/{styles,scripts,figures}/    real files, referenced by relative path
dist/<slug>/manifest.json                       content hash + asset inventory
        |
        |  tools/pack.py --paper <slug> --out <file>      (optional single-file export)
        v
<file>                                          one self-contained file, for mailing a copy
```

## Key decisions

**MathML instead of LaTeX or images.** The destination format is a mobile-friendly HTML
page, so equations are authored as MathML directly in the content files. Browsers render
`<math>` natively, no JavaScript math renderer is loaded, and the markup stays selectable
and accessible. Display equations are wrapped in `<div class="equation">` with a sibling
`<span class="eqno">` so the printed number aligns to the right margin.

**One Markdown file per section.** Translation is a long-running, interruptible process.
Per-section files let a session resume exactly where it stopped, and make terminology
review and diffing tractable. The build concatenates them in filename order.

**CJK-safe heading anchors.** The stock `toc` slugify in python-markdown strips non-ASCII
characters, which would collapse every Chinese heading to an empty anchor. `tools/build.py`
registers a slugify that keeps `\w` (which includes CJK) and falls back to `section`.

**No font is embedded; the browser picks it.** The stylesheet only names font families in
priority order: Times New Roman and metric-compatible serifs for Latin, then Source Han Sans SC,
Noto Sans SC, Microsoft YaHei, PingFang SC and Hiragino Sans GB for Simplified Chinese, and a
monospace chain that ends in the same CJK families for code. Every glyph is resolved from the
reading machine's own fonts, so nothing is downloaded at load time, no font license travels with
the deliverable, and each deliverable is about a megabyte smaller than a bundled CJK subset
would make it. An earlier revision subset Source Han Sans SC with `fontTools`, committed it
under `src/assets/fonts/`, and gated the build on a glyph-coverage check; that was dropped once
exact glyph fidelity stopped being worth the bytes and the vendored license. The trade-off is
that a reader without any listed CJK family gets whatever their system substitutes.

**Highlighting is declarative.** Highlighted pseudocode is authored with semantic classes
(`alg-keyword`, `alg-comment`, …) styled by the committed stylesheet, rather than by adding a
runtime highlighter or a Pygments dependency.

**Glyph substitution for symbols no CJK face covers.** Source Han Sans SC has no glyph
for `⩽` (U+2A7D) or `⊲` (U+22B2), which the DeepSeek source uses inside pseudocode. Those were
replaced with the covered near-equivalents `≤` and `◁`, and `ℝ` with plain `R` inside `<pre>`
blocks. The substitutions stay: a system CJK face is no more likely to carry those code points.
The monospace stack ends with the CJK families so uncommon symbols resolve
to a Chinese face instead of a random fallback. MathML keeps the true `⩽` and `ℓ`, because
math glyphs come from the math font, not the CJK face.

**Inline math convention.** Inline MathML is used whenever the expression has structure
(subscripts, superscripts, fractions, operators); a bare single variable may be written as
`<i>X</i>`. This keeps the content files readable without weakening the output.

**A coverage checker, not hope.** `tools/coverage.py` takes the expectations from the paper
manifest and checks them against that paper's content directory: every section heading, every
figure (the union of the manifest's list and the extractor's report, so a stale report cannot
hide a missing figure), every table caption and every numbered equation must appear, and no
paragraph outside math/code blocks may still be English prose. It exits non-zero, so it can gate
a release.

**A folder, not a base64 blob.** The shipped artifact is a folder per paper, `dist/<slug>/`,
holding `index.html` beside a real `assets/` tree: `assets/styles/reader.css`,
`assets/scripts/reader.js` and `assets/figures/*.png`, all reached by relative path. That is a
reversal of the earlier "one file, not a folder" design, and the reason is cost: base64 inflates
every embedded byte by about a third, makes the images opaque to diffing and browser caching,
and turns each small figure edit into a whole-payload rewrite. As files, the figures are
byte-identical to what `tools/extract.py` produced, the stylesheet and script are readable and
cacheable, and printing `index.html` to A4 still needs no server. The page opens straight from
`file://`, so offline reading is unaffected.

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
write, so a figure dropped from `papers/<slug>/assets/figures/` cannot linger in the shipped
folder and ship an image the page no longer references.

## Failure modes and guards

| Failure | Guard |
|---|---|
| Content uses a CJK glyph the reader's fonts lack | Nothing to guard: glyphs come from the reader's system, and the browser falls back on its own |
| Template placeholder left unresolved | `build()` raises `ValueError` listing the placeholders |
| Figure crop includes body text or clips a label | `tools/extract.py` grows the crop around drawing/image bounds; crops are reviewed once against page rasters |
| A manifest is malformed or a page range is impossible | `tools/paper.py` raises `PaperError` naming the paper and the field |
| A tool is run without a slug while several papers exist | `paper.resolve()` refuses and lists the registered slugs |
| Translation skips a paragraph or equation | `tools/coverage.py` cross-check against the manifest plus `.local/source/<slug>/report.json` |
| Wide table overflows the page on a phone | `build.py` wraps every `<table>` in a scrollable `.table-wrap`; narrow viewports give the table its intrinsic width |
| A display equation keeps a scroll container in print | The print stylesheet sets `.equation { overflow: visible }`, beside the `.table-wrap` rule: otherwise the printer draws a scrollbar over the equation number and clips wide formulas |
| A packed file still references `assets/` | `tools/pack.py` raises `ValueError` listing the uninlined resource references |
| A figure dropped from the sources lingers in the deliverable | `build.copy_assets` removes target files this build did not write; `tests/test_pack.py::test_build_removes_stale_figure_crops` covers it |
| A slug is not a legal English folder name | `paper.load` rejects it against `SLUG_RE` with `invalid paper slug ...` |
| A translation, figure crop or manifest is committed | `.gitignore` ignores all of `papers/`; reviews keep `git ls-files papers` empty, in the tree and in history |
| A font byte or `@font-face` sneaks back into the deliverable | `tests/test_pack.py` asserts the built page and the exported file have neither; `tests/test_build.py` asserts the copied stylesheet has no `@font-face` |
| Base64 payloads creep back into the built page | `tests/test_build.py` asserts the page contains no `base64` and no `data:image`, and that figures are referenced as `src="assets/figures/figure-NN.png"` |
| Absolute paths or machine-specific fonts leak into output | dist references only relative `assets/` paths |
