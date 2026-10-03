# Reader presentation and local-only publication

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

## Compact metadata without lost originals

The shared builder recognizes explicit auxiliary headings such as paper information,
acknowledgements/declarations, publication notes and references. It preserves technical
headings (for example a discussion of variable declarations). Source/rights blocks move
beneath the title in small, optionally expanded source notes, and leave the body TOC.
Publisher-neutrality boilerplate is not represented as the reader's own declaration.
Copyright and licensing restrictions remain intact in the source and source notes.

A project's canonical `work/reader-meta.md` holds header-only Markdown: source, version,
translation choices and reading limitations. Move existing notes there without rewriting the
translated argument. The builder's content hash includes this file and `work/reader.json`;
the hash remains a machine-readable HTML attribute rather than a prominent colophon.

Source-code analyses pass `kind: analysis` in builder metadata; they are not labeled as
translations. They retain their real inspected repository, commit and verification limits.

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

## Publication exclusions are not Git privacy

`.pagesignore` is a tracked, data-driven list of project slugs (one per line, optional comments).
`tools/pages.py` excludes those entire project trees from export and rejects an already-staged
site containing them. Local readers and their canonical work remain untouched.

This is separate from `.gitignore`: ignoring a path cannot retract a current deployment or
remove tracked history. To withdraw previously published material, replace the content
snapshot, verify the live URLs are unavailable and, only with explicit owner authorization,
rewrite affected content-branch history and remove old deployment artifacts. Never silently
force-push. Rewrites cannot recall third-party clones or external caches.

Other reader changes may be built and tested locally without publishing a new translation
snapshot. A removal-only update must preserve every remaining public reader and asset.
