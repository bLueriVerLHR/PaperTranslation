# Reader presentation and publication

The reader is a learning aid, not a publisher's edition. Attribution and a learning-use
notice do not grant permission to distribute translations or extracted figures. Verify the
original license and any necessary permission before public sharing; never describe a
personal-use disclaimer as a legal guarantee.

## HTML-first layout guidance

HTML is the delivery target; a browser print stylesheet is a fallback, not a requirement to
produce PDF editions. Screen layout must not inherit A4 dimensions, millimetre-based page
widths or simulated paper margins. Screen articles use the available viewport width with
responsive side gutters, not a fixed `rem`, character-count or paper-size content ceiling.
Paragraphs, headings, title notes and equations share that fluid content area. Chapter
navigation is closed by default at every screen width and opens from the toolbar; there is
no permanent side rail or duplicated outline. Use only source syntax actually supported by
the builder; a design recommendation is not a new directive.

- Let article content expand with the screen instead of centering a fixed-width reading
  strip inside a larger shell. Keep side gutters responsive and bounded; do not bound the
  article width itself. Phone safe-area padding remains available. Dialogs and the library
  card grid are separate UI regions and may retain their own size constraints.
- Collapse to one reading column on phones. Navigation must not consume the narrow content
  area or cover headings. Keep touch targets usable and preserve start-aligned Chinese/Latin
  prose instead of adding justification, forced line breaks or global text shrinking.
- Contain horizontal overflow in the code, table or equation that needs it, not the whole
  page. A scrollable region needs a visible affordance and keyboard access; a clipped right
  edge or a hover-only explanation is not a mobile fallback.
- Keep layout decisions in the shared runtime. Manuscripts supply structure and content, not
  local font sizes, fixed widths or copies of reader CSS/JS. Do not rewrite source paragraphs,
  mathematics or stable anchors just to match one screenshot.

## Markdown sources, generated HTML

Author new Markdown-first projects using the supported [document syntax](markdown.md), not
hand-written layout HTML. An explicit Pandoc profile converts semantic figures, footnotes,
tables and math at build time; it uses this same reader/template and shared runtime. Existing
projects retain their parser unless deliberately migrated. The Pandoc path does not infer
that an original author's headings should be relocated: header notes are explicit maintenance
inputs, while original body material stays in source order. The compatibility extraction rules
below describe the Python-Markdown path, not new author instructions.

## One shared reader

`src/styles/reader.css` owns typography for papers, source analyses and surveys. Mixed
Chinese/English prose uses start alignment, normal letter/word spacing and no justification,
including forced line breaks. Do not append project-specific font, fixed-size or alignment
overrides that disappear when the Pages exporter installs the shared stylesheet. Reading-size
controls use `--reading-scale`; code and ASCII diagrams remain monospaced.

The script's modal service is shared by the library, article TOC, citation details and
Markdown footnotes. Footnote links retain their native target/backlink fallback, and complete
note text remains in the saved document; a dialog never becomes its only copy. Cards
are centered in the native top layer, scroll internally and lock the background. Backdrop,
close button and Escape restore the opener and original scroll position. Tab and Shift+Tab
cycle within the card. Choosing a TOC heading closes the card *before* scrolling to and
focusing that heading; it does not restore the old position over the intended destination.

The TOC uses one canonical nested list, moved into its dialog rather than cloned for a second
navigation. Major chapters use larger, stronger labels; nested subjects use smaller text,
indentation and a quiet branch rule. Sibling entries within a subject are compact, while
chapter groups have an extra gap. Avoid equal large margins on every row or a global font
reduction. Touch pointers retain usable targets; long outlines scroll only in the opened
panel, with a subtle visible scrollbar. Native-details and dialog outlines share these styles.
Current-location highlighting updates only the previous/new entry and retains `aria-current`.

Without JavaScript or native dialog support, the original details/TOC tree remains usable.
The same scripts work with `file://`. Print hides interactive cards and overrides background
scroll locking so an open modal cannot clip the printed article.

## Opt-in question/answer chapters

Explicit question banks can switch between complete paired reading and question-only
self-testing with answer cards. They also offer topic-scoped random practice: the reader
chooses themes derived from the bank's own heading levels, draws one question, and keeps
its answer folded until asked. They reuse the shared modal, preserve no-JS/no-dialog
readability and print all canonical answers. Only marked banks are enhanced; ordinary
chapters are unchanged. See [question-bank authoring and interaction](questions.md) for
the HTML/Markdown contract, `data-level` metadata, search and random-practice semantics,
manifest inventory and validation scope.

## Native mathematics

Keep MathML's native `math` layout and text baseline. Inline expressions must not be
`inline-block` scroll boxes. Use a platform MATH-table font independently of prose fonts;
never download or redistribute proprietary system fonts. Ordinary inline math remains in
prose. Display equations and expressions wider than the reading column use a padded,
keyboard-accessible block scroller; resize and reading-scale changes recompute that layout
without modifying the MathML expression. Without scripts, native MathML width caps keep
oversized expressions local without turning ordinary inline symbols into inline-blocks.
Print restores visible overflow.

For authoring and typography changes:

- Keep variables, operators, subscripts, fractions, delimiters and upright function names
  semantically correct. Use aligned rows only for a meaningful derivation or mathematical
  grouping, not as a page-layout table. Do not insert arbitrary spacing or split expressions
  by text matching to make them fit a phone.
- Give display mathematics sufficient size and vertical clearance without inflating inline
  symbols or compressing every long formula. Keep equation numbers outside the scrollable
  expression so they neither overlap nor disappear with it.
- Inspect the actual font result, not just the configured `font-family` list. STIX Two Math
  and Latin Modern Math are possible MATH-table fonts; their presence on a desktop says
  nothing about availability on a phone. Offline builds still use installed fonts only.
  Any authorized Pages math-font addition must follow `pages.md`'s licensing, version/hash
  pinning and naming requirements, and verify mathematical variants and stretchy assemblies
  after conversion. The Pages exporter now supplies a renamed STIX Two Math face with its
  complete glyph/feature coverage and OpenType MATH table: visible-text-only subsetting
  would miss implicit math alphabets, radicals, script forms and stretchy assemblies.
  Do not download a font from article code or silently change the offline policy.
- A different generator does not by itself fix formula typography. The documented Pandoc
  profile supports build-time TeX-to-MathML; this changes author syntax, not the delivered
  native layout or font policy. It is not permission to replace existing math with images
  during polishing. Other math outputs or runtime renderers need a separate interface decision.

Reader fixes must be tested against the staged public snapshot as well as local builds.
Every reader references one library-root asset tree, not a project copy. `tools/assets.py`
refreshes local runtime code without rebuilding prose. Actions composes the current runtime
from main into the approved snapshot, so pipeline UI fixes update all readers automatically;
this never authorizes publishing new article content.

## Compact source-code presentation

A source excerpt should lead with its technical purpose and readable code, not a paragraph
of version/path bookkeeping. For a source-card design, a short repository label, file basename
and real line range can form the default summary; keep the complete evidence required by
[source-analysis.md](source-analysis.md) beside the same excerpt in an expandable source record.
Do not shorten the canonical commit or source URL, discard the repository-relative path, or
move all identity into inaccessible machine metadata. Full records must remain available in
the saved HTML without fetching GitHub or relying on JavaScript.

Native `details`/`summary` is a compatible progressive disclosure option. Its summary must be
meaningful on a phone, work with touch and keyboard, and leave the code visible when closed.
Existing plain Markdown captions remain valid. `tools/source_cards.py` provides a bounded
compatibility upgrade for the complete legacy caption emitted by the excerpt generator:
`源码摘录` purpose, repository, full commit, path, real line range, symbol and a matching
HTTPS GitHub fixed-version permalink, immediately followed by code. Commit/path/range and
code line count must agree; partial or inconsistent captions remain untouched. This is not a
general prose recognizer or a new Markdown directive. The builder and explicit runtime
refresh use the same idempotent upgrade; the original `pre`/`code` subtree is retained
verbatim. Source verification still belongs to the research records and excerpt generator,
not to this presentation adapter. Reuse structured records when authoring new generators.

Enhanced source cards visually hide common leading spaces without changing `textContent`.
Their copy control writes the original text, with an original-text selection fallback when
clipboard access fails. No-JS readers retain visible code and native source disclosure; they
do not show an unusable copy button. Source ranges are shown, not synthetic gutter numbers.

Display line numbers and copy controls must not contaminate the copied source. Visual removal
of common indentation must preserve the original text and relative indentation, be disclosed,
and leave an original-text copy/fallback. Editing code is not a typography fix. The source
analysis specification owns excerpt verification and permission requirements.

## Presentation review

Check representative narrow and wide views, for example 320/390/768/1440 CSS pixels, as well
as light/dark themes and supported reading-size changes. Verify that:

- prose and the document root do not overflow horizontally; wide content scrolls locally;
- inline math retains its baseline, display symbols are not clipped, equation numbers remain
  readable, and scroll regions can be operated without a pointer;
- source records expand by touch and keyboard, retain full fixed-version identity offline,
  and remain usable with no scripts; unavailable enhanced controls are not left as dead buttons;
- code text, mathematical structure, citations and stable IDs survive the presentation change;
  any display-only normalization is kept separate from canonical content and verification;
- the inspected browser/font environment and any untested mobile engines are reported honestly.
  Desktop viewport emulation is not a real-device or cross-browser typography test.

Use synthetic fixtures and TEMP comparison pages before touching canonical manuscripts.
Passing these checks establishes presentation behavior, not mathematical or technical validity.

## Compact metadata without lost originals

Classify material by authorship and purpose, not merely by a heading's wording. The source
author's technical definitions, glossary chapter or discussion of its title remain manuscript
content in their original position. Editorial term choices and brief genre notes belong below
the title; chapter-title translation maps and authoring instructions belong in non-rendered
maintenance files, not even in source notes.

The shared builder recognizes explicit auxiliary headings such as paper information,
acknowledgements/declarations, publication notes and references. It preserves technical
headings (for example a discussion of variable declarations). Source/rights blocks move
beneath the title in small, optionally expanded source notes, and leave the body TOC.
Publisher-neutrality boilerplate is not represented as the reader's own declaration.
Copyright and licensing restrictions remain intact in the source and source notes.

A project's canonical `work/reader-meta.md` holds header-only Markdown: actual source,
version, applicable license and genuinely relevant reading limitations. Keep operational
history (rejected sources, export status, tool checks, local paths and editorial correction
logs) out of reading pages. Review paragraphs semantically, not by keyword alone: experimental
conditions and technical qualifications are not workflow chatter. Avoid repeating title,
author or source fields already shown immediately above. Move existing notes there without rewriting the
translated argument. The builder's content hash includes this file and `work/reader.json`;
the hash remains a machine-readable HTML attribute rather than a prominent colophon.

Source-code analyses pass `kind: analysis` in builder metadata; they are not labeled as
translations. They retain their real inspected repository, commit and verification limits.
Self-authored reviews use `kind: review`, labeled 原创综述 rather than a translation or source-code
analysis. Keep project identity in canonical `work/meta.json`; do not invent a PDF/web source
manifest or an inspected repository. Publication eligibility is separate from presentation kind;
see `pages.md` for explicit local-only flags and snapshot approval.

## Visible terminology from one canonical glossary

Set `"show_glossary": true` in `work/reader.json` to render the reader-facing
`work/glossary.md` inside the title's **出处与说明**, after `reader-meta.md`. This does **not**
create a body section or add glossary headings to the body TOC. Use a level-two heading such
as `## 译名与文体约定`; keep only reader-relevant term pairs, distinctions and brief descriptive
notes there. Do not copy the table into `content/` or `reader-meta.md`.

The glossary remains a canonical input: it contributes to the content hash and is listed in
`reader_inputs`, not `sections`. The existing `sec-glossary` anchor remains available in the
header for saved links. The field must be boolean; a missing glossary or a colliding
`sec-glossary` content section stops the build. Default/false does not render this editorial
file. An original author's glossary written in `content/` remains body content independently
of this switch.

Before enabling the switch on an old mixed maintenance glossary, separate its contents:
keep English/translated term pairs in `glossary.md`, source/rights and genre descriptions in
`reader-meta.md`, and move chapter-title maps, batch instructions and review records to the
appropriate non-rendered maintenance files. The renderer does not infer or delete those
passages by keyword. Full ownership rules and contrasting examples are in
[chinese-writing.md](chinese-writing.md#正文与维护材料的边界).

## Contextual citations, not a full visible bibliography

Original bibliography files and extracted reference text stay under local `work/`. The
rendered body omits their list/heading. Numbered citations (including ranges) and explicitly
mapped author-year citations gain source links, native hover descriptions, accessible names
and an optional citation card with direct source links. Code, MathML and existing hyperlinks
are not rewritten. No JavaScript still leaves real HTTP(S) hyperlinks.

Optional `work/reader.json` supplies presentation metadata, without any project constants:

```json
{
  "kind": "translation",
  "source_url": "https://example.org/original",
  "citation_style": "mixed",
  "references": {
    "1": {
      "text": "A. Author. Original title (2024).",
      "url": "https://example.org/cited-work",
      "aliases": ["Author et al., 2024"]
    }
  }
}
```

Set `citation_style` to `numeric`, `author-year` or the default `mixed` for the original
citation convention. In author-year papers, ordinary numerical intervals must not turn into
numbered references. Prose entity boundaries (such as `&amp;` in author names) are handled
without rewriting protected code or MathML.

Keep reference text as printed. Normalize extraction whitespace, not facts, dates or apparent
source mistakes. Never invent URLs or pick an ambiguous author/year match. Missing/unmapped
entries must point to the original paper with an explicit limitation, not fabricated metadata.
Bibliographic accuracy and network reachability are separate verification steps.

The build manifest records linked citations and unmapped entries. Deferred citation-card text
also contributes glyphs to a licensed Pages font subset, so accented author names are not lost.

## Source selection and publication

For a rights-restricted published paper, first seek its corresponding arXiv preprint. Verify
identity, authors, fixed version and the applicable license; a similarly titled paper is not
an alternate version, and arXiv availability alone does not permit sharing adaptations. Translate
that verified preprint version in full. Use the published edition only for cited revisions,
without reproducing its complete content by default.

The project no longer maintains `.pagesignore`. Review publication scope explicitly rather
than treating an ignore list as a rights decision. Export only approved readers/assets, never
source PDFs, full English papers, extraction data or canonical work.

`.gitignore` cannot retract a current deployment or remove tracked history. To withdraw previously published material, replace the content
snapshot, verify the live URLs are unavailable and, only with explicit owner authorization,
rewrite affected content-branch history and remove old deployment artifacts. Never silently
force-push. Rewrites cannot recall third-party clones or external caches.

Other reader changes may be built and tested locally without publishing a new translation
snapshot. A removal-only update must preserve every remaining public reader and asset.
