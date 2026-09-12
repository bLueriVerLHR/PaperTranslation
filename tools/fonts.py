"""Vendor and subset the Simplified Chinese font used by the reader page.

The upstream CJK font is large (tens of megabytes). The deliverable only needs the
characters that actually appear in the translation, so this tool subsets the font with
``fontTools`` and writes small WOFF2 files that are committed under
``src/assets/fonts/``. That keeps the build offline: ``tools/build.py`` only copies them.

Subcommands
-----------
``download``
    Fetch Source Han Sans SC (falling back to Noto Sans SC subsets) into ``.local/fonts/``.
``subset``
    Subset the vendored font to the characters used by ``src/content/``.
``coverage``
    Report characters used by the content that the subset font cannot render.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "src" / "content"
FONT_DIR = ROOT / ".local" / "fonts"
OUT_DIR = ROOT / "src" / "assets" / "fonts"
LICENSE_PATH = OUT_DIR / "OFL.txt"

PRIMARY_URL = (
    "https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansSC.zip"
)
OFL_URL = "https://raw.githubusercontent.com/adobe-fonts/source-han-sans/release/LICENSE.txt"

WEIGHTS: dict[str, str] = {"regular": "Regular", "bold": "Bold"}

# Used only when the primary archive is unreachable. These are ready-to-serve subsets
# that already cover the common Simplified Chinese range.
FALLBACK_FILES: dict[str, str] = {
    "regular": "https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5/files/"
    "noto-sans-sc-chinese-simplified-400-normal.woff2",
    "bold": "https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5/files/"
    "noto-sans-sc-chinese-simplified-700-normal.woff2",
}

_MATH_RE = re.compile(r"<math\b.*?</math>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def proxy_url(explicit: str | None = None) -> str | None:
    """Resolve the HTTP(S) proxy from the argument or the environment."""
    if explicit:
        return explicit
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def collect_chars(content_dir: Path = CONTENT_DIR) -> set[str]:
    """Return the set of characters the CJK font must render.

    Math is excluded: it is drawn with the math font. Pseudocode and fenced code stay
    included, because the stylesheet lists the CJK face at the end of the monospace
    fallback chain, so uncommon symbols come from the bundled subset.
    """
    chars: set[str] = set()
    for path in sorted(content_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        text = _FENCE_RE.sub(" ", text)
        text = _MATH_RE.sub(" ", text)
        text = _TAG_RE.sub(" ", text)
        chars.update(text)
    chars.discard("\r")
    chars.discard("\n")
    return chars


def cjk_chars(chars: set[str]) -> set[str]:
    """Return the subset of ``chars`` above the Latin/punctuation block."""
    return {c for c in chars if ord(c) > 0x2010}


def _download(url: str, target: Path, proxy: str | None = None) -> None:
    """Download ``url`` to ``target``, optionally through a proxy."""
    print(f"downloading {url}")
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    else:
        opener = urllib.request.build_opener()
    with opener.open(url, timeout=300) as response:
        payload = response.read()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    print(f"  -> {target} ({len(payload) // 1024} KiB)")


def _extract_otfs(archive: Path, destination: Path) -> list[Path]:
    """Extract only the Regular/Bold OTFs from the release archive."""
    wanted = {f"-{suffix}.otf".lower() for suffix in WEIGHTS.values()}
    written: list[Path] = []
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.namelist():
            name = Path(member).name
            if not name.lower().endswith(".otf"):
                continue
            if not any(name.lower().endswith(suffix) for suffix in wanted):
                continue
            target = destination / name
            target.write_bytes(bundle.read(member))
            written.append(target)
    return written


def _download_license(proxy: str | None) -> None:
    """Fetch the upstream OFL license, best effort."""
    try:
        _download(OFL_URL, LICENSE_PATH, proxy)
        print(f"  -> {LICENSE_PATH}")
    except Exception as error:  # noqa: BLE001 - license is best-effort
        print(f"  license download failed: {error}", file=sys.stderr)


def cmd_download(args: argparse.Namespace) -> int:
    """Fetch and unpack the upstream font."""
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    proxy = proxy_url(args.proxy)
    if any(FONT_DIR.glob("*.otf")) and not args.force:
        print(f"fonts already present in {FONT_DIR}; use --force to refresh")
        return 0

    archive = FONT_DIR / Path(PRIMARY_URL).name
    try:
        if not archive.exists() or args.force:
            _download(PRIMARY_URL, archive, proxy)
        extracted = _extract_otfs(archive, FONT_DIR)
        if extracted:
            print(f"extracted {len(extracted)} font files: {[p.name for p in extracted]}")
            _download_license(proxy)
            return 0
        print("archive did not contain Regular/Bold OTFs", file=sys.stderr)
    except Exception as error:  # noqa: BLE001 - fall through to the mirror
        print(f"primary download failed: {error}", file=sys.stderr)

    print("falling back to prebuilt Noto Sans SC subsets")
    for slug, url in FALLBACK_FILES.items():
        _download(url, FONT_DIR / f"noto-sans-sc-{slug}.woff2", proxy)
    _download_license(proxy)
    print("note: fallback subsets cannot be re-subset; `subset` will copy them as-is")
    return 0


def _pick(weight: str) -> Path | None:
    """Find the vendored OTF for a weight."""
    suffix = f"-{WEIGHTS[weight]}.otf"
    candidates = [
        p for p in sorted(FONT_DIR.glob("*.otf")) if p.name.lower().endswith(suffix.lower())
    ]
    return candidates[0] if candidates else None


def cmd_subset(args: argparse.Namespace) -> int:
    """Subset the vendored fonts down to the characters in use."""
    chars = collect_chars()
    text = "".join(sorted(chars))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    success = True
    for weight in WEIGHTS:
        source = _pick(weight)
        target = OUT_DIR / f"source-han-sans-sc-{weight}.woff2"
        if source is None:
            fallback = FONT_DIR / f"noto-sans-sc-{weight}.woff2"
            if fallback.exists():
                shutil.copy2(fallback, target)
                print(f"{fallback.name} -> {target.name} ({target.stat().st_size // 1024} KiB)")
                continue
            print(f"missing font for weight {weight}; run `fonts.py download`", file=sys.stderr)
            success = False
            continue
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.notdef_outline = True
        options.recalc_bounds = True
        font = subset.load_font(str(source), options)
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text=text)
        subsetter.subset(font)
        subset.save_font(font, str(target), options)
        font.close()
        print(
            f"{source.name} -> {target.name} ({target.stat().st_size // 1024} KiB, "
            f"{len(chars)} chars)"
        )
    if not LICENSE_PATH.exists():
        print("note: OFL.txt is missing; run `fonts.py download`", file=sys.stderr)
    return 0 if success else 1


def cmd_coverage(args: argparse.Namespace) -> int:
    """Report content characters the committed subset font cannot render."""
    needed = cjk_chars(collect_chars())
    regular = OUT_DIR / "source-han-sans-sc-regular.woff2"
    if not regular.exists():
        print(f"missing {regular}; run `fonts.py subset`", file=sys.stderr)
        return 1
    with TTFont(io.BytesIO(regular.read_bytes())) as font:
        available = set(font.getBestCmap().keys())
    missing = sorted(c for c in needed if ord(c) not in available)
    print(f"cjk-ish characters needed : {len(needed)}")
    print(f"missing from subset       : {len(missing)}")
    if missing:
        print("  " + " ".join(f"{c!r}(U+{ord(c):04X})" for c in missing[:60]))
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="fetch the upstream font")
    download.add_argument("--force", action="store_true")
    download.add_argument("--proxy", default=None, help="HTTP(S) proxy URL")
    download.set_defaults(func=cmd_download)

    subset_cmd = sub.add_parser("subset", help="subset fonts to the content characters")
    subset_cmd.set_defaults(func=cmd_subset)

    coverage = sub.add_parser("coverage", help="check glyph coverage of the content")
    coverage.set_defaults(func=cmd_coverage)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
