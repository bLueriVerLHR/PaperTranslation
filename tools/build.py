"""Build the reader page from the per-section Markdown content.

The build is a pure function of committed inputs: it reads ``src/content/*.md``, the
page template, styles, scripts, figures, and subset fonts, then writes ``dist/``. No
network access and no runtime math renderer are involved; equations are MathML authored
directly in the content files.

Usage
-----
``python tools/build.py``
    Build ``dist/index.html`` and ``dist/assets/``.
``python tools/build.py --check-fonts``
    Build, then fail if the committed subset font cannot render a content character.
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
CONTENT_DIR = ROOT / "src" / "content"
TEMPLATE_PATH = ROOT / "src" / "templates" / "page.html"
STYLES_DIR = ROOT / "src" / "styles"
SCRIPTS_DIR = ROOT / "src" / "scripts"
ASSETS_DIR = ROOT / "src" / "assets"
CONFIG_PATH = ROOT / "src" / "page.json"
DIST_DIR = ROOT / "dist"

DEFAULT_CONFIG = {
    "title": "DeepSeek-V4.1-Flash",
    "subtitle": "技术报告 · 简体中文译本",
    "author": "DeepSeek-AI",
}


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


def load_config() -> dict[str, str]:
    """Read page metadata, falling back to defaults."""
    config = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        config.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    return config


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


def read_sections(content_dir: Path = CONTENT_DIR) -> list[Section]:
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
    styles_dir: Path = STYLES_DIR,
    scripts_dir: Path = SCRIPTS_DIR,
    assets_dir: Path = ASSETS_DIR,
) -> dict[str, list[str]]:
    """Copy styles, scripts, figures, and fonts into the build output."""
    plan = {
        "styles": (styles_dir, "assets/styles"),
        "scripts": (scripts_dir, "assets/scripts"),
        "figures": (assets_dir / "figures", "assets/figures"),
        "fonts": (assets_dir / "fonts", "assets/fonts"),
    }
    copied: dict[str, list[str]] = {}
    for key, (source, relative) in plan.items():
        target = dist / relative
        target.mkdir(parents=True, exist_ok=True)
        names: list[str] = []
        if source.exists():
            for path in sorted(source.iterdir()):
                if path.is_file():
                    shutil.copy2(path, target / path.name)
                    names.append(path.name)
        copied[key] = names
    return copied


def build(
    dist: Path = DIST_DIR,
    build_date: str | None = None,
    content_dir: Path = CONTENT_DIR,
    template_path: Path = TEMPLATE_PATH,
    styles_dir: Path = STYLES_DIR,
    scripts_dir: Path = SCRIPTS_DIR,
    assets_dir: Path = ASSETS_DIR,
) -> dict[str, object]:
    """Build the reader page and return a manifest of what was produced."""
    sections = read_sections(content_dir)
    config = load_config()
    template = template_path.read_text(encoding="utf-8")
    digest = content_hash(sections)

    replacements = {
        "{{TITLE}}": config["title"],
        "{{SUBTITLE}}": config["subtitle"],
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
    copied = copy_assets(dist, styles_dir, scripts_dir, assets_dir)
    (dist / "index.html").write_text(page, encoding="utf-8")
    manifest = {
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
    parser.add_argument("--dist", type=Path, default=DIST_DIR)
    parser.add_argument("--check-fonts", action="store_true")
    parser.add_argument("--build-date", default=None)
    args = parser.parse_args(argv)

    manifest = build(args.dist, args.build_date)
    print(f"built {args.dist / 'index.html'}")
    print(f"  sections    : {len(manifest['sections'])} -> {', '.join(manifest['sections'])}")
    print(f"  figures     : {len(manifest['assets']['figures'])}")
    print(f"  fonts       : {len(manifest['assets']['fonts'])}")
    print(f"  content hash: {manifest['content_hash']}")

    if args.check_fonts:
        # Imported here so `python tools/build.py` works without the package being on
        # sys.path at module import time.
        sys.path.insert(0, str(ROOT))
        from tools import fonts

        return fonts.main(["coverage"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
