"""Build the multi-direction LLM survey site from local Markdown and per-paper metadata.

This is a separate product from ``tools/build.py``: that one renders *one translated paper*,
this one renders *a survey of many papers*. The survey is written by hand under ``survey/`` -
narrative prose per direction, plus one folder per surveyed paper - and this tool turns it into
``dist/survey/``: a hub page that is itself the readable survey, and one detail page per paper
carrying that paper's translated abstract.

Layout of the inputs::

    survey/survey.json          identity of the survey (title, subtitle, author, directions)
    survey/hub/NN-direction.md  the narrative, in reading order; a line ``{{paper:<slug>}}``
                                expands into that paper's card
    survey/papers/<slug>/meta.json    identity and metadata of one surveyed paper
    survey/papers/<slug>/abstract.md  the translated abstract shown on its detail page

All paper metadata lives in ``meta.json`` and nowhere else, so a card on the hub and the
corresponding detail page cannot drift apart: both are rendered from the same record. Adding a
surveyed paper means adding one folder, never editing this tool.

Usage
-----
``python tools/survey.py``
    Build ``dist/survey/index.html`` and ``dist/survey/papers/<slug>.html``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `python tools/survey.py` to import the package
    sys.path.insert(0, str(ROOT))

from tools.build import (  # noqa: E402  (must follow the sys.path bootstrap above)
    SCRIPTS_DIR,
    STYLES_DIR,
    Section,
    combine_toc,
    make_markdown,
    wrap_tables,
)

SURVEY_DIR = ROOT / "survey"
HUB_DIR = SURVEY_DIR / "hub"
PAPERS_DIR = SURVEY_DIR / "papers"
INFO_PATH = SURVEY_DIR / "survey.json"

HUB_TEMPLATE = ROOT / "src" / "templates" / "survey-hub.html"
PAPER_TEMPLATE = ROOT / "src" / "templates" / "survey-paper.html"
SURVEY_STYLES = ROOT / "src" / "survey" / "survey.css"
PAPER_ASSET_DIR = "papers"

DEFAULT_DIST = ROOT / "dist" / "survey"

#: ``{{paper:some-slug}}`` on a line of its own expands into that paper's card.
CARD_RE = re.compile(r"^[ \t]*\{\{paper:([a-z0-9]+(?:-[a-z0-9]+)*)\}\}[ \t]*$", re.MULTILINE)
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")


class SurveyError(RuntimeError):
    """Raised when the local survey tree is inconsistent."""


@dataclass
class Paper:
    """One surveyed paper: its metadata, its translated abstract and its rendered card."""

    slug: str
    directory: Path
    meta: dict
    abstract: Section | None = None

    @property
    def title_en(self) -> str:
        """The paper's own title, never translated."""
        return str(self.meta.get("title_en", self.slug))

    @property
    def title_zh(self) -> str:
        """The title as it reads after translation, for readers of the survey."""
        return str(self.meta.get("title_zh", ""))

    @property
    def venue(self) -> str:
        """Publication venue, or an empty string when unknown."""
        return str(self.meta.get("venue", ""))

    @property
    def year(self) -> str:
        """Publication year as a string, or an empty string when unknown."""
        year = self.meta.get("year")
        return str(year) if year else ""

    @property
    def arxiv(self) -> str:
        """arXiv identifier without the ``arXiv:`` prefix."""
        return str(self.meta.get("arxiv", ""))

    @property
    def doi(self) -> str:
        """DOI, when the paper has one distinct from its arXiv identifier."""
        return str(self.meta.get("doi", ""))

    @property
    def cites(self) -> int | None:
        """Citation count; unknown is distinct from a verified zero."""
        value = self.meta.get("cites")
        return int(value) if value is not None else None

    @property
    def citation_label(self) -> str:
        """Display provenance-aware counts consistently in cards and details."""
        if self.cites is None:
            return "引用量未核实"
        stamp = f"截至 {self.cites_asof}" if self.cites_asof else "日期未核实"
        return f"引用 {self.cites:,}（{stamp}）"

    @property
    def cites_asof(self) -> str:
        """Date the citation count was read, so the number can be re-checked later."""
        return str(self.meta.get("cites_asof", ""))

    @property
    def stage(self) -> str:
        """Which pipeline stage the paper belongs to (pretraining, post-training, inference)."""
        return str(self.meta.get("stage", ""))

    @property
    def filename(self) -> str:
        """File name of this paper's detail page inside ``papers/``."""
        return f"{self.slug}.html"


@dataclass
class Hub:
    """The survey's identity plus its narrative sections."""

    info: dict
    sections: list[Section] = field(default_factory=list)

    @property
    def title(self) -> str:
        """Survey title shown in the page header."""
        return str(self.info.get("title", "大语言模型调研"))

    @property
    def subtitle(self) -> str:
        """One-line description of the survey's scope."""
        return str(self.info.get("subtitle", ""))

    @property
    def author(self) -> str:
        """Who the survey is attributed to."""
        return str(self.info.get("author", ""))


def load_info(path: Path = INFO_PATH) -> dict:
    """Read the survey's identity file."""
    if not path.exists():
        raise SurveyError(f"missing survey identity file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def render_inline(text: str) -> str:
    """Render a short metadata field as inline HTML, without the wrapping paragraph."""
    rendered = make_markdown().convert(str(text or "").strip()).strip()
    if rendered.startswith("<p>") and rendered.endswith("</p>"):
        rendered = rendered[3:-4]
    return rendered


def load_paper(directory: Path) -> Paper:
    """Read one surveyed paper's metadata and translated abstract."""
    meta_path = directory / "meta.json"
    if not meta_path.exists():
        raise SurveyError(f"missing paper metadata: {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    abstract_path = directory / "abstract.md"
    abstract = None
    if abstract_path.exists():
        md = make_markdown()
        abstract = Section(
            path=abstract_path,
            identifier=f"abstract-{directory.name}",
            html=md.convert(abstract_path.read_text(encoding="utf-8")),
            tokens=list(md.toc_tokens),
        )
    return Paper(slug=directory.name, directory=directory, meta=meta, abstract=abstract)


def load_papers(papers_dir: Path = PAPERS_DIR) -> dict[str, Paper]:
    """Read every surveyed paper, keyed by slug."""
    if not papers_dir.exists():
        raise SurveyError(f"missing papers directory: {papers_dir}")
    return {path.name: load_paper(path) for path in sorted(papers_dir.iterdir()) if path.is_dir()}


def card_html(paper: Paper, asset_prefix: str = "", card_id: str | None = None) -> str:
    """Render one paper as a card for the hub.

    The card carries the paper's own title, its Chinese title, the venue/year/citation line, the
    motivation and approach summaries, and the link to the detail page.
    """
    bits = [escape(part) for part in (paper.venue, paper.year) if part]
    bits.append(escape(paper.citation_label))
    meta_line = " · ".join(bits)

    links: list[str] = []
    if paper.arxiv:
        links.append(
            f'<a href="https://arxiv.org/abs/{escape(paper.arxiv)}">arXiv:{escape(paper.arxiv)}</a>'
        )
    if paper.doi:
        links.append(f'<a href="https://doi.org/{escape(paper.doi)}">DOI</a>')
    link_line = f' <span class="paper-links">{" · ".join(links)}</span>' if links else ""

    anchor = card_id or f"paper-{paper.slug}"
    lines = [f'<aside class="paper-card" id="{escape(anchor)}">']
    lines.append(f'<p class="paper-title">{escape(paper.title_en)}</p>')
    if paper.title_zh:
        lines.append(f'<p class="paper-zh-title">{escape(paper.title_zh)}</p>')
    if meta_line or link_line:
        lines.append(f'<p class="paper-meta">{meta_line}{link_line}</p>')

    motivation = paper.meta.get("motivation", "")
    if motivation:
        lines.append(
            f'<p class="paper-why"><span class="paper-label">动机</span>'
            f"{render_inline(motivation)}</p>"
        )
    approach = paper.meta.get("approach", "")
    if approach:
        lines.append(
            f'<p class="paper-how"><span class="paper-label">方案</span>'
            f"{render_inline(approach)}</p>"
        )

    target = f"{asset_prefix}{PAPER_ASSET_DIR}/{escape(paper.filename)}"
    label = "详情页：原文摘要译文" if paper.abstract else "详情页"
    lines.append(f'<p class="paper-more"><a href="{target}">{label} →</a></p>')
    lines.append("</aside>")
    return "\n".join(lines)


def expand_cards(
    text: str,
    papers: dict[str, Paper],
    asset_prefix: str = "",
    occurrences: dict[str, int] | None = None,
) -> str:
    """Expand cards with unique anchors, including repeats across hub sections."""
    if occurrences is None:
        occurrences = {}

    def replace(match: re.Match[str]) -> str:
        slug = match.group(1)
        if slug not in papers:
            raise SurveyError(
                f"the hub references paper {slug!r}, but survey/papers/{slug}/ does not exist"
            )
        count = occurrences.get(slug, 0) + 1
        occurrences[slug] = count
        suffix = f"--{count}" if count > 1 else ""
        return card_html(papers[slug], asset_prefix, f"paper-{slug}{suffix}")

    return CARD_RE.sub(replace, text)


def reading_order(hub_dir: Path) -> list[str]:
    """Return the slugs the hub references, in the order a reader meets them."""
    order: list[str] = []
    for path in sorted(hub_dir.glob("*.md")):
        for slug in CARD_RE.findall(path.read_text(encoding="utf-8")):
            if slug not in order:
                order.append(slug)
    return order


def nav_html(current: str, order: list[str], papers: dict[str, Paper]) -> str:
    """Render previous/next links across the surveyed papers."""
    if current not in order:
        return ""
    index = order.index(current)
    parts: list[str] = []
    if index > 0:
        previous = papers[order[index - 1]]
        parts.append(
            f'<a class="nav-prev" href="{escape(previous.filename)}">'
            f"← {escape(previous.title_en)}</a>"
        )
    if index + 1 < len(order):
        following = papers[order[index + 1]]
        parts.append(
            f'<a class="nav-next" href="{escape(following.filename)}">'
            f"{escape(following.title_en)} →</a>"
        )
    if not parts:
        return ""
    return '<nav class="paper-nav">' + "\n".join(parts) + "</nav>"


def facts_html(paper: Paper) -> str:
    """Render the metadata table shown at the top of a detail page."""
    rows: list[tuple[str, str]] = []
    if paper.title_zh:
        rows.append(("中文标题", escape(paper.title_zh)))
    authors = paper.meta.get("authors", "")
    if authors:
        rows.append(("作者", escape(str(authors))))
    venue = " · ".join(part for part in (paper.venue, paper.year) if part)
    if venue:
        rows.append(("发表", escape(venue)))
    if paper.stage:
        rows.append(("阶段", escape(paper.stage)))
    rows.append(("引用", escape(paper.citation_label)))
    if paper.cites is not None and paper.meta.get("cites_source"):
        rows.append(("引用来源", escape(str(paper.meta["cites_source"]))))

    links: list[str] = []
    if paper.arxiv:
        links.append(
            f'<a href="https://arxiv.org/abs/{escape(paper.arxiv)}">arXiv:{escape(paper.arxiv)}</a>'
        )
    if paper.doi:
        links.append(f'<a href="https://doi.org/{escape(paper.doi)}">DOI</a>')
    for label, url in (paper.meta.get("links") or {}).items():
        links.append(f'<a href="{escape(str(url))}">{escape(str(label))}</a>')
    if links:
        rows.append(("原文", " · ".join(links)))

    if not rows:
        return ""
    body = "\n".join(f"    <dt>{key}</dt>\n    <dd>{value}</dd>" for key, value in rows)
    return f'<dl class="paper-facts">\n{body}\n</dl>'


def render(template: Path, replacements: dict[str, str]) -> str:
    """Substitute every placeholder, refusing to emit a page with one left unresolved."""
    page = template.read_text(encoding="utf-8")
    for token, value in replacements.items():
        page = page.replace(token, value)
    leftovers = PLACEHOLDER_RE.findall(page)
    if leftovers:
        raise SurveyError(f"unresolved template placeholders: {sorted(set(leftovers))}")
    return page


def write_assets(dist: Path) -> dict[str, list[str]]:
    """Copy the shared stylesheet, the survey stylesheet and the reader script.

    ``survey.css`` deliberately lives in ``src/survey/`` rather than ``src/styles/``: the paper
    builder copies that whole directory, so a survey stylesheet placed there would ship inside
    every translated paper's ``assets/`` as a file the page never references.
    """
    plan = {
        "assets/styles": (STYLES_DIR, SURVEY_STYLES.parent),
        "assets/scripts": (SCRIPTS_DIR,),
    }
    copied: dict[str, list[str]] = {}
    for relative, sources in plan.items():
        target = dist / relative
        target.mkdir(parents=True, exist_ok=True)
        names: list[str] = []
        for source in sources:
            if not source.exists():
                continue
            for path in sorted(source.iterdir()):
                if path.is_file():
                    shutil.copy2(path, target / path.name)
                    names.append(path.name)
        # The output folder is the deliverable, so a stylesheet or script left behind by an
        # earlier build must not survive: it would ship a file the page no longer references.
        for stale in sorted(target.iterdir()):
            if stale.is_file() and stale.name not in names:
                stale.unlink()
        copied[relative.split("/")[-1]] = sorted(set(names))
    return copied


def build(
    dist: Path = DEFAULT_DIST,
    hub_dir: Path = HUB_DIR,
    papers_dir: Path = PAPERS_DIR,
    info: dict | None = None,
    hub_template: Path = HUB_TEMPLATE,
    paper_template: Path = PAPER_TEMPLATE,
    build_date: str | None = None,
) -> dict[str, object]:
    """Build the hub page and every paper detail page, returning a manifest."""
    info = info if info is not None else load_info()
    papers = load_papers(papers_dir)
    order = reading_order(hub_dir)

    missing = [slug for slug in order if slug not in papers]
    if missing:
        raise SurveyError(f"hub references unknown papers: {missing}")
    unused = sorted(set(papers) - set(order))
    if unused:
        raise SurveyError(f"surveyed papers the hub never references: {unused}")

    # Each hub file is expanded first - a card is block HTML, which the ``md_in_html``
    # extension passes through - and only then converted, so a card's markdown inside is
    # rendered by the same instance that wrote it and no card text leaks into the TOC.
    sections: list[Section] = []
    occurrences: dict[str, int] = {}
    for path in sorted(hub_dir.glob("*.md")):
        expanded = expand_cards(path.read_text(encoding="utf-8"), papers, occurrences=occurrences)
        md = make_markdown()
        sections.append(
            Section(
                path=path,
                identifier=f"sec-{path.stem}",
                html=md.convert(expanded),
                tokens=list(md.toc_tokens),
            )
        )

    payload = {
        "info": info,
        "hub": [section.html for section in sections],
        "papers": {
            slug: {"meta": paper.meta, "abstract": paper.abstract.html if paper.abstract else None}
            for slug, paper in papers.items()
        },
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    hub = Hub(info=info, sections=sections)
    stamp = build_date or date.today().isoformat()

    dist.mkdir(parents=True, exist_ok=True)
    (dist / PAPER_ASSET_DIR).mkdir(parents=True, exist_ok=True)
    copied = write_assets(dist)

    base = {
        "{{TITLE}}": escape(hub.title),
        "{{SUBTITLE}}": escape(hub.subtitle),
        "{{AUTHOR}}": escape(hub.author),
        "{{BUILD_DATE}}": stamp,
        "{{CONTENT_HASH}}": digest,
    }

    hub_page = render(
        hub_template,
        {
            **base,
            "{{ASSET_PREFIX}}": "",
            "{{TOC}}": combine_toc(sections),
            "{{CONTENT}}": wrap_tables("\n\n".join(section.html for section in sections)),
            "{{PAPER_COUNT}}": str(len(order)),
            "{{DIRECTION_COUNT}}": str(len(info.get("directions", []))),
        },
    )
    (dist / "index.html").write_text(hub_page, encoding="utf-8")

    written: list[str] = ["index.html"]
    for slug in order:
        current = papers[slug]
        body = current.abstract.html if current.abstract else "<p>尚未翻译。</p>"
        page = render(
            paper_template,
            {
                **base,
                "{{ASSET_PREFIX}}": "../",
                "{{PAPER_TITLE}}": escape(current.title_en),
                "{{PAPER_TITLE_ZH}}": escape(current.title_zh or current.title_en),
                "{{PAPER_SLUG}}": slug,
                "{{FACTS}}": facts_html(current),
                "{{NOTES}}": (
                    '<aside class="paper-notes"><h2>阅读说明与边界</h2>'
                    + make_markdown().convert(str(current.meta["notes"]))
                    + "</aside>"
                    if current.meta.get("notes")
                    else ""
                ),
                "{{CONTENT}}": wrap_tables(body),
                "{{NAV}}": nav_html(slug, order, papers),
            },
        )
        target = dist / PAPER_ASSET_DIR / current.filename
        target.write_text(page, encoding="utf-8")
        written.append(f"{PAPER_ASSET_DIR}/{current.filename}")

    expected = {papers[slug].filename for slug in order}
    for stale in (dist / PAPER_ASSET_DIR).glob("*.html"):
        if stale.name not in expected:
            stale.unlink()

    untranslated = [slug for slug in order if not papers[slug].abstract]
    manifest = {
        "title": hub.title,
        "content_hash": digest,
        "directions": [d.get("name") for d in info.get("directions", [])],
        "papers": order,
        "papers_without_abstract": untranslated,
        "assets": copied,
        "pages": written,
    }
    (dist / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST, help="override output directory")
    parser.add_argument("--build-date", default=None)
    args = parser.parse_args(argv)

    manifest = build(dist=args.dist, build_date=args.build_date)
    print(f"survey       : {manifest['title']}")
    print(f"built        : {args.dist / 'index.html'}")
    print(f"  papers      : {len(manifest['papers'])} -> {', '.join(manifest['papers'])}")
    print(f"  pages       : {len(manifest['pages'])}")
    print(f"  styles      : {', '.join(manifest['assets']['styles'])}")
    print(f"  content hash: {manifest['content_hash']}")
    if manifest["papers_without_abstract"]:
        print(f"  no abstract : {', '.join(manifest['papers_without_abstract'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
