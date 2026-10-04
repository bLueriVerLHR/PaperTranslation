"""Export reader-only Pages content; never copy work trees or source documents.

Use an empty absolute TEMP directory with --out. Publication is a separate explicit
step: review site-manifest.json, then push that directory to pages-content.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import posixpath
import re
import shutil
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import assets, build  # noqa: E402

PRIVATE = {"work", "reference", "survey", ".git", "__pycache__"}
ASSET_TYPES = {".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}
PUBLIC_TYPES = ASSET_TYPES | {".html", ".woff2", ".txt"}


class PageInfo(HTMLParser):
    """Collect title, visible text and local resource/link references."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.text = ""
        self.code = ""
        self.code_depth = 0
        self.refs: list[str] = []
        self.in_title = False
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record references without fetching external links."""
        self.in_title = tag == "title" or self.in_title
        if tag in {"script", "style"}:
            self.hidden_depth += 1
        if tag in {"code", "pre", "kbd", "samp"}:
            self.code_depth += 1
        for key, value in attrs:
            if value and key in {"src", "href", "poster"}:
                self.refs.append(value)
            if value and key == "srcset":
                self.refs.extend(item.strip().split()[0] for item in value.split(","))
            if value and key == "data-citations":
                # Citation card text is rendered on demand, so its glyphs also need subsets.
                try:
                    records = json.loads(value)
                    self.text += " ".join(record["text"] for record in records)
                except (ValueError, KeyError, TypeError):
                    pass

    def handle_endtag(self, tag: str) -> None:
        """End title or hidden text."""
        if tag == "title":
            self.in_title = False
        if tag in {"code", "pre", "kbd", "samp"}:
            self.code_depth = max(0, self.code_depth - 1)
        if tag in {"script", "style"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)

    def handle_data(self, data: str) -> None:
        """Collect glyphs for font subsetting."""
        if self.in_title:
            self.title += data
        if not self.hidden_depth:
            self.text += data
            if self.code_depth:
                self.code += data


def inspect_page(text: str) -> PageInfo:
    """Parse an HTML string."""
    info = PageInfo()
    info.feed(text)
    return info


def is_private(path: Path) -> bool:
    """Reject hidden paths and source directories, case-insensitively."""
    return any(part.lower() in PRIVATE or part.startswith(".") for part in path.parts)


def excluded_projects(path: Path | None = None) -> set[str]:
    """Read publication exclusions as data, never per-project tool constants."""
    path = path or ROOT / ".pagesignore"
    excluded = set()
    if not path.exists():
        return excluded
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        slug = line.split("#", 1)[0].strip().strip("/")
        if not slug:
            continue
        if not build.paper.SLUG_RE.fullmatch(slug):
            raise ValueError(f"{path}:{number}: expected a project slug, not a path or glob")
        excluded.add(slug)
    return excluded


def publication_data(path: Path) -> dict:
    """Reject ambiguous publication JSON rather than silently using the last field."""

    def unique_fields(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}: {path}")
            result[key] = value
        return result

    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
    if not isinstance(data, dict):
        raise ValueError(f"publication metadata must be an object: {path}")
    if "public_export" in data and not isinstance(data["public_export"], bool):
        raise ValueError(f"public_export must be a boolean: {path}")
    return data


def local_only_projects(dist: Path) -> set[str]:
    """Exclude translations and explicit vetoes without changing existing deployments."""
    excluded = excluded_projects()
    for work in dist.glob("*/work"):
        profile = work / "reader.json"
        data = publication_data(profile) if profile.is_file() else {}
        # A paper manifest denotes an external paper, not an authored source-code book.
        translation = (work / "paper.json").is_file() or (
            profile.is_file() and data.get("kind", "translation") == "translation"
        )
        if translation or data.get("public_export") is False:
            excluded.add(work.parent.name)
    for manifest in dist.glob("*/manifest.json"):
        data = publication_data(manifest)
        if data.get("public_export") is False:
            excluded.add(manifest.parent.name)
    return excluded


def public_files(dist: Path) -> list[Path]:
    """Stage eligible readers; translations stay local even with an obsolete opt-in."""
    excluded = local_only_projects(dist)
    files = []
    for path in sorted(dist.rglob("*")):
        relative = path.relative_to(dist)
        if (
            relative.parts[0] in excluded
            or (
                len(relative.parts) == 1
                and path.suffix.lower() == ".html"
                and path.stem in excluded
            )
            or is_private(relative)
        ):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink is not publishable: {relative}")
        # Standard UI code is installed once at the site root, never exported per project.
        if any(
            relative.as_posix() == name or relative.as_posix().endswith("/" + name)
            for name in assets.SOURCES
        ):
            continue
        if path.is_file() and (
            path.suffix.lower() == ".html"
            or ("assets" in relative.parts and path.suffix.lower() in ASSET_TYPES)
        ):
            files.append(path)
    return files


def redact_local_paths(text: str) -> str:
    """Anonymize local repository locations in public copies, never canonical prose."""
    return re.sub(
        r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/<>\s\"']+[\\/]+Documents[\\/]+",
        "$LOCAL_REPOS/",
        text,
        flags=re.IGNORECASE,
    )


def relative_url(source: Path, destination: str) -> str:
    """Return a quoted, base-path independent relative URL."""
    return quote(posixpath.relpath(destination, source.parent.as_posix()), safe="/-._")


def render_home(entries: list[dict[str, str]]) -> str:
    """Create a searchable, grouped directory; every link also works without JS."""
    groups: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        groups.setdefault(entry["path"].split("/")[0], []).append(entry)
    cards = []
    for slug, pages in groups.items():
        primary = next((p for p in pages if p["path"] == f"{slug}/index.html"), pages[0])
        links = "\n".join(
            f'<li><a href="{quote(p["path"], safe="/-._")}">{html.escape(p["title"])}</a></li>'
            for p in pages
            if p is not primary
        )
        details = (
            f'<details class="library-pages"><summary>更多页面（{len(pages) - 1}）</summary>'
            f'<ul class="library-page-links">{links}</ul></details>'
            if links
            else ""
        )
        cards.append(
            f'<section class="library-card"><p class="meta">{html.escape(slug)}</p>'
            f'<h2><a href="{quote(primary["path"], safe="/-._")}">{html.escape(primary["title"])}</a></h2>'
            f"{details}</section>"
        )
    return f"""<!DOCTYPE html>
<html lang="zh-Hans" data-theme="auto"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark"><title>纸上 · 阅读文库</title>
<meta name="description" content="主题综述与源码分析，适合学习的个人阅读文库。">
<link rel="icon" href="data:,"><link rel="stylesheet" href="assets/styles/reader.css">
<link rel="stylesheet" href="assets/styles/library.css">
<link rel="stylesheet" href="assets/fonts/fonts.css"></head><body>
<a class="skip-link" href="#content">跳到文库</a>
<div class="toolbar" role="toolbar" aria-label="阅读工具栏"><button id="theme-toggle" type="button">跟随系统</button></div>
<main class="page library" id="content"><header class="title-block">
<p class="eyebrow">PAPER TRANSLATION / READING LIBRARY</p><h1>纸上 · 阅读文库</h1>
<p class="subtitle">读论文，连起知识，也深入代码。</p>
<p class="meta">{len(groups)} 个项目 · {len(entries)} 个阅读页面</p></header>
<label for="library-search">查找标题或项目</label>
<input id="library-search" type="search" placeholder="例如：Attention、量化、Redis" autocomplete="off">
<p id="search-status" class="meta" role="status" aria-live="polite"></p>
<div class="library-grid">{"".join(cards)}</div>
<footer class="colophon"><p>译文与图示的权利归原作者；管线的 MIT 许可不覆盖这些内容。</p>
<p>中文采用思源宋体裁剪版，代码采用 Maple Mono。英文优先本机 Times New Roman。</p>
<p><a href="assets/fonts/NOTICE.txt">字体许可与来源</a></p></footer></main>
<script src="assets/scripts/reader.js"></script><script src="assets/scripts/library.js"></script></body></html>"""


def check_site(site: Path, *, allow_legacy_assets: bool = False) -> list[str]:
    """Reject source leaks, broken URLs and duplicated/noncanonical standard assets."""
    errors = []
    excluded = excluded_projects()
    for path in sorted(site.rglob("*")):
        relative = path.relative_to(site)
        if ".git" in relative.parts:
            continue
        if relative.parts[0] in excluded:
            errors.append(f"publication-excluded project: {relative}")
        bootstrap = relative.as_posix() == ".github/workflows/pages.yml"
        bootstrap_dir = path.is_dir() and relative.as_posix() in {".github", ".github/workflows"}
        if path.is_symlink() or (is_private(relative) and not bootstrap and not bootstrap_dir):
            errors.append(f"private/symlink: {relative}")
        if not path.is_file():
            continue
        if not allow_legacy_assets and any(
            relative.as_posix().endswith("/" + name) for name in assets.SOURCES
        ):
            errors.append(f"duplicated shared asset: {relative}")
        if (
            path.suffix.lower() not in PUBLIC_TYPES
            and relative.as_posix() != "site-manifest.json"
            and not bootstrap
        ):
            errors.append(f"unsupported file: {relative}")
        if path.suffix == ".txt" and relative.as_posix() not in {
            "assets/fonts/NOTICE.txt",
            "assets/fonts/han-OFL.txt",
            "assets/fonts/maple-OFL.txt",
            "assets/fonts/tinos-OFL.txt",
        }:
            errors.append(f"unexpected text/source file: {relative}")
        refs = []
        if path.suffix == ".html":
            text = path.read_text(encoding="utf-8")
            refs = inspect_page(text).refs
            # Ordinary external citations are fine; external rendering resources are not.
            if re.search(
                r'<(?:script|link|img|iframe)\b[^>]*(?:src|href)=["\']https?://', text, re.I
            ):
                errors.append(f"external render resource: {relative}")
        elif path.suffix == ".css":
            css = path.read_text(encoding="utf-8")
            refs = re.findall(r'url\(["\']?([^\)"\']+)', css)
            refs.extend(re.findall(r'@import\s+["\']([^"\']+)', css))
        for ref in refs:
            url = urlsplit(ref)
            if path.suffix == ".css" and (url.scheme or url.netloc):
                errors.append(f"external CSS render resource: {relative}: {ref}")
                continue
            if url.scheme in {"http", "https", "mailto", "data"} or not url.path:
                continue
            if url.scheme or url.netloc or url.path.startswith("/"):
                errors.append(f"non-portable URL: {relative}: {ref}")
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if not allow_legacy_assets:
                for standard in assets.SOURCES:
                    if (url.path == standard or url.path.endswith("/" + standard)) and target != (
                        site / standard
                    ).resolve():
                        errors.append(f"noncanonical shared asset URL: {relative}: {ref}")
            if not target.is_relative_to(site.resolve()) or not target.exists():
                errors.append(f"missing/escaping URL: {relative}: {ref}")
            elif is_private(target.relative_to(site.resolve())):
                errors.append(f"private URL: {relative}: {ref}")
    return errors


def export(dist: Path, out: Path) -> list[dict[str, str]]:
    """Stage the reviewed allowlist without changing any canonical input."""
    if not out.is_absolute() or not out.resolve().is_relative_to(
        Path(tempfile.gettempdir()).resolve()
    ):
        raise ValueError("--out must be an absolute system TEMP path")
    if out.exists() and any(out.iterdir()):
        raise ValueError("--out must be empty; never clean dist as an export step")
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for source in public_files(dist):
        relative = source.relative_to(dist)
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix != ".html":
            shutil.copy2(source, target)
            continue
        text = assets.rewrite(redact_local_paths(source.read_text(encoding="utf-8")), relative)
        info = inspect_page(text)
        entries.append({"path": relative.as_posix(), "title": info.title.strip() or relative.stem})
        text = text.replace('initial-scale=1"', 'initial-scale=1, viewport-fit=cover"')
        text = text.replace(
            "</head>",
            f'<link rel="stylesheet" href="{relative_url(relative, "assets/fonts/fonts.css")}">\n</head>',
        )
        home = f'<a class="site-home" href="{relative_url(relative, "index.html")}">← 文库</a>'
        text = re.sub(
            r"(<main\b[^>]*>)", lambda match, home=home: match.group(1) + home, text, count=1
        )
        target.write_text(text, encoding="utf-8")
    if not entries:
        raise ValueError("no rendered pages found")
    # A single runtime tree serves every page, including nested legacy readers.
    assets.install(out)
    # GitHub push events use workflows from the pushed branch. Carry this one bootstrap
    # on pages-content too; Actions explicitly excludes it from the published artifact.
    workflow = out / ".github/workflows/pages.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / ".github/workflows/pages.yml", workflow)
    (out / "index.html").write_text(render_home(entries), encoding="utf-8")
    # Fonts are added next by pages_fonts; a complete-site validation is mandatory afterwards.
    (out / "site-manifest.json").write_text(
        json.dumps({"pages": entries}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return entries


def write_inventory(site: Path) -> None:
    """Record exact public file hashes after fonts have been installed."""
    manifest = site / "site-manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["files"] = {
        p.relative_to(site).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(site.rglob("*"))
        if p.is_file()
        and p != manifest
        and not {".git", ".github"}.intersection(p.relative_to(site).parts)
    }
    manifest.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )


def main() -> int:
    """Export or validate a staged site."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument(
        "--refresh-shared",
        type=Path,
        help="update shared assets in a TEMP reader-only snapshot, without rebuilding prose",
    )
    args = parser.parse_args()
    if args.refresh_shared:
        site = args.refresh_shared
        if not site.is_absolute() or not site.resolve().is_relative_to(
            Path(tempfile.gettempdir()).resolve()
        ):
            parser.error("--refresh-shared must be an absolute system TEMP path")
        if not (site / "site-manifest.json").is_file():
            parser.error("--refresh-shared needs an existing reader-only snapshot")
        if errors := check_site(site, allow_legacy_assets=True):
            print("\n".join(errors))
            return 1
        result = assets.refresh(site)
        if errors := check_site(site):
            print("\n".join(errors))
            return 1
        write_inventory(site)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.check:
        errors = check_site(args.check)
        if errors:
            print("\n".join(errors))
            return 1
        write_inventory(args.check)
        print("Reader-only site validated; inventory updated.")
    elif args.out:
        entries = export(args.dist, args.out)
        print(f"Staged {len(entries)} pages at {args.out}; add fonts then run --check.")
    else:
        parser.error("supply --out or --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
