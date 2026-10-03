# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Pages and mobile reading

- Add an explicitly authorized reader-only `pages-content` branch and GitHub Actions Pages
  deployment, without publishing canonical `work/`, PDF, extraction or survey source files.
- Add a searchable, grouped reading-library homepage with relative links to every exported
  page, plus return-to-library navigation on readers.
- Improve phone typography, safe-area spacing, 44px reading controls, persistent text-size
  preferences, reduced-motion support and localized overflow for code, tables and MathML.
- Keep default offline readers font-free; Pages self-hosts hash-verified, renamed SIL OFL
  WOFF2 subsets of Source Han Serif SC and Maple Mono CN, plus Tinos when installed Times
  New Roman is unavailable. Include full license notices with the font assets.
- Add staged publication validation and a non-force-pushing TEMP content-checkout helper.

### Storage layout (current)

- The LLM survey deliverable is `dist/llm-survey/`; per-paper supplementary notes live in
  `dist/<slug>/notes/`.

- Per-paper canonical translation, metadata, glossary, figure crops and useful reference
  intermediates now live in `dist/<slug>/work/`. Rebuilds preserve `work/`; never delete the
  entire deliverable tree as a cleanup step.
- Source PDFs remain external originals, read in place with `extract.py --pdf`. A PDF source
  may have a null path; building retained work does not need the original PDF.
- All disposable environments, caches, task presets, logs, reports and experiments live in
  system TEMP via `tools/dev-env.ps1`. Migration archives are temporary recovery data only.
- Directory names in earlier entries below describe historical layouts, not current operating
  rules. Follow `AGENTS.md` and the layout above; do not recreate historical source or scratch
  folders. The survey's source/detail-page directories are a separate, unchanged product.

### Added

- **Web-source support** in the pipeline, so a paper need not come from a PDF. A manifest that
  names `source.web` (`{base, index}`) instead of `source.pdf` gives every section a page URL
  rather than a printed page range; `tools/paper.py` gained a `WebSource` type, a nullable
  `SectionRange.url`, a nullable `Paper.source_pdf` and an `is_web` flag on both, while every
  existing derived path and the plain-`{"pdf": ...}` manifest keep working unchanged.
  `tools/web.py` is the extractor for that source: it fetches each section, walks the rendered
  body and writes the same per-section text plus `report.json` inventory the PDF extractor
  produces, so `build`, `coverage` and the figure listing work identically. It uses the standard
  library only (`urllib.request`), adds no dependency, retries transient transport failures, and
  is idempotent like its PDF counterpart.
- `tools/web.py` recovers equations from the renderer's own output instead of transcribing them:
  the target site renders math as MathJax SVG, where each element still carries
  `data-mml-node` naming the MathML node it came from and each glyph is a `<use data-c="...">`
  codepoint. Walking that structure yields an exact MathML tree, so no LaTeX parser is involved
  and the pipeline keeps its rule that content authors MathML directly. Styled codepoints are
  folded back to plain letters and the styling is recorded as `mathvariant`.
- A `sanitize_svg` pass strips embedded fonts and editor metadata from fetched SVG figures. The
  hand-drawn diagrams on that site carry a base64 WOFF2 web font and the original editor document
  inside their markup; the project never embeds or vendors a font, so both are removed before the
  figure is written (one diagram drops from 60081 to 37759 bytes).
- Recovered equations are now structurally correct. The renderer wraps every real node in one or
  more grouping elements — a TeX grouping atom around a bracketed subscript, an anonymous group
  inside a radical — and `tools/web.py` was reading those wrappers as if they were the glyphs: a
  superscript slot received the wrapper instead of its contents, so `K^(j)` rendered with its five
  parts stacked on five lines, and a `menclose` and an `msqrt` came back empty. Grouping atoms are
  emitted as `mrow`, an unnamed group is descended through, a single-operand bracing wrapper is
  unwrapped, and the duplicate radical glyph the renderer draws itself is dropped so the radicand
  it was hiding shows. All 892 expressions in the Flash Attention series now render inline; a
  probe against the live page goes from 375 malformed elements to zero.
- A cancelled term is no longer lost or drawn unmarked. The source strikes a term out with a
  `<line>`, never a `notation` attribute, so `tools/web.py` reads the two endpoints back and
  records the direction (`updiagonalstrike`, since the renderer's y-axis points up). The struck
  text, previously dropped entirely, is kept inside the `menclose`; and because Chromium
  implements neither the element nor the attribute, `reader.css` draws the diagonal as a hairline
  gradient across the element's box. The four cancellations in the series read as struck-out
  terms again instead of vanishing.
- Full Simplified Chinese translation of the 12 published pages of *Flash Attention From Scratch*
  (Sonny Li, <https://lubits.ch/flash/>) as a web-sourced deliverable under
  `papers/flash-attention-from-scratch/`: the series introduction, Parts 1-8, the appendix, both
  appendices on Ampere microarchitecture and block-size configuration, and the glossary. The
  series' Parts 9 and 10 are still unpublished by the author and are noted as such rather than
  invented. All 100 figures, 69 tables and 892 recovered MathML expressions are carried over.
  Code, PTX and SASS listings are kept verbatim; terminology is
  given bilingually on first use and collected in `papers/flash-attention-from-scratch/glossary.md`.
  The site does not number its own figures or tables, so the extractor assigns numbers and the
  translation keeps `图 N` for the 83 figures that carry no caption rather than inventing one.
- `tools/pack.py` maps `.svg` to `image/svg+xml` and skips the ffmpeg re-encode for vector
  figures. Without the MIME entry a packed SVG would be embedded as
  `application/octet-stream` and a browser would refuse to render it, and a vector figure has
  nothing to gain from a raster re-encode.
- Tests for fenced code rendering in `tools/build.py`: a ``` fence must produce a block with its
  language class, and a fence placed directly under a caption comment must still render.
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
- The survey now covers **all six directions** (machine-learning systems, long-context
  architectures including linear attention, on-device, distributed, multimodal with VLA as one
  of its applications, and Agent) as a problem-first narrative: each direction opens with the
  production failures that motivate it - repetition in production, MoE batch inference losing
  sparsity, long-context cost, KV residency, quantization error, straggler and communication
  failures, hallucinated observations, unrecoverable actions, compounding agent errors -
  and the methods are grouped by the pipeline stage that intervenes. 66 papers carry
  verified venue, year and citation counts read from Semantic Scholar on 2026-09-20, with a
  second, later batch re-verified on 2026-09-22. The matched title is recorded so the count can
  be re-checked; a count that could not be
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
- The distributed direction gained the **万卡 (10,000+ GPU) scale** and production
  fault-recovery rounds: MegaScale and the datacenter characterization of LLM development for
  what changes when a job spans ten thousand GPUs for months, ByteRobust and ByteCheckpoint for
  treating failure detection, recovery and checkpoints as routine infrastructure, Oobleck and
  Bamboo for tolerant pipeline topologies, SWARM parallelism for training across weak and
  unreliable links, and MegaScale-Infer for disaggregating attention from FFN in MoE serving.
  Their primary sources are archived by `survey/curation/collect_scale_sources.py` and
  materialized by `survey/curation/materialize_scale.py`, which is scoped to this round so it
  cannot drop caveats recorded by earlier rounds. VLA is no longer a separate direction: it is
  merged into multimodal as an application, and `check_site.py` now derives the declared
  direction count instead of hard-coding it and asserts one hub file per direction, so the
  merge cannot half-happen.
- Full Simplified Chinese translation of *SalesRLAgent: A Reinforcement Learning Approach for
  Real-Time Sales Conversion Prediction and Optimization* (Nandakishor M, Deepmost Innovations,
  arXiv:2503.23303v1, 2025) as a fifth paper under `papers/sales-rl-agent/`: abstract,
  Sections 1-8, the three tables (Table I conversion-prediction accuracy, Table II inference
  performance, Table III ablation study) as HTML tables, and Algorithm 1 (conversion
  probability estimation) as a numbered pseudocode listing. The paper has no figures and no
  numbered display equations, so the deliverable ships an empty `assets/figures/`. The paper
  narrates in the first person singular, so the translation keeps the author's "I" voice
  rather than smoothing it into "we"; the author list, affiliation, contact address,
  acknowledgment and references stay in the original per project convention.
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

- Code blocks rendered as inline runs instead of blocks. `tools/build.py`'s extension list had
  no `fenced_code`, so a ``` fence became a paragraph holding a `<code>` element, losing the line
  structure of every source listing (the first paper to ship code was the Flash Attention series,
  whose 99 listings all rendered wrong). `fenced_code` is now enabled.
- `tools/coverage.py` matches a figure reference by number and any extension rather than a fixed
  `figure-NN.png`, because a web source downloads SVG figures. The `.png` assumption was baked
  into the checker and would have reported every vector figure as missing.
- Display equations no longer keep a scroll container in the print stylesheet. The printer drew
  a scrollbar widget at the right margin on top of the equation number, hiding it, and clipped
  any formula wider than the column. `.equation` now sets `overflow: visible` in print, mirroring
  the existing `.table-wrap` rule; all three papers regain every equation number.
- An equation is no longer broken out of the sentence that contains it, and no longer swallows
  the line above it. `md_in_html` treats `math` as a block-level tag, so an inline `<math>` that
  opened a source line ended the running paragraph and was emitted as a sibling block: the phrase
  "...stored in the register file of the warp" was cut off from the `(8,8)` that completed it, and
  the equation then rendered across the full width with its parts stacked. `math` is dropped from
  the parser's block-level set, so it stays in the prose where it was written. The same pass gives
  a display equation its own block: a line holding nothing but an equation that wraps an `mtable`
  or carries `display="block"` is surrounded with blank lines, so the short label introducing it
  is not justified letter-by-letter against the full measure (Chinese has no word spaces for the
  justification to absorb, so `*表示该行有改动。` was rendering as `* 表 示 该 行 有 改 动 。`).
  A content file never has to think about blank lines to get its layout right.
- Markdown no longer reaches inside an equation and rewrites a glyph as markup. With `math`
  span-level, `md_in_html` hands the element's contents to the inline patterns, which then pair
  characters: `64*128*2` came back as `64`, emphasis, `2`, with an `<em>` straddling two `<mo>`
  elements. Characters a rule can actually pair (`*`, `_`, `` ` ``, `[`, `]`, `|`, `\`) are now
  written as numeric references between `<math>` and `</math>` — the same character to MathML, no
  longer a pattern to the parser — so the content files keep writing `64*128*2` and `M[i][j]`
  naturally.
- A translated section no longer ships a second table of contents. The body copy of the
  source's own contents list (`## 目录` followed by fifteen `###` entries) duplicated the page's
  folded TOC and aimed every entry at the original site; because it sat at the same heading depth
  as the section's real headings, all sixteen entries became top-level sidebar entries and the
  headings they belonged to had none. `build.py`'s `_DropBodyToc` preprocessor drops a heading
  that introduces a list of headings — recognising the shape, not the wording — so the sidebar
  goes from 294 entries to 278 and `sec-00-front` from 17 to 1.
- Cross-references to the source site no longer leave the offline page. `build.py`'s
  `rewrite_source_links` aims each link whose URL names a page of this paper's own source at the
  `#sec-<name>` anchor of the section that now holds it: 70 such links became 57 page-internal
  anchors, leaving only the colophon's literal citation URL and the feeds link. A link to any
  other host (the paper's repository, a citation) is left exactly as written. A source-site deep
  link such as `Part-3#kernel-1` lands at the top of its section, because the built page never
  recorded the original's heading anchors.
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
