"""Optional: fold one paper's built folder into a single self-contained HTML file.

The shipped deliverable is a *folder*: ``dist/<slug>/index.html`` beside a real ``assets/``
tree, which every browser opens straight from ``file://``. That is what ``tools/build.py``
produces and it is the layout the project ships.

This tool exists only for the case where a folder is awkward - mailing one file to a reader,
or opening it from a device that cannot follow relative paths. It reads the built folder and
inlines the stylesheet, the reader script and every figure as ``data:`` URIs, producing a
single file that needs no siblings. Because base64 costs roughly a third more bytes than the
binary it carries, this is deliberately opt-in and never the default: pass ``--out`` to say
where the file goes.

``--figures=file`` keeps the images as files in a sibling ``figures/`` folder and inlines only
the stylesheet and the script, which is the cheapest way to get a one-*page* file when the
images can travel next to it.

Fonts are deliberately *not* embedded: the stylesheet only names font families, so the browser
resolves each glyph from the reader's own fonts.
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

_IMAGE_RE = re.compile(r'src="assets/figures/([^"]+)"')
# Resources the browser must fetch to render the page (images, scripts, stylesheets).
_RESOURCE_RE = re.compile(
    r'<(?:img|script|link|source|iframe)\b[^>]*?(?:src|href)="(?!#)(?!data:)([^"]+)"',
    re.IGNORECASE,
)
# Ordinary hyperlinks in the prose; they do not affect offline rendering.
_CONTENT_LINK_RE = re.compile(r'<a\b[^>]*href="(?!#)(?!data:)([^"]+)"', re.IGNORECASE)

MIME_TYPES = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg"}


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


def figure_data_uri(image: Path, use_webp: bool = True) -> str:
    """Return a data URI for a figure, preferring a lossless WebP re-encode.

    WebP only wins for large raster crops; the small PNGs this pipeline commonly produces are
    often smaller untouched, so the re-encode is compared against the original and the smaller
    of the two is embedded. Nothing is written back to the source figure.
    """
    if use_webp and (ffmpeg := ffmpeg_path()):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / (image.stem + ".webp")
            result = subprocess.run(  # noqa: S603 - fixed argv, resolved ffmpeg path
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(image),
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
            if (
                result.returncode == 0
                and target.exists()
                and 0 < target.stat().st_size < image.stat().st_size
            ):
                return file_data_uri(target)
    return file_data_uri(image)


def external_resource_refs(html: str) -> list[str]:
    """Return resource URLs the page would still have to fetch (should be empty)."""
    return sorted(set(_RESOURCE_RE.findall(html)))


def content_links(html: str) -> list[str]:
    """Return ordinary hyperlinks in the prose; these do not break offline reading."""
    return sorted(set(_CONTENT_LINK_RE.findall(html)))


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
    out: Path,
    use_webp: bool = True,
    figures_as_files: bool = False,
) -> Path:
    """Fold ``dist/index.html`` and its assets into a single file at ``out``."""
    page_path = dist / "index.html"
    if not page_path.exists():
        raise FileNotFoundError(f"no built page at {page_path}; run tools/build.py first")
    html = page_path.read_text(encoding="utf-8")

    stylesheet = dist / "assets" / "styles" / "reader.css"
    if stylesheet.exists():
        css = stylesheet.read_text(encoding="utf-8")
        html = html.replace(STYLESHEET_TAG, f"<style>\n{css}\n</style>")

    script = dist / "assets" / "scripts" / "reader.js"
    if script.exists():
        html = html.replace(
            SCRIPT_TAG, f"<script>\n{script.read_text(encoding='utf-8')}\n</script>"
        )

    if figures_as_files:
        # The images travel beside the page, so rewrite the references before the leftover check:
        # `figures/...` is a sibling path by design, not an asset that failed to inline.
        target_figures = out.parent / "figures"
        target_figures.mkdir(parents=True, exist_ok=True)
        source_figures = dist / "assets" / "figures"
        if source_figures.exists():
            for figure in sorted(source_figures.iterdir()):
                if figure.is_file():
                    shutil.copy2(figure, target_figures / figure.name)
        html = html.replace('src="assets/figures/', 'src="figures/')
    else:
        html = inline_images(html, dist / "assets" / "figures", use_webp)

    leftovers = external_resource_refs(html)
    if figures_as_files:
        # In this mode `figures/...` is the intended sibling path; only a leftover `assets/`
        # reference means the rewrite missed something.
        leftovers = [ref for ref in leftovers if ref.startswith("assets/")]
    if leftovers:
        raise ValueError(f"assets were not inlined: {leftovers}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", default=None, help="registered paper slug")
    parser.add_argument("--dist", type=Path, default=None, help="override the built folder")
    parser.add_argument("--out", type=Path, required=True, help="where to write the single file")
    parser.add_argument(
        "--figures-as-files",
        action="store_true",
        help="leave the figures as files in a sibling figures/ folder instead of embedding them",
    )
    parser.add_argument(
        "--no-webp", action="store_true", help="embed the original PNGs instead of lossless WebP"
    )
    args = parser.parse_args(argv)

    current = paper.resolve(args.paper)
    dist = args.dist or current.output_dir
    if args.dist is not None and args.out.parent == dist:
        parser.error("--out must be outside the built folder when --dist is given")

    target = pack(
        dist,
        args.out,
        use_webp=not args.no_webp,
        figures_as_files=args.figures_as_files,
    )
    size = target.stat().st_size
    text = target.read_text(encoding="utf-8")
    print(f"paper            : {current.slug}")
    print(f"folded           : {target}")
    print(f"  size             : {size / 1024 / 1024:.2f} MiB")
    print(f"  figures          : {'files in figures/' if args.figures_as_files else 'embedded'}")
    print(f"  resource refs    : {len(external_resource_refs(text))} (must be 0)")
    print(f"  content links    : {len(content_links(text))} (left as written; not fetched)")
    print("note             : the folder under dist/<slug>/ is the deliverable; this is an export")
    return 0


if __name__ == "__main__":
    sys.exit(main())
