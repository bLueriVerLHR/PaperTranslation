# Architecture

## What this repository is

A small, reproducible pipeline that turns a research paper into a single A4-sized HTML
reading page in Simplified Chinese. It is deliberately not a general translation engine:
translation is authored by an agent one section at a time, while the pipeline guarantees
that the mechanical parts — source extraction, layout, math markup, fonts, and packaging —
are deterministic and re-runnable.

## Data flow

```
.local/source/DeepSeek_V41_Tech_Report.pdf      (external input, not committed)
        |
        |  tools/extract.py
        v
.local/source/pages/page-NN.txt                 per-page text, reading order
.local/source/pages-png/page-NN.png             per-page raster for formula reading
.local/source/sections/*.txt                    section-level text
src/assets/figures/figure-NN.png                figure crops (committed)
        |
        |  authored translation (TASK-4)
        v
src/content/NN-name.md                          one file per section, MathML inline
src/glossary.md                                 shared terminology
        |
        |  tools/build.py  +  tools/fonts.py
        v
dist/index.html                                 reader page
dist/assets/{styles,scripts,figures,fonts}/     copied, offline assets
dist/manifest.json                              content hash + asset inventory
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
content uses a few thousand distinct characters, so `tools/fonts.py subset` produces small
WOFF2 files that are committed under `src/assets/fonts/`. The build itself never touches the
network; `tools/fonts.py coverage` fails the build when content introduces a character the
subset cannot render.

**Latin text is not bundled.** Times New Roman is a system font and cannot be
redistributed. The stylesheet requests it first and falls back through metric-compatible
serifs, so the reading experience is consistent without shipping a proprietary font.

**Highlighting is declarative.** The paper contains a single pseudocode block
(`Algorithm 1`). Rather than add a runtime highlighter or a Pygments dependency, the block
is authored with semantic classes (`alg-keyword`, `alg-comment`, …) styled by the committed
stylesheet.

## Failure modes and guards

| Failure | Guard |
|---|---|
| Content introduces a CJK glyph missing from the subset font | `tools/build.py --check-fonts` fails with the missing code points |
| Template placeholder left unresolved | `build()` raises `ValueError` listing the placeholders |
| Figure crop includes body text or clips a label | `tools/extract.py` grows the crop around drawing/image bounds; crops are reviewed once against page rasters |
| Translation skips a paragraph or equation | TASK-5 coverage cross-check against `.local/source/report.json` |
| Absolute paths or machine-specific fonts leak into output | dist references only relative `assets/` paths |
