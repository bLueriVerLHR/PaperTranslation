"""Extract source text, page rasters, and figure crops from a paper's PDF.

The tool is idempotent: re-running it on an unchanged PDF reports the assets as
unchanged instead of rewriting them.

The paper to extract is a registered manifest under ``papers/`` (see ``tools/paper.py``); it
supplies the source PDF path, the printed section map, and every output location.

Outputs
-------
``.local/source/<slug>/pages/page-NN.txt``
    Per-page plain text in reading order (PyMuPDF ``sort=True``).
``.local/source/<slug>/pages-png/page-NN.png``
    Per-page raster at ``--page-dpi`` for visual inspection of formulas.
``papers/<slug>/assets/figures/figure-NN.png``
    Cropped figure regions, committed because the deliverable needs them.
``.local/source/<slug>/report.json``
    Machine-readable inventory: page count, sections, figures, equations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `python tools/extract.py` to import the package
    sys.path.insert(0, str(ROOT))

from tools import paper  # noqa: E402  (must follow the sys.path bootstrap above)

# Caption styles seen in practice: "Figure 1 | ..." / "Figure 1: ..." (DeepSeek), "Fig. 1. ..."
# (Elsevier) and "Fig. 1 <EN SPACE> title" (Springer, as in Artificial Intelligence Review, where
# the en space extracts as U+00B7). The separator after the number must be punctuation, a symbol,
# or a non-ASCII space; a plain ASCII space is not enough, because that is also how running prose
# mentions a figure ("Fig. 1 shows ...").
CAPTION_SEPARATOR = r"(?:[^\w\s]|[\u00a0\u1680\u2000-\u200b\u202f\u205f\u3000])"
CAPTION_RE = re.compile(rf"^(?:Figure|Fig\.?)\s+(\d+)\s*{CAPTION_SEPARATOR}")
EQUATION_RE = re.compile(r"\(\s*(\d{1,2})\s*\)\s*$")
# A trailing "(1)" is only an equation number when the line is not a prose enumeration such as
# "two groups: (1)" (DeepSeek) or "... reduce cloud calls by 40-50%. (2)" (the on-device survey).
# Both end the text before the marker with a colon or sentence-ending punctuation, which a display
# equation's right-aligned label does not.
ENUMERATION_RE = re.compile(r"[:\uff1a]\s*\(\s*\d{1,2}\s*\)\s*$")
_SENTENCE_END = ".:,;?!\u3002\uff0c\uff1a\uff1b\u201d\u300d"
HEADING_RE = re.compile(r"^(?:\d+(?:\.\d+)*|[A-C])\.?\s+\S")

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

    slug: str
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


def _page_text(page: fitz.Page, columns: int = 1) -> str:
    """Return one page's text in reading order.

    ``columns=1`` uses PyMuPDF's own ordering, which is correct for single-column papers.
    Multi-column papers interleave their columns under that ordering, so a two-column page is
    rebuilt explicitly: full-width blocks split the page into horizontal bands, and each band is
    read left column first, then right column.
    """
    if columns < 2:
        return page.get_text("text", sort=True)

    mid = (page.rect.x0 + page.rect.x1) / 2
    left: list[tuple[fitz.Rect, str]] = []
    right: list[tuple[fitz.Rect, str]] = []
    spanning: list[tuple[fitz.Rect, str]] = []
    for rect, text in _block_texts(page):
        if rect.x0 < mid - 2 and rect.x1 > mid + 2:
            spanning.append((rect, text))
        elif (rect.x0 + rect.x1) / 2 < mid:
            left.append((rect, text))
        else:
            right.append((rect, text))
    spanning.sort(key=lambda block: block[0].y0)

    bounds: list[tuple[float, float]] = []
    top = page.rect.y0
    for rect, _text in spanning:
        bounds.append((top, rect.y0))
        top = rect.y1
    bounds.append((top, page.rect.y1))

    lines: list[str] = []
    for index, (band_top, band_bottom) in enumerate(bounds):
        for column in (left, right):
            for rect, text in sorted(column, key=lambda block: block[0].y0):
                if band_top - 1 <= rect.y0 < band_bottom:
                    lines.append(text.strip())
        if index < len(spanning):
            lines.append(spanning[index][1].strip())
    return "\n".join(lines) + "\n"


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
    texts = [rect for rect, _text in _block_texts(page)]
    rects: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.width <= MIN_RECT or rect.height <= MIN_RECT:
            continue
        if rect.get_area() > 0.9 * page_area:
            continue  # page background, not figure content
        if any(_expand(text, 1.0).contains(rect) for text in texts):
            # Text drawn as vector art (running heads, page numbers) is covered by its own
            # text block; keeping it would drag a figure crop up over the page header.
            continue
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


def extract_figures(doc: fitz.Document, dpi: int, out_dir: Path) -> list[FigureRecord]:
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


def extract_pages(
    doc: fitz.Document, page_dpi: int, pages_dir: Path, pages_png_dir: Path, columns: int = 1
) -> None:
    """Write per-page text and raster images."""
    for pno in range(doc.page_count):
        page = doc[pno]
        text = _page_text(page, columns)
        _write_if_changed(
            pages_dir / f"page-{pno + 1:02d}.txt", text.replace("\n", "\r\n").encode("utf-8")
        )
        pixmap = page.get_pixmap(matrix=fitz.Matrix(page_dpi / 72, page_dpi / 72), alpha=False)
        _write_if_changed(pages_png_dir / f"page-{pno + 1:02d}.png", pixmap.tobytes("png"))


def _looks_like_equation(line: str) -> bool:
    """Decide whether a line carrying a final ``(N)`` really is a display equation.

    Prose enumerations end the line the same way - ``two groups: (1)``, ``... by 40-50%. (2)`` -
    so the text before the marker is inspected: if it ends with a colon or with sentence-ending
    punctuation, the number belongs to the sentence and not to an equation. A right-aligned
    display-equation label follows the formula itself, which ends in a symbol or a variable
    rather than in prose punctuation.
    """
    match = EQUATION_RE.search(line)
    if match is None:
        return False
    body = line.strip()[: match.start()].rstrip()
    if not body or body[-1] in _SENTENCE_END:
        return False
    return ENUMERATION_RE.search(body) is None


def find_equations(doc: fitz.Document, columns: int = 1) -> list[EquationRecord]:
    """Locate numbered display equations from line-final ``(N)`` markers."""
    found: dict[int, EquationRecord] = {}
    for pno in range(doc.page_count):
        for line in _page_text(doc[pno], columns).splitlines():
            match = EQUATION_RE.search(line)
            if not match:
                continue
            number = int(match.group(1))
            if not (1 <= number <= 99) or number in found:
                continue
            stripped = line.strip()
            if len(stripped) < 4 or not _looks_like_equation(stripped):
                continue
            found[number] = EquationRecord(number=number, page=pno + 1, line=stripped)
    return [found[k] for k in sorted(found)]


def build_sections(
    doc: fitz.Document, sections: list[paper.SectionRange], out_dir: Path, columns: int = 1
) -> list[dict[str, object]]:
    """Write section text files from the manifest's printed page ranges."""
    written: list[dict[str, object]] = []
    for section in sections:
        last = min(section.last_page, doc.page_count)
        if section.first_page > last:
            continue
        chunks = [_page_text(doc[p - 1], columns) for p in range(section.first_page, last + 1)]
        text = "".join(chunks)
        _write_if_changed(
            out_dir / f"{section.name}.txt", text.replace("\n", "\r\n").encode("utf-8")
        )
        headings = [
            line.strip()
            for line in text.splitlines()
            if HEADING_RE.match(line.strip()) and len(line.strip()) < 90
        ]
        written.append(
            {
                "name": section.name,
                "first_page": section.first_page,
                "last_page": last,
                "headings": headings,
            }
        )
    return written


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
    parser.add_argument("--paper", default=None, help="registered paper slug")
    parser.add_argument("--pdf", type=Path, default=None, help="override the source PDF path")
    parser.add_argument("--figure-dpi", type=int, default=300)
    parser.add_argument("--page-dpi", type=int, default=200)
    parser.add_argument("--probe", action="store_true", help="print heading candidates and exit")
    parser.add_argument("--skip-pages", action="store_true", help="skip per-page text/raster dump")
    parser.add_argument("--figures-only", action="store_true", help="rebuild figures only")
    args = parser.parse_args(argv)

    current = paper.resolve(args.paper)
    pdf_path = args.pdf or current.source_pdf
    if not pdf_path.exists():
        parser.error(f"source PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    if args.probe:
        probe(doc)
        return 0

    body_size = _body_font_size(doc)
    if not args.skip_pages:
        extract_pages(doc, args.page_dpi, current.pages_dir, current.pages_png_dir, current.columns)
    figures = extract_figures(doc, args.figure_dpi, current.figures_dir)
    if args.figures_only:
        changed = sum(1 for f in figures if f.changed)
        print(f"figures          : {len(figures)} ({changed} written)")
        for fig in figures:
            flag = "written" if fig.changed else "same   "
            print(f"  figure {fig.number:>2} p{fig.page:<3} {fig.width}x{fig.height} {flag}")
        return 0
    equations = find_equations(doc, current.columns)
    sections = build_sections(doc, current.sections, current.sections_dir, current.columns)

    report = Report(
        slug=current.slug,
        pdf=_display_path(pdf_path),
        page_count=doc.page_count,
        body_font_size=body_size,
        figures=figures,
        equations=equations,
        sections=sections,
    )
    current.report_path.parent.mkdir(parents=True, exist_ok=True)
    current.report_path.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    changed = sum(1 for f in figures if f.changed)
    print(f"paper            : {current.slug} ({current.title})")
    print(f"pages            : {report.page_count}")
    print(f"columns          : {current.columns}")
    print(f"body font size   : {body_size}")
    print(
        f"figures          : {len(figures)} ({changed} written, {len(figures) - changed} unchanged)"
    )
    for fig in figures:
        flag = "written" if fig.changed else "same   "
        print(f"  figure {fig.number:>2} p{fig.page:<3} {fig.width}x{fig.height} {flag}")
    print(f"equations        : {len(equations)} -> {[e.number for e in equations]}")
    print(f"report           : {_display_path(current.report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
