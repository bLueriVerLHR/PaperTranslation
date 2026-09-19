# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A local **LLM survey** product (`tools/survey.py`) alongside the paper pipeline: one
  narrative hub at `dist/survey/index.html` that places many papers in context, plus a folded
  detail page per surveyed work at `dist/survey/papers/<slug>.html` carrying a translated
  original abstract. Each surveyed paper is one folder (`survey/papers/<slug>/meta.json` plus
  `abstract.md`) referenced from the narrative by a `{{paper:<slug>}}` marker, so the hub
  card and the detail page come from the same metadata and cannot drift apart; the build
  fails loudly on either a marker with no folder or a surveyed folder the narrative never
  references. The whole of `survey/` is local-only and ignored, for the same reason as
  `papers/`: its Markdown interleaves original prose with translations of other people's
  abstracts.
- The survey now covers **all seven directions** (machine-learning systems, long-context
  architectures including linear attention, on-device, distributed, multimodal, VLA and
  Agent) as a problem-first narrative: each direction opens with the production failures
  that motivate it - repetition in production, MoE batch inference losing sparsity,
  long-context cost, KV residency, quantization error, straggler and communication
  failures, hallucinated observations, unrecoverable actions, compounding agent errors -
  and the methods are grouped by the pipeline stage that intervenes. 58 papers carry
  verified venue, year and citation counts read from Semantic Scholar on 2026-09-20, with
  the matched title recorded so the count can be re-checked; a count that could not be
  verified is stored as `null` and rendered as unverified rather than as zero. Editorial
  caveats (assumption-bound numbers, new preprints that must not have their figures
  multiplied, preprint-versus-proceedings year differences) render in a separate
  reading-notes aside so they never contaminate a translated abstract. `tools/survey.py`
  gained unique anchors for a paper referenced from several sections, a nullable citation
  field, HTML escaping of template values, and deletion of stale generated detail pages.
  `survey/curation/` records how the corpus was archived and checked: `collect_sources.py`
  snapshots every primary source, `materialize.py` rebuilds metadata while preserving
  verified citation fields, and `check_site.py` audits the built site for duplicate ids,
  broken local links or fragments, unexpanded placeholders and `data:` URIs.
- Full Simplified Chinese translation of *On-device large language models: a survey of model
  compression and system optimization* (Chen et al., *Artificial Intelligence Review* 59:191,
  2026) as a fourth paper under `papers/on-device-llm-survey/`: abstract, Sections 1-8, all 9
  figures and all 9 tables. The paper has no numbered display equations, so no MathML display
  equations appear; inline quantities the PDF text layer had replaced with placeholder ids were
  recovered from the page rasters. The 20-author list, affiliations and the author-contributions
  statement stay in the original per project convention.
- Full Simplified Chinese translation of *Neural Text Degeneration with Unlikelihood Training*
  (Welleck et al., NeurIPS 2019) as a third paper under `papers/unlikelihood-training/`:
  abstract, Sections 1-7 and Appendices A-E, with both figures, all 9 tables and all 23
  numbered display equations as MathML. The paper's own title is used, not the Zotero
  filename, which reads "Neural Text Generation with Unlikelihood Training".
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
- HTML build pipeline (`tools/build.py`): per-section Markdown to an A4 reader page in
  `dist/<slug>/index.html` beside its real `assets/` tree, with a folded-by-default TOC,
  CJK-safe heading anchors, light/dark themes, and a scroll wrapper for wide tables.
- Optional single-file exporter (`tools/pack.py`): folds a built folder into one self-contained
  HTML file on demand (`--out` required), inlining the stylesheet, the reader script and every
  figure as a `data:` URI — figures re-encoded to lossless WebP when that is actually smaller.
  It refuses to emit a file that still references an external resource. Not the shipped format.
- Font pipeline (`tools/fonts.py`): proxy-aware Source Han Sans SC download, subsetting to the
  exact characters used, glyph-coverage check, and the upstream OFL notice.
- Coverage checker (`tools/coverage.py`) that cross-checks sections, figures, tables and
  equations against the source inventory and flags any remaining English prose.
- Repository scaffold: isolated Python 3.14 environment, pytest and ruff configuration,
  AGENTS.md, CONTRIBUTING.md, and architecture notes under `docs/`.
- Licensing: MIT for the pipeline code (`LICENSE`) with an explicit scope notice
  (`NOTICE.md`): no paper-derived material is published, and the MIT grant covers only what is
  actually in the repository.
- Every translation produced above was authored locally and is not committed; `papers/` is
  ignored from now on (see **Changed**).

### Changed

- The deliverable is a **folder**, not a base64 blob: each paper builds to `dist/<slug>/` holding
  `index.html` beside a real `assets/` tree (`assets/styles/reader.css`,
  `assets/scripts/reader.js`, `assets/figures/figure-NN.png`), all reached by relative path.
  Nothing is inlined by default, so the built page opens straight from `file://` while the figures
  stay byte-identical files a browser can cache and a reviewer can inspect. Because the slug now names
  that folder, `paper.load` validates it as a lowercase English identifier
  (`^[a-z0-9]+(?:-[a-z0-9]+)*$`) and rejects anything else with `invalid paper slug ...`; the
  `safe_filename` helper that sanitised Windows-illegal characters out of a Chinese title is gone
  with it, and the top level of `dist/` holds one English-named folder per paper.
- `tools/pack.py` is demoted from the shipped format to an opt-in single-file export: `--out` is
  now required, and `--figures-as-files` inlines only the stylesheet and the reader script. The
  embedded-figure path compares a lossless WebP re-encode against the original and keeps whichever is
  smaller, so a small PNG is no longer inflated by a losing re-encode.
- `tools/build.py` writes directly to the paper's `dist/<slug>/` (the old `dist/build/<slug>/`
  intermediate is gone) and prunes asset files the build did not just write, so a figure dropped from
  `papers/<slug>/assets/figures/` cannot linger in the shipped folder.
- The repository now publishes the pipeline only. `papers/` is `git`-ignored, so translations,
  glossaries, manifests and figure crops are no longer part of the working tree, the commit
  history or the remote: a translation is a derivative work of the paper it translates, and a
  figure crop is a verbatim extract from that paper's PDF. The published clone has the tools and
  no content, and `tools/extract.py` regenerates the figures from a PDF the user supplies.
  `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/architecture.md` and `NOTICE.md` state the
  boundary; `tests/test_paper.py` and `tests/test_coverage.py` skip the registered-paper
  assertions when `papers/` is empty, so the suite is green in a fresh clone.

- The packed deliverable no longer embeds a font. `src/styles/reader.css` only names font
  families in priority order — Times New Roman plus metric-compatible serifs for Latin, then
  Source Han Sans SC, Noto Sans SC, Microsoft YaHei, PingFang SC and Hiragino Sans GB for
  Simplified Chinese — and the browser resolves every glyph from the reader's installed fonts.
  The DeepSeek deliverable drops from 2.13 MiB to 1.07 MiB, the mamba survey from 2.49 MiB to
  1.43 MiB.
- `tools/pack.py` inlines the stylesheet, the reader script and the figures only, and
  `tools/build.py` no longer copies fonts into the built `assets/`.

### Removed

- Every paper-derived file left the repository: `papers/deepseek-v41-flash/`,
  `papers/mamba-survey/` and `papers/unlikelihood-training/` — 33 translated sections, three
  glossaries, three manifests and 17 figure crops (3.9 MiB) — purged from all 27 commits, not
  just from the working tree. They stay on the machine that produced them.
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
- Survey cards no longer letter-space their titles. A title is rendered as a `.paper-title`
  paragraph inside `.body`, so it inherited `text-align: justify` from `reader.css`; combined
  with `text-wrap: balance` this broke a long English title over two lines and stretched its
  word spaces across the full measure. One gap in the Qwen2-VL card title measured 4px natural
  and 92px rendered, and 17 of the 59 card titles wrapped. Card titles, Chinese titles and the
  metadata line now opt back out with `text-align: start`. Printed cards and fact grids also set
  `break-inside: avoid`, so a card is not split across an A4 boundary.

### Security

- `gitleaks` scan over the working tree and the full commit history reports no leaks.

[Unreleased]: https://github.com/bLueriVerLHR/PaperTranslation/compare/v0.0.0...HEAD
