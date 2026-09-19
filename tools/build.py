"""Build one paper's reader page from its per-section Markdown content.

The build is a pure function of committed inputs: it reads ``papers/<slug>/content/*.md``, the
shared page template, styles, scripts and that paper's figure crops, then writes the deliverable
folder ``dist/<slug>/`` - ``index.html`` beside a real ``assets/`` tree, all referenced by
relative path so the page opens straight from ``file://``. No network access and no runtime math
renderer are involved; equations are MathML authored directly in the content files, and fonts
are left to the browser.

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
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `python tools/build.py` to import the package
    sys.path.insert(0, str(ROOT))

from tools import paper  # noqa: E402  (must follow the sys.path bootstrap above)

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


def make_markdown() -> markdown.Markdown:
    """Create a configured Markdown instance with a CJK-safe TOC."""
    return markdown.Markdown(
        extensions=[
            "tables",
            "attr_list",
            "md_in_html",
            "sane_lists",
            "def_list",
            "footnotes",
            "toc",
        ],
        extension_configs={"toc": {"toc_depth": "2-4", "slugify": slugify, "anchorlink": False}},
    )


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


def content_hash(sections: list[Section]) -> str:
    """Return a short digest over the section source files."""
    digest = hashlib.sha256()
    for section in sections:
        digest.update(section.path.name.encode("utf-8"))
        digest.update(section.path.read_bytes())
    return digest.hexdigest()[:12]


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
) -> dict[str, object]:
    """Build one reader page and return a manifest of what was produced."""
    sections = read_sections(content_dir)
    if metadata is None:
        metadata = metadata_for(paper_slug)
    template = template_path.read_text(encoding="utf-8")
    digest = content_hash(sections)

    replacements = {
        "{{TITLE}}": metadata.get("title", ""),
        "{{SUBTITLE}}": metadata.get("subtitle", ""),
        "{{AUTHOR}}": metadata.get("author", ""),
        "{{TOC}}": combine_toc(sections),
        "{{CONTENT}}": wrap_tables(wrap_sections(sections)),
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
