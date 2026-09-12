# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Full Simplified Chinese translation of *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache
  Compression*: abstract, Sections 1-6, Appendix B and Appendix C, with all 12 figures, 5
  tables and 17 numbered display equations as MathML.
- PDF extraction pipeline (`tools/extract.py`): per-page text and rasters, automatic figure
  crop detection, and a machine-readable element inventory.
- HTML build pipeline (`tools/build.py`): per-section Markdown to a single A4 reader page with
  a folded-by-default TOC, CJK-safe heading anchors, light/dark themes, and a scroll wrapper
  for wide tables.
- Font pipeline (`tools/fonts.py`): proxy-aware Source Han Sans SC download, subsetting to the
  exact characters used, glyph-coverage check, and the upstream OFL notice.
- Coverage checker (`tools/coverage.py`) that cross-checks sections, figures, tables and
  equations against the source inventory and flags any remaining English prose.
- Repository scaffold: isolated Python 3.14 environment, pytest and ruff configuration,
  AGENTS.md, CONTRIBUTING.md, and architecture notes under `docs/`.

### Fixed

- Figure crops no longer clip the caption line, and subfigure labels sitting between the
  artwork and the caption are now included in the crop.
- Dependency advisories in `fonttools`, `brotli` and `pytest` were resolved by upgrading;
  `pip-audit -r requirements.txt` now reports no known vulnerabilities.

### Security

- `gitleaks` scan over the working tree and the full commit history reports no leaks.

[Unreleased]: https://example.invalid/PaperTranslation/compare/v0.0.0...HEAD
