"""One shared asset tree per library, for file:// and Pages alike.

Page-specific figures stay beside their pages. Standard reader/library/survey code
is installed exactly once, at the library root. Refreshing it never rebuilds prose.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "assets/styles/reader.css": ROOT / "src/styles/reader.css",
    "assets/scripts/reader.js": ROOT / "src/scripts/reader.js",
    "assets/styles/library.css": ROOT / "src/pages/library.css",
    "assets/scripts/library.js": ROOT / "src/pages/library.js",
    "assets/styles/survey.css": ROOT / "src/survey/survey.css",
}
PRIVATE = {"work", "reference", ".git", "__pycache__"}
RESOURCE = re.compile(
    r"(<(?:link|script)\b[^>]*?\b(?:href|src)\s*=\s*)([\"\'])([^\"\']+)(\2)", re.I
)


def relative_url(page: Path, resource: str) -> str:
    """Return a portable relative URL for any page depth (including project Pages)."""
    return quote(posixpath.relpath(resource, page.parent.as_posix()), safe="/-._")


def install(site: Path) -> list[str]:
    """Update the five standard resources once; preserve fonts and unrelated files."""
    changed = []
    for relative, source in SOURCES.items():
        target = site / relative
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
            raise ValueError(f"shared asset path is a symlink: {target}")
        data = source.read_bytes()
        if not target.exists() or target.read_bytes() != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            changed.append(relative)
    return changed


def rewrite(text: str, page: Path) -> str:
    """Change only standard local stylesheet/script URLs, not article markup or fonts."""

    def replace(match: re.Match[str]) -> str:
        url = urlsplit(match[3])
        if url.scheme or url.netloc:
            return match[0]
        path = Path(url.path).as_posix()
        for relative in SOURCES:
            if path == relative or path.endswith("/" + relative):
                return match[1] + match[2] + relative_url(page, relative) + match[4]
        return match[0]

    return RESOURCE.sub(replace, text)


def refresh(site: Path) -> dict[str, list[str]]:
    """Migrate rendered URLs once, then refresh just the shared tree on later calls.

    Canonical work, figures, fonts and nonstandard resources are never removed.
    Only obsolete copies of these five generated standard files are retired.
    """
    changed = install(site)
    pages, removed = [], []
    for path in sorted(site.rglob("*.html")):
        relative = path.relative_to(site)
        if PRIVATE.intersection(relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"reader page is a symlink: {path}")
        text = path.read_text(encoding="utf-8")
        rewritten = rewrite(text, relative)
        if rewritten != text:
            path.write_text(rewritten, encoding="utf-8", newline="\n")
            pages.append(relative.as_posix())
    for relative in SOURCES:
        for path in sorted(site.glob("**/" + relative)):
            local = path.relative_to(site)
            if local.as_posix() == relative or PRIVATE.intersection(local.parts):
                continue
            if path.is_symlink():
                raise ValueError(f"legacy asset is a symlink: {path}")
            path.unlink()
            removed.append(local.as_posix())
    return {"shared_assets": changed, "pages": pages, "removed_legacy_copies": removed}


def main() -> int:
    """Refresh local library assets without rebuilding or publishing any translation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error("library root must already exist")
    result = refresh(args.root)
    for key, value in result.items():
        print(f"{key}: {len(value)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
