"""Per-paper manifests: identity, source location, section map, and expectations.

The pipeline serves any number of translated papers. Everything that differs between them
lives in ``papers/<slug>/paper.json`` plus that folder's ``content/``, ``glossary.md`` and
``assets/figures/``; everything that is the same for all papers (template, styles, reader
script, subset fonts) stays shared under ``src/``.

A manifest looks like this::

    {
      "title": "文档标题",
      "subtitle": "副标题",
      "author": "DeepSeek-AI",
      "source": {"pdf": ".local/source/<slug>/paper.pdf"},
      "columns": 2,
      "sections": [{"name": "00-front", "first": 1, "last": 3}],
      "expectations": {"headings": ["## 摘要"], "figures": [1], "tables": [1], "equations": [1]}
    }

``sections`` drives extraction: the printed page ranges of the source PDF, used to write the
per-section text dumps a translation session reads. ``expectations`` drives the coverage
checker: what the finished translation must contain.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS_DIR = ROOT / "papers"
DIST_DIR = ROOT / "dist"
LOCAL_SOURCE_DIR = ROOT / ".local" / "source"

MANIFEST_NAME = "paper.json"

_ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class PaperError(ValueError):
    """Raised when a paper cannot be resolved or its manifest is unusable."""


def safe_filename(title: str) -> str:
    """Turn a document title into a filename that is legal on Windows.

    Windows-illegal characters and control characters become ``-``; CJK is preserved, so the
    deliverable keeps its Chinese title.
    """
    name = _ILLEGAL_FILENAME_CHARS.sub("-", title)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.rstrip(". ")
    name = re.sub(r"-{2,}", "-", name).strip("- ")
    return name or "paper"


@dataclass(frozen=True)
class SectionRange:
    """One extracted section: a name and the inclusive printed page range."""

    name: str
    first_page: int
    last_page: int


@dataclass(frozen=True)
class Expectations:
    """What the coverage checker demands of the finished translation."""

    headings: list[str] = field(default_factory=list)
    figures: list[int] = field(default_factory=list)
    tables: list[int] = field(default_factory=list)
    equations: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class Paper:
    """One registered paper and every path derived from its slug."""

    slug: str
    directory: Path
    title: str
    subtitle: str
    author: str
    source_pdf: Path
    sections: list[SectionRange]
    expectations: Expectations
    columns: int = 1

    @property
    def content_dir(self) -> Path:
        """Markdown translation files, one per section."""
        return self.directory / "content"

    @property
    def glossary_path(self) -> Path:
        """Binding terminology table for this paper."""
        return self.directory / "glossary.md"

    @property
    def figures_dir(self) -> Path:
        """Committed figure crops extracted from the source PDF."""
        return self.directory / "assets" / "figures"

    @property
    def source_dir(self) -> Path:
        """Local-only extraction workspace for this paper."""
        return LOCAL_SOURCE_DIR / self.slug

    @property
    def pages_dir(self) -> Path:
        """Per-page plain text dumps."""
        return self.source_dir / "pages"

    @property
    def pages_png_dir(self) -> Path:
        """Per-page rasters, used to read formulas and table layout by eye."""
        return self.source_dir / "pages-png"

    @property
    def sections_dir(self) -> Path:
        """Section-level text dumps."""
        return self.source_dir / "sections"

    @property
    def report_path(self) -> Path:
        """Extraction inventory consumed by the coverage checker."""
        return self.source_dir / "report.json"

    @property
    def dist_dir(self) -> Path:
        """Intermediate multi-file build for this paper."""
        return DIST_DIR / "build" / self.slug

    @property
    def output_name(self) -> str:
        """Filename of the packed, self-contained deliverable."""
        return f"{safe_filename(self.title)}.html"

    @property
    def output_path(self) -> Path:
        """Path of the packed, self-contained deliverable."""
        return DIST_DIR / self.output_name


def manifest_path(slug: str) -> Path:
    """Return the manifest path for ``slug``."""
    return PAPERS_DIR / slug / MANIFEST_NAME


def available() -> list[str]:
    """Return the slugs of every registered paper, sorted."""
    if not PAPERS_DIR.exists():
        return []
    return sorted(p.parent.name for p in PAPERS_DIR.glob(f"*/{MANIFEST_NAME}"))


def _require(data: dict[str, object], key: str, slug: str, kind: type) -> object:
    """Return ``data[key]`` or raise a manifest error naming the paper and field."""
    if key not in data:
        raise PaperError(f"{MANIFEST_NAME} for {slug!r} is missing {key!r}")
    value = data[key]
    if not isinstance(value, kind):
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: {key!r} must be {kind.__name__}")
    return value


def _parse_sections(raw: object, slug: str) -> list[SectionRange]:
    """Parse the ``sections`` list, validating each entry."""
    if not isinstance(raw, list) or not raw:
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'sections' must be a non-empty list")
    sections: list[SectionRange] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise PaperError(f"{MANIFEST_NAME} for {slug!r}: a section must be an object")
        name = _require(entry, "name", slug, str)
        first = _require(entry, "first", slug, int)
        last = _require(entry, "last", slug, int)
        if first < 1 or last < first:
            raise PaperError(
                f"{MANIFEST_NAME} for {slug!r}: section {name!r} has an invalid page range"
            )
        sections.append(SectionRange(str(name), int(first), int(last)))
    return sections


def _parse_expectations(raw: object, slug: str) -> Expectations:
    """Parse the ``expectations`` object, tolerating omitted keys."""
    if not isinstance(raw, dict):
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'expectations' must be an object")

    def ints(key: str) -> list[int]:
        value = raw.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, int) for v in value):
            raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'expectations.{key}' must be ints")
        return [int(v) for v in value]

    headings = raw.get("headings", [])
    if not isinstance(headings, list) or not all(isinstance(h, str) for h in headings):
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'expectations.headings' must be strings")

    return Expectations(
        headings=[str(h) for h in headings],
        figures=ints("figures"),
        tables=ints("tables"),
        equations=ints("equations"),
    )


def load(slug: str) -> Paper:
    """Load and validate the manifest for ``slug``."""
    path = manifest_path(slug)
    if not path.exists():
        known = ", ".join(available()) or "none"
        raise PaperError(f"unknown paper {slug!r} (registered papers: {known})")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PaperError(f"{MANIFEST_NAME} for {slug!r} must contain an object")

    title = _require(data, "title", slug, str)
    subtitle = _require(data, "subtitle", slug, str)
    author = _require(data, "author", slug, str)
    source = _require(data, "source", slug, dict)
    pdf = _require(source, "pdf", slug, str)

    pdf_path = Path(str(pdf))
    if not pdf_path.is_absolute():
        pdf_path = ROOT / pdf_path

    columns = data.get("columns", 1)
    if not isinstance(columns, int) or columns < 1:
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'columns' must be a positive integer")

    return Paper(
        slug=slug,
        directory=path.parent,
        title=str(title),
        subtitle=str(subtitle),
        author=str(author),
        source_pdf=pdf_path,
        sections=_parse_sections(data.get("sections"), slug),
        expectations=_parse_expectations(data.get("expectations", {}), slug),
        columns=int(columns),
    )


def all_papers() -> list[Paper]:
    """Load every registered paper."""
    return [load(slug) for slug in available()]


def resolve(slug: str | None) -> Paper:
    """Resolve ``slug``, or the only registered paper when ``slug`` is None."""
    if slug:
        return load(slug)
    slugs = available()
    if len(slugs) == 1:
        return load(slugs[0])
    if not slugs:
        raise PaperError(f"no papers registered under {PAPERS_DIR}")
    raise PaperError(f"several papers are registered; pass --paper <slug>: {', '.join(slugs)}")
