"""Per-paper manifests: identity, source location, section map, and expectations.

The pipeline serves any number of translated papers. Everything that differs between them
lives in ``dist/<slug>/work/paper.json`` plus that folder's ``content/``, ``glossary.md`` and
``assets/figures/``; everything that is the same for all papers (template, styles, reader
script) stays shared under ``src/``.

The slug doubles as the deliverable folder name, so it is restricted to a lowercase English
identifier: the reader page and its asset tree live in ``dist/<slug>/``.

A manifest looks like this::

    {
      "title": "文档标题",
      "subtitle": "副标题",
      "author": "DeepSeek-AI",
      "source": {"pdf": null},
      "columns": 2,
      "sections": [{"name": "00-front", "first": 1, "last": 3}],
      "expectations": {"headings": ["## 摘要"], "figures": [1], "tables": [1], "equations": [1]}
    }

``sections`` drives extraction: the printed page ranges of the source PDF, used to write the
per-section text dumps a translation session reads. ``expectations`` drives the coverage
checker: what the finished translation must contain.

A source that was published as a web page instead of a PDF names it with ``source.web``, and
its sections carry a ``url`` instead of a page range::

    {
      "title": "教程标题",
      "subtitle": "副标题",
      "author": "Sonny Li",
      "source": {"web": {"base": "https://example.invalid/", "index": "https://example.invalid/contentIndex.json"}},
      "sections": [{"name": "01-intro", "url": "series/Part-1"}]
    }

``base`` is the site root those relative ``url``s hang off; ``index`` is optional and, when the
site publishes one, names a machine-readable index of the same prose that a reconstructing tool
can cross-check against. A paper has exactly one of ``source.pdf`` and ``source.web``.
``source.pdf`` may be null: rebuilding uses retained work materials, while re-extraction
requires an external original supplied with ``extract.py --pdf``. PDFs are never copied
into the project's work or deliverable folders.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
WORK_DIR_NAME = "work"

MANIFEST_NAME = "paper.json"

# A slug names a folder inside dist/, so it is held to an ASCII path-safe identifier.
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PaperError(ValueError):
    """Raised when a paper cannot be resolved or its manifest is unusable."""


@dataclass(frozen=True)
class SectionRange:
    """One extracted section: a name and either a printed page range or a source URL.

    A PDF paper addresses its sections by inclusive printed page range; a web paper addresses
    them by a site-relative URL. Exactly one of the two is set, and ``url`` is relative to
    :attr:`WebSource.base`.
    """

    name: str
    first_page: int | None
    last_page: int | None
    url: str | None = None

    @property
    def is_web(self) -> bool:
        """True when this section is fetched from the web rather than read from a PDF."""
        return self.url is not None


@dataclass(frozen=True)
class WebSource:
    """A source published as a web page rather than a PDF.

    ``base`` is the site root that every section URL hangs off. ``index`` optionally names a
    machine-readable document index the site publishes (Quartz serves one at
    ``/static/contentIndex.json``); a reconstructing tool can use it to cross-check prose that
    the rendered markup makes hard to read, such as LaTeX that only survives as vector art.
    """

    base: str
    index: str | None = None

    def absolute(self, url: str) -> str:
        """Return ``url`` resolved against this source's base."""
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            return url
        return urljoin(self.base, url)


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
    source_pdf: Path | None
    sections: list[SectionRange]
    expectations: Expectations
    columns: int = 1
    source_web: WebSource | None = None

    @property
    def is_web(self) -> bool:
        """True when this paper's source is a web page rather than a PDF."""
        return self.source_web is not None

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
        """Local-only figure crops needed to rebuild the deliverable."""
        return self.directory / "assets" / "figures"

    @property
    def source_dir(self) -> Path:
        """Retained reference text and rasters, alongside the translation sources."""
        return self.directory / "reference"

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
    def output_dir(self) -> Path:
        """Deliverable folder for this paper: ``dist/<slug>/``."""
        return DIST_DIR / self.slug

    @property
    def output_path(self) -> Path:
        """Reader page inside the deliverable folder."""
        return self.output_dir / "index.html"


def manifest_path(slug: str) -> Path:
    """Return the manifest path for ``slug``."""
    return DIST_DIR / slug / WORK_DIR_NAME / MANIFEST_NAME


def available() -> list[str]:
    """Return the slugs of every registered paper, sorted."""
    if not DIST_DIR.exists():
        return []
    return sorted(p.parents[1].name for p in DIST_DIR.glob(f"*/{WORK_DIR_NAME}/{MANIFEST_NAME}"))


def _require(data: dict[str, object], key: str, slug: str, kind: type) -> object:
    """Return ``data[key]`` or raise a manifest error naming the paper and field."""
    if key not in data:
        raise PaperError(f"{MANIFEST_NAME} for {slug!r} is missing {key!r}")
    value = data[key]
    if not isinstance(value, kind):
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: {key!r} must be {kind.__name__}")
    return value


def _parse_sections(raw: object, slug: str, web: WebSource | None = None) -> list[SectionRange]:
    """Parse the ``sections`` list, validating each entry.

    A web paper names each section by URL (relative to ``web.base``); a PDF paper names it by
    inclusive printed page range. The two are not mixed inside one manifest.
    """
    if not isinstance(raw, list) or not raw:
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'sections' must be a non-empty list")
    sections: list[SectionRange] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise PaperError(f"{MANIFEST_NAME} for {slug!r}: a section must be an object")
        name = _require(entry, "name", slug, str)
        if web is not None:
            if "url" not in entry:
                raise PaperError(
                    f"{MANIFEST_NAME} for {slug!r}: web section {name!r} needs a 'url'"
                )
            url = _require(entry, "url", slug, str)
            sections.append(SectionRange(str(name), None, None, str(url)))
            continue
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


def _parse_web_source(raw: object, slug: str) -> WebSource:
    """Parse the ``source.web`` object."""
    if not isinstance(raw, dict):
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'source.web' must be an object")
    base = _require(raw, "base", slug, str)
    index = raw.get("index")
    if index is not None and not isinstance(index, str):
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'source.web.index' must be a string")
    return WebSource(base=str(base), index=str(index) if index is not None else None)


def load(slug: str) -> Paper:
    """Load and validate the manifest for ``slug``."""
    path = manifest_path(slug)
    if not path.exists():
        known = ", ".join(available()) or "none"
        raise PaperError(f"unknown paper {slug!r} (registered papers: {known})")
    if not SLUG_RE.match(slug):
        raise PaperError(
            f"invalid paper slug {slug!r}: the slug names the deliverable folder "
            "dist/<slug>/, so use lowercase ASCII words joined by '-'"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PaperError(f"{MANIFEST_NAME} for {slug!r} must contain an object")

    title = _require(data, "title", slug, str)
    subtitle = _require(data, "subtitle", slug, str)
    author = _require(data, "author", slug, str)
    source = _require(data, "source", slug, dict)
    if "pdf" in source and "web" in source:
        raise PaperError(
            f"{MANIFEST_NAME} for {slug!r}: 'source' names both a pdf and a web source; "
            "a paper has exactly one"
        )
    if "web" in source:
        web = _parse_web_source(source["web"], slug)
        pdf_path = None
    elif "pdf" in source:
        web = None
        pdf = source["pdf"]
        if pdf is not None and not isinstance(pdf, str):
            raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'pdf' must be a path or null")
        pdf_path = Path(pdf) if pdf is not None else None
        if pdf_path is not None and not pdf_path.is_absolute():
            pdf_path = ROOT / pdf_path
    else:
        raise PaperError(f"{MANIFEST_NAME} for {slug!r}: 'source' needs either 'pdf' or 'web'")

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
        sections=_parse_sections(data.get("sections"), slug, web),
        expectations=_parse_expectations(data.get("expectations", {}), slug),
        columns=int(columns),
        source_web=web,
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
        raise PaperError(f"no papers registered under {DIST_DIR}/*/{WORK_DIR_NAME}")
    raise PaperError(f"several papers are registered; pass --paper <slug>: {', '.join(slugs)}")
