# Architecture

## What this repository is

A small, reproducible pipeline that turns a research paper into a single A4-sized HTML reading
page in Simplified Chinese. It is deliberately not a general translation engine: translation is
authored by an agent one section at a time, while the pipeline guarantees that the mechanical
parts — source extraction, layout, math markup, fonts, and packaging — are deterministic and
re-runnable for every registered paper.

## Papers are data, not code

The pipeline serves any number of papers. Everything that differs between them lives under
`papers/<slug>/`:

```
papers/<slug>/paper.json          identity, source PDF, section map, coverage expectations
papers/<slug>/content/*.md        the translation, one file per section
papers/<slug>/glossary.md         binding terminology for this paper
papers/<slug>/assets/figures/     figure crops, committed
```

Everything identical across papers stays shared under `src/`: the page template, the theme and
print stylesheet, the reader script, and the single subset font. Adding a paper therefore means
writing a manifest — no tool changes, no new constants. `tools/paper.py` loads the manifest and
derives every path (`content_dir`, `figures_dir`, `dist_dir`, `output_path`, …), so a slug is
the only paper-specific argument any tool takes.

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
papers/<slug>/assets/figures/figure-NN.png      figure crops (committed)
        |
        |  authored translation
        v
papers/<slug>/content/NN-name.md                one file per section, MathML inline
papers/<slug>/glossary.md                       shared terminology
        |
        |  tools/build.py --paper <slug>  +  tools/fonts.py
        v
dist/build/<slug>/index.html                    reader page (intermediate)
dist/build/<slug>/assets/{styles,scripts,figures,fonts}/
dist/build/<slug>/manifest.json                 content hash + asset inventory
        |
        |  tools/pack.py --paper <slug>
        v
dist/<title>.html                               single self-contained deliverable, one per paper
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

**Subset, committed fonts; offline build.** Source Han Sans SC is tens of megabytes. The
content uses a few thousand distinct characters, so `tools/fonts.py subset` walks every paper's
content, produces small WOFF2 files covering the union, and commits them under
`src/assets/fonts/`. The subset is shared rather than per paper: the fonts are small, and one
copy keeps `pack.py` and the stylesheet identical for every document. The build itself never
touches the network; `fonts.py coverage` fails the build when content introduces a character the
subset cannot render.

**Latin text is not bundled.** Times New Roman is a system font and cannot be
redistributed. The stylesheet requests it first and falls back through metric-compatible
serifs, so the reading experience is consistent without shipping a proprietary font.

**Highlighting is declarative.** Highlighted pseudocode is authored with semantic classes
(`alg-keyword`, `alg-comment`, …) styled by the committed stylesheet, rather than by adding a
runtime highlighter or a Pygments dependency.

**Glyph substitution for characters the bundled face lacks.** Source Han Sans SC has no glyph
for `⩽` (U+2A7D) or `⊲` (U+22B2), which the DeepSeek source uses inside pseudocode. Those were
replaced with the covered near-equivalents `≤` and `◁`, and `ℝ` with plain `R` inside `<pre>`
blocks. The monospace font stack ends with the subset CJK face so uncommon symbols resolve
to a bundled glyph instead of a system fallback. MathML keeps the true `⩽` and `ℓ`, because
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

**One file, not a folder.** The shipped artifact is a single self-contained HTML file produced
by `tools/pack.py`: the stylesheet, the reader script, the subset fonts and every figure are
inlined as `data:` URIs. Figures are re-encoded to lossless WebP for the embedded copy (702 KiB
versus 1644 KiB for the DeepSeek PNGs, with no quality loss; lossy WebP at q90 was *larger* at
974 KiB), and the committed PNGs stay the untouched source of truth. The packer refuses to write
a file that still contains a non-`data:` resource reference, so a stray `assets/` path fails
loudly instead of shipping a page that silently renders unstyled. Ordinary hyperlinks in the
prose are deliberately left as links, since they cost nothing offline. The multi-file build is
kept under `dist/build/<slug>/` because it is easier to inspect and test; the top level of
`dist/` holds only the deliverables.

## Failure modes and guards

| Failure | Guard |
|---|---|
| Content introduces a CJK glyph missing from the subset font | `build.py --check-fonts` fails with the missing code points |
| Template placeholder left unresolved | `build()` raises `ValueError` listing the placeholders |
| Figure crop includes body text or clips a label | `tools/extract.py` grows the crop around drawing/image bounds; crops are reviewed once against page rasters |
| A manifest is malformed or a page range is impossible | `tools/paper.py` raises `PaperError` naming the paper and the field |
| A tool is run without a slug while several papers exist | `paper.resolve()` refuses and lists the registered slugs |
| Translation skips a paragraph or equation | `tools/coverage.py` cross-check against the manifest plus `.local/source/<slug>/report.json` |
| Wide table overflows the page on a phone | `build.py` wraps every `<table>` in a scrollable `.table-wrap`; narrow viewports give the table its intrinsic width |
| A packed file still references `assets/` | `tools/pack.py` raises `ValueError` listing the uninlined resource references |
| A title is not a legal filename | `paper.safe_filename` replaces Windows-illegal characters and strips trailing dots/spaces |
| Absolute paths or machine-specific fonts leak into output | dist references only relative `assets/` paths |
