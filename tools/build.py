"""Build one paper's reader page from its per-section Markdown content.

The build reads local-only ``dist/<slug>/work/content/*.md``, the
shared page template, styles, scripts and that paper's figure crops, then writes the deliverable
folder ``dist/<slug>/`` - ``index.html`` beside a real ``assets/`` tree, all referenced by
relative path so the page opens straight from ``file://``. No network access and no runtime math
renderer are involved; equations are MathML authored directly in the content files, and fonts
are left to the browser. The retained ``work/`` tree is the rebuild source of truth and
must never be removed by output cleanup.

Usage
-----
``python tools/build.py --paper <slug>``
    Build ``dist/<slug>/index.html`` and its ``assets/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from html import escape
from pathlib import Path

import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `python tools/build.py` to import the package
    sys.path.insert(0, str(ROOT))

from tools import paper, reader  # noqa: E402  (must follow the sys.path bootstrap above)

TEMPLATE_PATH = ROOT / "src" / "templates" / "page.html"
STYLES_DIR = ROOT / "src" / "styles"
SCRIPTS_DIR = ROOT / "src" / "scripts"


@dataclass
class Section:
    """One content file and its rendered form."""

    path: Path
    identifier: str
    html: str
    tokens: list[dict] = field(default_factory=list)


def slugify(value: str, separator: str = "-") -> str:
    """Slugify a heading while keeping CJK characters.

    The default ``markdown.extensions.toc`` slugify strips non-ASCII text, which would
    leave every Chinese heading with an empty anchor.
    """
    value = re.sub(r"<[^>]+>", "", value)
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_-]+", separator, value)
    return value.strip(separator) or "section"


# A heading that introduces a list of headings. That shape has exactly one meaning in a
# translated section: a table of contents the source kept in its own body rather than in a
# sidebar. The page already has a table of contents - the folded one - and leaving the second
# copy in place makes every one of its items a sidebar entry of its own, burying the real
# section headings under a duplicate of themselves and aiming each entry back into the copy
# instead of at a section. The heading and its list are therefore dropped.
HEADING_LINE = re.compile(r"^ {0,3}#{1,6}\s+\S")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
LIST_HEADING_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+#{1,6}\s+\S")


class _DropBodyToc(Preprocessor):
    """Remove a table of contents written into the body of a section."""

    def run(self, lines: list[str]) -> list[str]:
        """Return ``lines`` with every heading that introduces a list of headings removed."""
        kept: list[str] = []
        index = 0
        while index < len(lines):
            if HEADING_LINE.match(lines[index]):
                end = self._contents_end(lines, index)
                if end is not None:
                    index = end
                    continue
            kept.append(lines[index])
            index += 1
        return kept

    @staticmethod
    def _contents_end(lines: list[str], start: int) -> int | None:
        """Return the first line after the contents block at ``start``, or ``None`` for none.

        The block is a heading, then - after any blank lines - a list whose first item is
        itself a heading. Everything from the heading to the last list item goes; a blank line
        inside the list keeps it going, since a list may be written with one item per
        paragraph. The separating blank line after the block is left behind, so the drop never
        joins two paragraphs that were apart.
        """
        index = start + 1
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines) or not LIST_HEADING_ITEM.match(lines[index]):
            return None
        while index < len(lines):
            if LIST_ITEM.match(lines[index]):
                index += 1
                continue
            if lines[index].strip():
                return index
            probe = index
            while probe < len(lines) and not lines[probe].strip():
                probe += 1
            if probe < len(lines) and LIST_ITEM.match(lines[probe]):
                index = probe
                continue
            return index
        return index


class _DropBodyTocExtension(Extension):
    """Register :class:`_DropBodyToc` ahead of every other preprocessor."""

    def extendMarkdown(self, md: markdown.Markdown) -> None:  # noqa: N802 - Python-Markdown's name
        """Install the preprocessor above the math pass."""
        md.preprocessors.register(_DropBodyToc(md), "body_toc_drop", 45)


MATH_ELEMENT = re.compile(r"<math\b.*?</math>", re.DOTALL | re.IGNORECASE)

# A source line holding nothing but a display equation. Such an equation belongs on a line of its
# own, and ``mtable`` is what marks it as display: content files write an inline equation inside a
# sentence and a multi-row one on its own line. Reconciling the tag with Markdown's block rules is
# this filter's job, so a content file never has to think about blank lines.
DISPLAY_MATH_LINE = re.compile(r"^\s*<math\b(?=[^>]*>).*?</math>\s*$", re.DOTALL | re.IGNORECASE)
DISPLAY_MARKERS = ("<mtable", 'display="block"')

# Characters Markdown would read as markup rather than as themselves. Because an inline
# ``<math>`` sits in a paragraph's text, ``md_in_html`` leaves its contents to the inline
# patterns, which are then free to pair two ``*`` into emphasis or turn ``[a](b)`` into a link.
# Each is written as a numeric reference: that is the same character to MathML, but no longer a
# pattern for the parser. Only the characters a rule can actually pair are listed, so the
# rendered page keeps readable source for everything else.
MARKDOWN_ACTIVE = {
    "*": "&#42;",
    "_": "&#95;",
    "`": "&#96;",
    "[": "&#91;",
    "]": "&#93;",
    "|": "&#124;",
    "\\": "&#92;",
}


class _MathProtection(Preprocessor):
    """Keep Markdown's inline patterns out of the MathML a content file authored."""

    def run(self, lines: list[str]) -> list[str]:
        """Isolate display equations, then escape the Markdown-active characters inside math."""
        text = "\n".join(self._isolate_display_equations(lines))

        def protect(match: re.Match[str]) -> str:
            return "".join(MARKDOWN_ACTIVE.get(char, char) for char in match.group(0))

        return MATH_ELEMENT.sub(protect, text).split("\n")

    @staticmethod
    def _isolate_display_equations(lines: list[str]) -> list[str]:
        """Surround each line that holds only a display equation with blank lines.

        ``math`` is span-level here, so without a blank line Markdown folds the equation into the
        paragraph above. That paragraph is then no longer one line long, and the short label
        introducing the equation (``*表示该行有改动。``) is justified against the full measure and
        reads letter-by-letter.
        """
        spaced: list[str] = []
        for line in lines:
            match = DISPLAY_MATH_LINE.match(line)
            if match and any(marker in line for marker in DISPLAY_MARKERS):
                if spaced and spaced[-1].strip():
                    spaced.append("")
                spaced.extend((line, ""))
            else:
                spaced.append(line)
        return spaced


class _MathProtectionExtension(Extension):
    """Register :class:`_MathProtection` ahead of every other preprocessor."""

    def extendMarkdown(self, md: markdown.Markdown) -> None:  # noqa: N802 - Python-Markdown's name
        """Install the preprocessor above the built-in whitespace pass."""
        md.preprocessors.register(_MathProtection(md), "math_protection", 40)


def make_markdown() -> markdown.Markdown:
    """Create a configured Markdown instance with a CJK-safe TOC.

    ``math`` is dropped from the parser's block-level element set. A content file authors an
    inline equation as ``<math>...</math>`` directly in the prose, and ``md_in_html`` treats a
    block-level tag at the start of a line as the end of the running paragraph: the equation
    would be lifted out of its sentence and emitted as a sibling block. MathML has no
    block-versus-inline distinction of its own - the ``display`` attribute carries that - so
    treating the element as span-level is both correct and what keeps a sentence whole. Its
    contents are then protected, since exposing them to the inline patterns would let Markdown
    rewrite a glyph into markup.

    The body's own table of contents goes first: it duplicates the page's folded one, and its
    items would otherwise each claim a sidebar entry.
    """
    md = markdown.Markdown(
        extensions=[
            "tables",
            "attr_list",
            "md_in_html",
            "sane_lists",
            "def_list",
            "footnotes",
            "toc",
            # Content files carry code as ``` fences; without this extension they would render
            # as inline <code> runs and the source listings would lose their line structure.
            "fenced_code",
            _DropBodyTocExtension(),
            _MathProtectionExtension(),
        ],
        extension_configs={"toc": {"toc_depth": "1-4", "slugify": slugify, "anchorlink": False}},
    )
    md.block_level_elements = [tag for tag in md.block_level_elements if tag != "math"]
    return md


def read_sections(content_dir: Path) -> list[Section]:
    """Render every content file to HTML, in filename order."""
    sections: list[Section] = []
    for path in sorted(content_dir.glob("*.md")):
        md = make_markdown()
        html = md.convert(path.read_text(encoding="utf-8"))
        sections.append(
            Section(
                path=path,
                identifier=f"sec-{path.stem}",
                html=html,
                tokens=list(md.toc_tokens),
            )
        )
    return sections


def render_toc(items: list[dict]) -> str:
    """Render nested TOC tokens as an ``<ol>`` tree."""
    if not items:
        return ""
    lines = ["<ol>"]
    for item in items:
        lines.append(
            f'<li><a href="#{item["id"]}">{item["name"]}</a>'
            + render_toc(item.get("children") or [])
            + "</li>"
        )
    lines.append("</ol>")
    return "\n".join(lines)


def combine_toc(sections: list[Section]) -> str:
    """Merge every section's TOC tokens into one tree."""
    merged: list[dict] = []
    for section in sections:
        for token in section.tokens:
            merged.append(token)
    return render_toc(merged)


def wrap_sections(sections: list[Section]) -> str:
    """Wrap each rendered section in a ``<section>`` element."""
    chunks: list[str] = []
    for section in sections:
        chunks.append(f'<section id="{section.identifier}">\n{section.html}\n</section>')
    return "\n\n".join(chunks)


def wrap_tables(html: str) -> str:
    """Wrap every table in a scroll container so wide tables stay usable on phones."""
    if 'class="table-wrap"' in html:
        return html
    return re.sub(
        r"(<table\b.*?</table>)",
        r'<div class="table-wrap">\1</div>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )


SOURCE_LINK = re.compile(r'(<a\b[^>]*?\bhref=")([^"]+)(")', re.IGNORECASE)


def source_link_targets(current: paper.Paper) -> dict[str, str]:
    """Map every page of a web source to the anchor of the section that now holds it.

    A PDF-sourced paper has no web identity to name, so the map is empty and the rewrite is a
    no-op for it.
    """
    if current.source_web is None:
        return {}
    return {
        current.source_web.absolute(section.url): f"#sec-{section.name}"
        for section in current.sections
        if section.url
    }


def rewrite_source_links(html: str, targets: dict[str, str]) -> str:
    """Aim references to the source site at this page's own sections.

    A translation keeps the cross-references the original wrote between its pages - "continue
    with Part 3", "see the glossary" - and in the deliverable those links would leave a page
    built to open from ``file://`` without a server. Each one is pointed at the ``<section>``
    that now holds that part instead. The original's own anchors (``Part-3#kernel-1``) have no
    counterpart here, because the built page never recorded them, so a deep link lands at the
    top of its section rather than at a subsection. A link to anything else - the paper's
    repository, a citation - is left exactly as written.
    """
    if not targets:
        return html

    def replace(match: re.Match[str]) -> str:
        target = targets.get(match.group(2).split("#", 1)[0])
        if target is None:
            return match.group(0)
        return f"{match.group(1)}{target}{match.group(3)}"

    return SOURCE_LINK.sub(replace, html)


def content_hash(sections: list[Section], extras: list[Path] | None = None) -> str:
    """Return a digest over canonical sections and optional reader notes/citation metadata."""
    digest = hashlib.sha256()
    for path in [*(section.path for section in sections), *(extras or [])]:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def filter_toc(tokens: list[dict], identifiers: set[str]) -> list[dict]:
    """Keep only actual body anchors, including children of a removed auxiliary heading."""
    kept = []
    for token in tokens:
        children = filter_toc(token.get("children") or [], identifiers)
        if token["id"] in identifiers:
            kept.append({**token, "children": children})
        else:
            kept.extend(children)
    return kept


def copy_assets(
    dist: Path,
    styles_dir: Path | None = STYLES_DIR,
    scripts_dir: Path | None = SCRIPTS_DIR,
    figures_dir: Path | None = None,
) -> dict[str, list[str]]:
    """Copy styles, scripts and figures into the build output.

    A ``None`` directory means this build has no such asset set; missing directories are
    skipped rather than treated as an error. Existing files are overwritten in place and a
    stale asset of the same name is replaced, so the copied tree always matches the sources.
    """
    plan = {
        "styles": (styles_dir, "assets/styles"),
        "scripts": (scripts_dir, "assets/scripts"),
        "figures": (figures_dir, "assets/figures"),
    }
    copied: dict[str, list[str]] = {}
    for key, (source, relative) in plan.items():
        target = dist / relative
        target.mkdir(parents=True, exist_ok=True)
        names: list[str] = []
        if source is not None and source.exists():
            for path in sorted(source.iterdir()):
                if path.is_file():
                    shutil.copy2(path, target / path.name)
                    names.append(path.name)
        # The output folder is the deliverable, so a figure crop left behind by an earlier
        # build must not survive: it would ship an image the page no longer references.
        for stale in sorted(target.iterdir()):
            if stale.is_file() and stale.name not in names:
                stale.unlink()
        copied[key] = names
    return copied


def metadata_for(slug: str | None) -> dict[str, str]:
    """Return the page metadata (title, subtitle, author) of a registered paper."""
    current = paper.resolve(slug)
    return {
        "title": current.title,
        "subtitle": current.subtitle,
        "author": current.author,
    }


def build(
    dist: Path,
    content_dir: Path,
    template_path: Path = TEMPLATE_PATH,
    styles_dir: Path | None = STYLES_DIR,
    scripts_dir: Path | None = SCRIPTS_DIR,
    figures_dir: Path | None = None,
    metadata: dict[str, str] | None = None,
    paper_slug: str | None = None,
    build_date: str | None = None,
    source_targets: dict[str, str] | None = None,
) -> dict[str, object]:
    """Build one reader page and return a manifest of what was produced.

    ``source_targets`` says where a cross-reference to the source site should land instead; it
    is derived from the manifest when ``paper_slug`` names one, and given explicitly by a caller
    that builds a folder with no registered paper behind it.
    """
    sections = read_sections(content_dir)
    if metadata is None:
        metadata = metadata_for(paper_slug)
    if source_targets is None and paper_slug is not None:
        source_targets = source_link_targets(paper.load(paper_slug))
    template = template_path.read_text(encoding="utf-8")
    work = content_dir.parent
    profile = reader.load_profile(work)
    extra_files = [
        path for path in (work / "reader.json", work / "reader-meta.md") if path.exists()
    ]
    digest = content_hash(sections, extra_files)
    references = dict(profile.get("references", {}))
    header_notes, body_sections = [], []
    for section in sections:
        body, notes, extracted = reader.split_auxiliary(section.html)
        for key, record in extracted.items():
            configured = references.get(key, {})
            references[key] = {
                **configured,
                **record,
                "url": record.get("url") or configured.get("url"),
            }
        if notes.strip():
            header_notes.append(notes)
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', body))
        if body.strip():
            body_sections.append(
                Section(section.path, section.identifier, body, filter_toc(section.tokens, ids))
            )
    notes_path = work / "reader-meta.md"
    if notes_path.exists():
        header_notes.insert(0, make_markdown().convert(notes_path.read_text(encoding="utf-8")))
    content = rewrite_source_links(wrap_tables(wrap_sections(body_sections)), source_targets or {})
    citations = reader.CitationLinker(
        content, references, profile.get("source_url"), profile.get("citation_style", "mixed")
    )
    content = "".join(citations.output)
    source_url = profile.get("source_url")
    source_link = (
        f'<p class="meta source-link">原文来源：<a href="{escape(source_url, quote=True)}">{escape(source_url)}</a></p>'
        if source_url
        else ""
    )
    source_notes = (
        '<details class="meta source-details"><summary>出处与说明</summary>'
        + "\n".join(header_notes)
        + "</details>"
        if header_notes
        else ""
    )
    kind = profile.get("kind", metadata.get("kind", "translation"))
    notice = (
        "源码与引用材料遵循各自原有许可证。" if kind == "analysis" else "译文与图示的版权归原作者。"
    )

    replacements = {
        "{{TITLE}}": escape(metadata.get("title", "")),
        "{{SUBTITLE}}": escape(metadata.get("subtitle", "")),
        "{{AUTHOR}}": escape(metadata.get("author", "")),
        "{{READER_KIND}}": "源码研读笔记" if kind == "analysis" else "中文译文",
        "{{READER_NOTICE}}": notice,
        "{{SOURCE_LINK}}": source_link,
        "{{SOURCE_NOTES}}": source_notes,
        "{{TOC}}": combine_toc(body_sections),
        "{{CONTENT}}": content,
        "{{BUILD_DATE}}": build_date or date.today().isoformat(),
        "{{CONTENT_HASH}}": digest,
    }
    page = template
    for token, value in replacements.items():
        page = page.replace(token, value)

    leftovers = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if leftovers:
        raise ValueError(f"unresolved template placeholders: {sorted(set(leftovers))}")

    dist.mkdir(parents=True, exist_ok=True)
    copied = copy_assets(dist, styles_dir, scripts_dir, figures_dir)
    (dist / "index.html").write_text(page, encoding="utf-8")
    manifest = {
        "paper": paper_slug,
        "title": metadata.get("title", ""),
        "content_hash": digest,
        "sections": [s.path.name for s in sections],
        "reader_inputs": [path.name for path in extra_files],
        "citations_linked": citations.linked,
        "citations_without_records": sorted(citations.unresolved),
        "assets": copied,
    }
    (dist / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", default=None, help="registered paper slug")
    parser.add_argument("--dist", type=Path, default=None, help="override the output directory")
    parser.add_argument("--build-date", default=None)
    args = parser.parse_args(argv)

    current = paper.resolve(args.paper)
    dist = args.dist or current.output_dir

    manifest = build(
        dist=dist,
        content_dir=current.content_dir,
        figures_dir=current.figures_dir,
        metadata=metadata_for(current.slug),
        paper_slug=current.slug,
        build_date=args.build_date,
        source_targets=source_link_targets(current),
    )
    print(f"paper        : {current.slug} ({current.title})")
    print(f"built        : {dist / 'index.html'}")
    print(f"  assets      : assets/{{{','.join(sorted(manifest['assets']))}}}")
    print(f"  sections    : {len(manifest['sections'])} -> {', '.join(manifest['sections'])}")
    print(f"  figures     : {len(manifest['assets']['figures'])}")
    print(f"  content hash: {manifest['content_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
