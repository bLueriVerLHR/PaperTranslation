# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Full Simplified Chinese translation of *A comprehensive survey and taxonomy of mamba:
  Applications, Challenges, and Future Directions* (Miao et al., *Information Fusion* 130, 2026,
  104094) as a second paper under `papers/mamba-survey/`: abstract, Sections 1-9, all 3 figures,
  all 5 tables and all 5 numbered display equations as MathML.
- Multi-paper layout: every translated paper now lives in `papers/<slug>/` with a `paper.json`
  manifest holding its identity, source PDF, printed section map and coverage expectations.
  `tools/paper.py` resolves the manifest, and `extract`, `build`, `pack`, `coverage` and `fonts`
  all take `--paper <slug>`. Adding a paper no longer requires touching tool code.
- `tools/build.py` emits the intermediate build to `dist/build/<slug>/`, so the top level of
  `dist/` holds only the shipped deliverables, one self-contained HTML file per paper.
- `papers/deepseek-v41-flash/` and `papers/mamba-survey/` as the two registered papers.
- Full Simplified Chinese translation of *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache
  Compression*: abstract, Sections 1-6, Appendix B and Appendix C, with all 12 figures, 5
  tables and 17 numbered display equations as MathML.
- PDF extraction pipeline (`tools/extract.py`): per-page text and rasters, automatic figure
  crop detection, and a machine-readable element inventory.
- HTML build pipeline (`tools/build.py`): per-section Markdown to a single A4 reader page with
  a folded-by-default TOC, CJK-safe heading anchors, light/dark themes, and a scroll wrapper
  for wide tables.
- Single-file packer (`tools/pack.py`): inlines the subset fonts, all figures (re-encoded to
  lossless WebP when `ffmpeg` is available), the stylesheet and the script as `data:` URIs, and
  writes one self-contained HTML file named after the document title. It refuses to emit a file
  that still references an external resource.
- Font pipeline (`tools/fonts.py`): proxy-aware Source Han Sans SC download, subsetting to the
  exact characters used, glyph-coverage check, and the upstream OFL notice.
- Coverage checker (`tools/coverage.py`) that cross-checks sections, figures, tables and
  equations against the source inventory and flags any remaining English prose.
- Repository scaffold: isolated Python 3.14 environment, pytest and ruff configuration,
  AGENTS.md, CONTRIBUTING.md, and architecture notes under `docs/`.
- Licensing: MIT for the pipeline code (`LICENSE`) with an explicit scope notice
  (`NOTICE.md`) that the translated text and extracted figures are the original authors'
  material and are excluded from the MIT grant.

### Changed

- The packed deliverable no longer embeds a font. `src/styles/reader.css` only names font
  families in priority order — Times New Roman plus metric-compatible serifs for Latin, then
  Source Han Sans SC, Noto Sans SC, Microsoft YaHei, PingFang SC and Hiragino Sans GB for
  Simplified Chinese — and the browser resolves every glyph from the reader's installed fonts.
  The DeepSeek deliverable drops from 2.13 MiB to 1.07 MiB, the mamba survey from 2.49 MiB to
  1.43 MiB.
- `tools/pack.py` inlines the stylesheet, the reader script and the figures only, and
  `tools/build.py` no longer copies fonts into `dist/build/<slug>/assets/`.

### Removed

- Bundled subset fonts and everything that existed to produce and check them:
  `src/assets/fonts/` (including `OFL.txt`), `tools/fonts.py`, `tests/test_fonts.py`, the
  `build.py --check-fonts` gate, and the font download/subset/coverage rows in the command
  tables. `fonttools` and `brotli` leave `requirements.txt` with them. No font is redistributed
  any more, so `NOTICE.md` loses its OFL section.

### Fixed

- Display equations no longer keep a scroll container in the print stylesheet. The printer drew
  a scrollbar widget at the right margin on top of the equation number, hiding it, and clipped
  any formula wider than the column. `.equation` now sets `overflow: visible` in print, mirroring
  the existing `.table-wrap` rule; all three papers regain every equation number.
- Figure captions in the Elsevier style (`Fig. 1. ...`) are now detected, so two-column
  publisher PDFs produce figure crops at all.
- Two-column pages are rebuilt in true reading order (full-width blocks split the page into
  bands, each band read left column first), instead of the interleaved order PyMuPDF returns;
  a page's column count is declared per paper in its manifest.
- Figure crops no longer clip the caption line, and subfigure labels sitting between the
  artwork and the caption are now included in the crop.
- Dependency advisories in `fonttools`, `brotli` and `pytest` were resolved by upgrading;
  `pip-audit -r requirements.txt` now reports no known vulnerabilities.

### Security

- `gitleaks` scan over the working tree and the full commit history reports no leaks.

[Unreleased]: https://example.invalid/PaperTranslation/compare/v0.0.0...HEAD
