# Reader presentation and publication

The reader is a learning aid, not a publisher's edition. Attribution and a learning-use
notice do not grant permission to distribute translations or extracted figures. Verify the
original license and any necessary permission before public sharing; never describe a
personal-use disclaimer as a legal guarantee.

## One shared reader

`src/styles/reader.css` owns typography for papers, source analyses and surveys. Mixed
Chinese/English prose uses start alignment, normal letter/word spacing and no justification,
including forced line breaks. Do not append project-specific font, fixed-size or alignment
overrides that disappear when the Pages exporter installs the shared stylesheet. Reading-size
controls use `--reading-scale`; code and ASCII diagrams remain monospaced.

The script's modal service is shared by the library, article TOC and citation details. Cards
are centered in the native top layer, scroll internally and lock the background. Backdrop,
close button and Escape restore the opener and original scroll position. Tab and Shift+Tab
cycle within the card. Choosing a TOC heading closes the card *before* scrolling to and
focusing that heading; it does not restore the old position over the intended destination.

Without JavaScript or native dialog support, the original details/TOC tree remains usable.
The same scripts work with `file://`. Print hides interactive cards and overrides background
scroll locking so an open modal cannot clip the printed article.

## Native mathematics

Keep MathML's native `math` layout and text baseline. Inline expressions must not be
`inline-block` scroll boxes. Use a platform MATH-table font independently of prose fonts;
never download or redistribute proprietary system fonts. Ordinary inline math remains in
prose. Display equations and expressions wider than the reading column use a padded,
keyboard-accessible block scroller; resize and reading-scale changes recompute that layout
without modifying the MathML expression. Print restores visible overflow.

Reader fixes must be tested against the staged public snapshot as well as local builds.
Every reader references one library-root asset tree, not a project copy. `tools/assets.py`
refreshes local runtime code without rebuilding prose. Actions composes the current runtime
from main into the approved snapshot, so pipeline UI fixes update all readers automatically;
this never authorizes publishing new article content.

## Compact metadata without lost originals

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

Set `"show_glossary": true` in `work/reader.json` to render `work/glossary.md` as the first
body section and include its headings in the TOC. Use a level-two heading such as
`## 术语对应表`; do not copy the table into `content/`. The glossary contributes to the content
hash and generated section inventory. The field must be boolean; a missing glossary or a
colliding `sec-glossary` content section stops the build. Default/false keeps existing readers
unchanged. English term, manuscript wording and distinctions belong in the table; see
[chinese-writing.md](chinese-writing.md).

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
