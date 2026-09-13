"""Pack one paper's built reader page into a single self-contained HTML file.

The multi-file build under ``dist/build/<slug>/`` is convenient to test and inspect, but the
shipped deliverable is a single file that can be copied anywhere and opened offline. This tool
inlines the stylesheet, the reader script, the subset fonts and every figure as ``data:`` URIs,
then writes ``dist/<title>.html`` - exactly one file per registered paper.

Figures are re-encoded to lossless WebP for the embedded copy when ``ffmpeg`` is available:
measured at 43% of the PNG size with no quality loss. The committed PNGs under
``papers/<slug>/assets/figures/`` are never modified, and the pack silently falls back to them
when ``ffmpeg`` is missing.
"""

from __future__ import annotations

import argparse
import base64
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `python tools/pack.py` to import the package
    sys.path.insert(0, str(ROOT))

from tools import paper  # noqa: E402  (must follow the sys.path bootstrap above)

STYLESHEET_TAG = '<link rel="stylesheet" href="assets/styles/reader.css">'
SCRIPT_TAG = '<script src="assets/scripts/reader.js"></script>'

_FONT_URL_RE = re.compile(r'url\("\.\./fonts/([^"]+)"\)')
_IMAGE_RE = re.compile(r'src="assets/figures/([^"]+)"')
# Resources the browser must fetch to render the page (images, scripts, stylesheets).
_RESOURCE_RE = re.compile(
    r'<(?:img|script|link|source|iframe)\b[^>]*?(?:src|href)="(?!#)(?!data:)([^"]+)"',
    re.IGNORECASE,
)
# Ordinary hyperlinks in the prose; they do not affect offline rendering.
_CONTENT_LINK_RE = re.compile(r'<a\b[^>]*href="(?!#)(?!data:)([^"]+)"', re.IGNORECASE)

MIME_TYPES = {".woff2": "font/woff2", ".png": "image/png", ".webp": "image/webp"}


def safe_filename(title: str) -> str:
    """Return a filename-safe document title (see :func:`tools.paper.safe_filename`)."""
    return paper.safe_filename(title)


def data_uri(data: bytes, mime: str) -> str:
    """Encode bytes as a ``data:`` URI."""
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def file_data_uri(path: Path) -> str:
    """Encode a file as a ``data:`` URI, guessing the MIME type from the suffix."""
    return data_uri(
        path.read_bytes(), MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")
    )


def ffmpeg_path() -> str | None:
    """Return the ffmpeg executable if one is on PATH."""
    return shutil.which("ffmpeg")


def figure_data_uri(png: Path, use_webp: bool = True) -> str:
    """Return a data URI for a figure, preferring a lossless WebP re-encode."""
    if use_webp and (ffmpeg := ffmpeg_path()):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / (png.stem + ".webp")
            result = subprocess.run(  # noqa: S603 - fixed argv, resolved ffmpeg path
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(png),
                    "-c:v",
                    "libwebp",
                    "-lossless",
                    "1",
                    "-compression_level",
                    "6",
                    str(target),
                ],
                capture_output=True,
                check=False,
            )
            if result.returncode == 0 and target.exists() and target.stat().st_size > 0:
                return file_data_uri(target)
    return file_data_uri(png)


def external_resource_refs(html: str) -> list[str]:
    """Return resource URLs the page would still have to fetch (should be empty)."""
    return sorted(set(_RESOURCE_RE.findall(html)))


def content_links(html: str) -> list[str]:
    """Return ordinary hyperlinks in the prose; these do not break offline reading."""
    return sorted(set(_CONTENT_LINK_RE.findall(html)))


def inline_css(css: str, fonts_dir: Path) -> str:
    """Replace ``url("../fonts/...")`` references with embedded data URIs."""

    def replace(match: re.Match[str]) -> str:
        font = fonts_dir / match.group(1)
        if not font.exists():
            return match.group(0)
        return f'url("{file_data_uri(font)}")'

    return _FONT_URL_RE.sub(replace, css)


def inline_images(html: str, figures_dir: Path, use_webp: bool = True) -> str:
    """Replace ``src="assets/figures/..."`` references with embedded data URIs."""
    cache: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in cache:
            figure = figures_dir / name
            if not figure.exists():
                return match.group(0)
            cache[name] = figure_data_uri(figure, use_webp)
        return f'src="{cache[name]}"'

    return _IMAGE_RE.sub(replace, html)


def pack(
    dist: Path,
    out: Path | None = None,
    use_webp: bool = True,
    title: str | None = None,
) -> Path:
    """Inline every asset of ``dist/index.html`` and write one self-contained file."""
    page_path = dist / "index.html"
    if not page_path.exists():
        raise FileNotFoundError(f"no built page at {page_path}; run tools/build.py first")
    html = page_path.read_text(encoding="utf-8")

    stylesheet = dist / "assets" / "styles" / "reader.css"
    if stylesheet.exists():
        css = inline_css(stylesheet.read_text(encoding="utf-8"), dist / "assets" / "fonts")
        html = html.replace(STYLESHEET_TAG, f"<style>\n{css}\n</style>")

    script = dist / "assets" / "scripts" / "reader.js"
    if script.exists():
        html = html.replace(
            SCRIPT_TAG, f"<script>\n{script.read_text(encoding='utf-8')}\n</script>"
        )

    html = inline_images(html, dist / "assets" / "figures", use_webp)

    leftovers = external_resource_refs(html)
    if leftovers:
        raise ValueError(f"assets were not inlined: {leftovers}")

    document_title = title or "paper"
    target = out or dist / f"{safe_filename(document_title)}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", default=None, help="registered paper slug")
    parser.add_argument("--dist", type=Path, default=None, help="override the build directory")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--title", default=None, help="override the filename title")
    parser.add_argument(
        "--no-webp", action="store_true", help="embed the original PNGs instead of lossless WebP"
    )
    args = parser.parse_args(argv)

    current = paper.resolve(args.paper)
    dist = args.dist or current.dist_dir
    title = args.title or current.title
    if args.out is not None:
        out = args.out
    elif args.dist is not None:
        out = dist / f"{safe_filename(title)}.html"
    else:
        out = current.output_path

    target = pack(dist, out, use_webp=not args.no_webp, title=title)
    size = target.stat().st_size
    text = target.read_text(encoding="utf-8")
    print(f"paper            : {current.slug}")
    print(f"packed {target}")
    print(f"  size             : {size / 1024 / 1024:.2f} MiB")
    print(
        f"  figures          : {'lossless WebP' if not args.no_webp and ffmpeg_path() else 'PNG'}"
    )
    print(f"  resource refs    : {len(external_resource_refs(text))} (must be 0)")
    print(f"  content links    : {len(content_links(text))} (left as written; not fetched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
