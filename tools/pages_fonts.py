"""Add licensed, self-hosted WOFF2 subsets to a staged Pages site.

Original fonts are downloaded only to system TEMP, SHA-256 checked against the
reviewed lock file, and never vendored into main. Subsets use new family names to
respect OFL Reserved Font Names. Re-run on every export to include newly used glyphs.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pages import inspect_page  # noqa: E402

LOCK = ROOT / "tools/font-sources.json"


def download_sources(cache: Path) -> dict[str, Path]:
    """Fetch only pinned HTTPS font sources into TEMP and verify every cached byte."""
    if not cache.is_absolute() or not cache.resolve().is_relative_to(
        Path(tempfile.gettempdir()).resolve()
    ):
        raise ValueError("font cache must be an absolute system TEMP path")
    cache.mkdir(parents=True, exist_ok=True)
    paths = {}
    for source in json.loads(LOCK.read_text(encoding="utf-8")):
        path = cache / source["file"]
        if not path.exists():
            if not source["url"].startswith("https://"):
                raise ValueError("font sources must use HTTPS")
            request = urllib.request.Request(  # noqa: S310 - HTTPS checked above
                source["url"], headers={"User-Agent": "PaperTranslation-fonts"}
            )
            with urllib.request.urlopen(request, timeout=180) as response:  # noqa: S310
                data = response.read(160 * 1024 * 1024 + 1)
            if len(data) > 160 * 1024 * 1024:
                raise ValueError("font download exceeds size limit")
            if hashlib.sha256(data).hexdigest() != source["sha256"]:
                raise ValueError(f"font checksum mismatch: {source['file']}")
            path.write_bytes(data)
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"cached font checksum mismatch: {source['file']}")
        paths[source["file"]] = path
    return paths


def write_subset(source: Path | io.BytesIO, target: Path, points: set[int], family: str) -> None:
    """Subset and rename a font without dropping its copyright/license records."""
    font = TTFont(source, recalcTimestamp=False)
    options = subset.Options()
    options.flavor = "woff2"
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.name_legacy = True
    worker = subset.Subsetter(options=options)
    worker.populate(unicodes=points)
    worker.subset(font)
    # Rename family/full/PostScript names; preserve style and all legal records.
    for record in font["name"].names:
        if record.nameID in {1, 3, 4, 6, 16}:
            value = family.replace(" ", "") if record.nameID == 6 else family
            record.string = value.encode(record.getEncoding())
    if "CFF " in font:
        cff = font["CFF "].cff
        cff.fontNames = [family.replace(" ", "")]
        cff.topDictIndex[0].FamilyName = family
        cff.topDictIndex[0].FullName = family
    font.flavor = "woff2"
    font.save(target)
    font.close()


def font_rule(family: str, name: str, weight: int, style: str, points: set[int]) -> str:
    """Restrict a face to its actual glyphs, so serif punctuation never steals Latin."""
    ranges = ",".join(f"U+{point:X}" for point in sorted(points))
    return (
        f'@font-face {{ font-family: "{family}"; src: url("{name}") format("woff2"); '
        f"font-weight: {weight}; font-style: {style}; font-display: swap; unicode-range: {ranges}; }}"
    )


def install_fonts(site: Path, cache: Path) -> None:
    """Create CJK regular/bold chunks, Maple code faces and a Times-compatible fallback."""
    sources = download_sources(cache)
    out = site / "assets/fonts"
    out.mkdir(parents=True, exist_ok=True)
    counts: Counter[int] = Counter()
    code_points = set(range(32, 127))
    for path in sorted(site.rglob("*.html")):
        info = inspect_page(path.read_text(encoding="utf-8"))
        counts.update(map(ord, info.text))
        code_points.update(map(ord, info.code))
    # Include dynamically generated toolbar/search strings too.
    for script in [*(ROOT / "src/scripts").glob("*.js"), ROOT / "src/pages/library.js"]:
        counts.update(map(ord, script.read_text(encoding="utf-8")))
    counts.update(
        map(ord, "▸▾←→字号目录找到个项目没有匹配请尝试其他关键词跟随系统浅色深色回到顶部")
    )
    all_points = set(counts) | set(range(32, 127))
    rules = []
    for style, weight in (("regular", 400), ("bold", 700)):
        source = sources[f"han-{style}.otf"]
        with TTFont(source) as font:
            points = {p for p in all_points if p > 0x2FF and p in font.getBestCmap()}
        # Frequency chunks mean common text reuses the same small cached font files.
        ordered = sorted(points, key=lambda p: (-counts[p], p))
        for index in range(0, len(ordered), 512):
            chunk = set(ordered[index : index + 512])
            name = f"han-{style}-{index // 512:02d}.woff2"
            write_subset(source, out / name, chunk, "Paper Han Serif")
            rules.append(font_rule("Paper Han Serif", name, weight, "normal", chunk))
    with zipfile.ZipFile(sources["maple-cn.zip"]) as archive:
        for style, weight in (
            ("Regular", 400),
            ("Bold", 700),
            ("Italic", 400),
            ("BoldItalic", 700),
        ):
            member = next(
                name for name in archive.namelist() if name.endswith(f"MapleMono-CN-{style}.ttf")
            )
            data = archive.read(member)
            with TTFont(io.BytesIO(data)) as font:
                points = code_points & set(font.getBestCmap())
            name = f"maple-{style.lower()}.woff2"
            write_subset(io.BytesIO(data), out / name, points, "Paper Maple Mono")
            rules.append(
                font_rule(
                    "Paper Maple Mono",
                    name,
                    weight,
                    "italic" if "Italic" in style else "normal",
                    points,
                )
            )
    for style, weight in (("regular", 400), ("bold", 700), ("italic", 400), ("bolditalic", 700)):
        source = sources[f"tinos-{style}.ttf"]
        with TTFont(source) as font:
            points = {p for p in all_points if p <= 0x2FF and p in font.getBestCmap()}
        name = f"tinos-{style}.woff2"
        write_subset(source, out / name, points, "Paper Times Fallback")
        rules.append(
            font_rule(
                "Paper Times Fallback",
                name,
                weight,
                "italic" if "italic" in style else "normal",
                points,
            )
        )
    rules.append("""
:root {
  --font-serif: "Times New Roman", "Paper Times Fallback", "Paper Han Serif", "Source Han Serif SC", serif;
  --font-cjk: var(--font-serif);
  --font-mono: "Paper Maple Mono", "Maple Mono CN", "Paper Han Serif", monospace;
}
code, pre, kbd, samp { font-family: var(--font-mono); }
""")
    (out / "fonts.css").write_text("\n".join(rules), encoding="utf-8")
    for family in ("han", "maple", "tinos"):
        (out / f"{family}-OFL.txt").write_bytes(sources[f"{family}-license.txt"].read_bytes())
    notice = (
        "Self-hosted fonts: Source Han Serif SC 2.003, Maple Mono CN v7.9, Tinos.\n"
        "All are SIL Open Font License 1.1; full copyright and licenses accompany this file.\n"
        "Subsets renamed Paper Han Serif, Paper Maple Mono and Paper Times Fallback.\n"
        "Tinos is a Times-compatible fallback, not Microsoft Times New Roman.\n"
        "Subset modifications: used glyphs only; WOFF2 conversion and family renaming.\n\n"
    )
    notice += LOCK.read_text(encoding="utf-8")
    (out / "NOTICE.txt").write_text(notice, encoding="utf-8")
    print(
        f"Installed {len(list(out.glob('*.woff2')))} subsets, {sum(p.stat().st_size for p in out.glob('*.woff2')) / 1048576:.2f} MiB"
    )


def main() -> int:
    """Install font assets into an already staged reader-only site."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    if not (args.site / "site-manifest.json").is_file():
        parser.error("export the reader-only site first with tools/pages.py")
    install_fonts(args.site, args.cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
