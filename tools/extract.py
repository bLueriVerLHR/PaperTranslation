"""Extract source text, page rasters, and figure crops from the report PDF.

The tool is idempotent: re-running it on an unchanged PDF reports the assets as
unchanged instead of rewriting them.

Outputs
-------
``.local/source/pages/page-NN.txt``
    Per-page plain text in reading order (PyMuPDF ``sort=True``).
``.local/source/pages-png/page-NN.png``
    Per-page raster at ``--page-dpi`` for visual inspection of formulas.
``src/assets/figures/figure-NN.png``
    Cropped figure regions, committed because the deliverable needs them.
``.local/source/report.json``
    Machine-readable inventory: page count, sections, figures, equations.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / ".local" / "source" / "DeepSeek_V41_Tech_Report.pdf"
PAGES_DIR = ROOT / ".local" / "source" / "pages"
PAGES_PNG_DIR = ROOT / ".local" / "source" / "pages-png"
FIGURES_DIR = ROOT / "src" / "assets" / "figures"
REPORT_PATH = ROOT / ".local" / "source" / "report.json"

CAPTION_RE = re.compile(r"^Figure\s+(\d+)\s*[|:]")
EQUATION_RE = re.compile(r"\(\s*(\d{1,2})\s*\)\s*$")
HEADING_RE = re.compile(r"^(?:\d+(?:\.\d+)*|[A-C])\.?\s+\S")

# Section boundaries as printed in the table of contents (1-based PDF pages).
SECTION_MAP: list[tuple[str, int, int]] = [
    ("00-front", 1, 3),
    ("01-introduction", 4, 6),
    ("02-architecture", 7, 15),
    ("03-infrastructures", 16, 19),
    ("04-pretraining", 20, 24),
    ("05-posttraining", 25, 36),
    ("06-conclusion", 37, 45),
    ("07-references", 38, 45),
    ("08-appendix-a-authors", 46, 47),
    ("09-appendix-b", 47, 49),
    ("10-appendix-c", 49, 51),
]

FIG_PAD = 6.0  # points of padding around an auto-detected figure region
CLUSTER_GAP = 14.0  # points; content rects closer than this belong to one figure
MIN_RECT = 4.0  # ignore hairline rules and dots


def _expand(rect: fitz.Rect, pad: float) -> fitz.Rect:
    """Grow a rectangle by ``pad`` points on every side."""
    return fitz.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad)


def _display_path(path: Path) -> str:
    """Return a repository-relative POSIX path when possible."""
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


@dataclass
class FigureRecord:
    """One detected figure and the region it was cropped from."""

    number: int
    page: int
    caption: str
    bbox: list[float]
    path: str
    width: int
    height: int
    changed: bool


@dataclass
class EquationRecord:
    """One numbered display equation."""

    number: int
    page: int
    line: str


@dataclass
class Report:
    """Full extraction inventory."""

    pdf: str
    page_count: int
    body_font_size: float
    figures: list[FigureRecord] = field(default_factory=list)
    equations: list[EquationRecord] = field(default_factory=list)
    sections: list[dict[str, object]] = field(default_factory=list)


def _write_if_changed(path: Path, data: bytes) -> bool:
    """Write ``data`` to ``path`` only when the content differs.

    Returns True when the file was written (created or updated).
    """
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def _block_texts(page: fitz.Page) -> list[tuple[fitz.Rect, str]]:
    """Return text blocks as (rect, text) pairs."""
    out: list[tuple[fitz.Rect, str]] = []
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks", sort=True):
        if text.strip():
            out.append((fitz.Rect(x0, y0, x1, y1), text))
    return out


def _body_font_size(doc: fitz.Document) -> float:
    """Return the dominant span font size across the document (weighted by chars)."""
    totals: dict[float, int] = {}
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    size = round(span["size"] * 2) / 2
                    totals[size] = totals.get(size, 0) + len(span["text"])
    if not totals:
        return 10.0
    return max(totals.items(), key=lambda kv: kv[1])[0]


def _content_rects(page: fitz.Page) -> list[fitz.Rect]:
    """Return drawing and image rectangles that could belong to a figure."""
    page_area = page.rect.get_area()
    rects: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.width <= MIN_RECT or rect.height <= MIN_RECT:
            continue
        if rect.get_area() > 0.9 * page_area:
            continue  # page background, not figure content
        rects.append(rect)
    for image in page.get_images(full=True):
        for rect in page.get_image_rects(image[0]):
            if rect.width > MIN_RECT and rect.height > MIN_RECT:
                rects.append(rect)
    return rects


def _figure_region(page: fitz.Page, caption: fitz.Rect) -> fitz.Rect:
    """Infer the figure region that belongs to a caption.

    Subfigure labels such as ``(a)``/``(b)`` sit between the artwork and the caption, so
    the region cannot simply end at the previous text block. Instead the artwork is
    clustered upward from the caption by proximity, and the box is then extended down to
    the caption to absorb the labels.
    """
    content = [r for r in _content_rects(page) if r.y1 <= caption.y0 + 2]
    if content:
        seed = max(content, key=lambda r: r.y1)
        cluster = [seed]
        remaining = [r for r in content if r != seed]
        changed = True
        while changed:
            changed = False
            for rect in list(remaining):
                if any(_expand(member, CLUSTER_GAP).intersects(rect) for member in cluster):
                    cluster.append(rect)
                    remaining.remove(rect)
                    changed = True
        region = cluster[0]
        for rect in cluster[1:]:
            region = region | rect
        region = fitz.Rect(region.x0, region.y0, region.x1, caption.y0 - 2)
        region = fitz.Rect(
            region.x0 - FIG_PAD,
            region.y0 - FIG_PAD,
            region.x1 + FIG_PAD,
            caption.y0 - 4,
        )
        return region & page.rect

    # No artwork found (rare); fall back to the whitespace band above the caption.
    blocks = _block_texts(page)
    top = page.rect.y0 + 24.0
    for rect, _text in blocks:
        if rect.y1 <= caption.y0 - 1.0:
            top = max(top, rect.y1)
    return fitz.Rect(page.rect.x0 + 12, top, page.rect.x1 - 12, caption.y0 - 2) & page.rect


def extract_figures(
    doc: fitz.Document, dpi: int, out_dir: Path = FIGURES_DIR
) -> list[FigureRecord]:
    """Detect figure captions and crop the region above each one."""
    records: list[FigureRecord] = []
    seen: set[int] = set()
    for pno in range(doc.page_count):
        page = doc[pno]
        for rect, text in _block_texts(page):
            first = text.strip().splitlines()[0].strip()
            match = CAPTION_RE.match(first)
            if not match:
                continue
            number = int(match.group(1))
            if number in seen:
                continue
            seen.add(number)
            region = _figure_region(page, rect)
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=region, alpha=False
            )
            target = out_dir / f"figure-{number:02d}.png"
            changed = _write_if_changed(target, pixmap.tobytes("png"))
            records.append(
                FigureRecord(
                    number=number,
                    page=pno + 1,
                    caption=first,
                    bbox=[round(v, 1) for v in region],
                    path=_display_path(target),
                    width=pixmap.width,
                    height=pixmap.height,
                    changed=changed,
                )
            )
    records.sort(key=lambda r: r.number)
    return records


def extract_pages(doc: fitz.Document, page_dpi: int) -> None:
    """Write per-page text and raster images."""
    for pno in range(doc.page_count):
        page = doc[pno]
        text = page.get_text("text", sort=True)
        _write_if_changed(
            PAGES_DIR / f"page-{pno + 1:02d}.txt", text.replace("\n", "\r\n").encode("utf-8")
        )
        pixmap = page.get_pixmap(matrix=fitz.Matrix(page_dpi / 72, page_dpi / 72), alpha=False)
        _write_if_changed(PAGES_PNG_DIR / f"page-{pno + 1:02d}.png", pixmap.tobytes("png"))


def find_equations(doc: fitz.Document) -> list[EquationRecord]:
    """Locate numbered display equations from line-final ``(N)`` markers."""
    found: dict[int, EquationRecord] = {}
    for pno in range(doc.page_count):
        for line in doc[pno].get_text("text", sort=True).splitlines():
            match = EQUATION_RE.search(line)
            if not match:
                continue
            number = int(match.group(1))
            if not (1 <= number <= 99) or number in found:
                continue
            stripped = line.strip()
            if len(stripped) < 4:
                continue
            found[number] = EquationRecord(number=number, page=pno + 1, line=stripped)
    return [found[k] for k in sorted(found)]


def build_sections(doc: fitz.Document) -> list[dict[str, object]]:
    """Write section text files from the printed page ranges."""
    out_dir = ROOT / ".local" / "source" / "sections"
    sections: list[dict[str, object]] = []
    for name, first, last in SECTION_MAP:
        last = min(last, doc.page_count)
        if first > last:
            continue
        chunks = [doc[p - 1].get_text("text", sort=True) for p in range(first, last + 1)]
        text = "".join(chunks)
        _write_if_changed(out_dir / f"{name}.txt", text.replace("\n", "\r\n").encode("utf-8"))
        headings = [
            line.strip()
            for line in text.splitlines()
            if HEADING_RE.match(line.strip()) and len(line.strip()) < 90
        ]
        sections.append(
            {"name": name, "first_page": first, "last_page": last, "headings": headings}
        )
    return sections


def probe(doc: fitz.Document) -> None:
    """Print heading-candidate blocks with their font sizes (debug aid)."""
    for pno in range(doc.page_count):
        page = doc[pno]
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                if not text or not HEADING_RE.match(text):
                    continue
                size = max(span["size"] for span in line["spans"])
                print(f"p{pno + 1:02d} {size:5.1f} {text[:80]}")


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--figure-dpi", type=int, default=300)
    parser.add_argument("--page-dpi", type=int, default=200)
    parser.add_argument("--probe", action="store_true", help="print heading candidates and exit")
    parser.add_argument("--skip-pages", action="store_true", help="skip per-page text/raster dump")
    parser.add_argument("--figures-only", action="store_true", help="rebuild figures only")
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        parser.error(f"source PDF not found: {args.pdf}")

    doc = fitz.open(args.pdf)
    if args.probe:
        probe(doc)
        return 0

    body_size = _body_font_size(doc)
    if not args.skip_pages:
        extract_pages(doc, args.page_dpi)
    figures = extract_figures(doc, args.figure_dpi)
    if args.figures_only:
        changed = sum(1 for f in figures if f.changed)
        print(f"figures          : {len(figures)} ({changed} written)")
        for fig in figures:
            flag = "written" if fig.changed else "same   "
            print(f"  figure {fig.number:>2} p{fig.page:<3} {fig.width}x{fig.height} {flag}")
        return 0
    equations = find_equations(doc)
    sections = build_sections(doc)

    report = Report(
        pdf=str(args.pdf),
        page_count=doc.page_count,
        body_font_size=body_size,
        figures=figures,
        equations=equations,
        sections=sections,
    )
    REPORT_PATH.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    changed = sum(1 for f in figures if f.changed)
    print(f"pages            : {report.page_count}")
    print(f"body font size   : {body_size}")
    print(
        f"figures          : {len(figures)} ({changed} written, {len(figures) - changed} unchanged)"
    )
    for fig in figures:
        flag = "written" if fig.changed else "same   "
        print(f"  figure {fig.number:>2} p{fig.page:<3} {fig.width}x{fig.height} {flag}")
    print(f"equations        : {len(equations)} -> {[e.number for e in equations]}")
    print(f"report           : {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
