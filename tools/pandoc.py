"""Small Pandoc adapter; document syntax belongs to Pandoc, not project preprocessors."""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

from markdown.extensions.toc import nest_toc_tokens

from tools import reader


class _Headings(HTMLParser):
    """Expose rendered headings through the existing reader's TOC interface."""

    def __init__(self, html: str):
        super().__init__()
        self.tokens: list[dict] = []
        self.current: dict | None = None
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Collect already generated IDs, without guessing or changing anchors."""
        if re.fullmatch(r"h[1-4]", tag):
            values = dict(attrs)
            self.current = {"level": int(tag[1]), "id": values.get("id"), "name": ""}

    def handle_data(self, data: str) -> None:
        """Keep plain heading text, including inline mathematical symbols."""
        if self.current is not None:
            self.current["name"] += data

    def handle_endtag(self, tag: str) -> None:
        """Finish a heading while leaving nested inline elements alone."""
        if self.current is not None and tag == f"h{self.current['level']}":
            if self.current["id"]:
                self.current["name"] = escape(self.current["name"])
                self.tokens.append(self.current)
            self.current = None


def toc_tokens(html: str) -> list[dict]:
    """Return the existing nested TOC shape, derived from the actual rendered page."""
    return nest_toc_tokens(_Headings(html).tokens)


def render(documents: dict[str, str]) -> tuple[dict[str, str], str]:
    """Render one document with globally unique heading, code and footnote identities.

    Keys are internal section IDs; values are expanded canonical Markdown. Native fenced
    divs delimit fragments, so authors need no HTML wrappers. Header notes come first and
    chapters last; Pandoc's generated endnotes stay at the end of the last fragment.
    """
    try:
        import pypandoc

        version = str(pypandoc.get_pandoc_version())
    except (ImportError, OSError) as error:
        raise ValueError(
            "Pandoc is unavailable; run: python tools/dev.py setup --pandoc"
        ) from error
    if not documents:
        return {}, version
    if any(not re.fullmatch(r"[\w-]+", key) for key in documents):
        raise ValueError(
            "Pandoc section IDs must contain only letters, digits, underscores or hyphens"
        )
    source = "\n\n".join(
        f":::::::::::::::: {{#{key}}}\n\n{text}\n\n::::::::::::::::"
        for key, text in documents.items()
    )
    try:
        html = pypandoc.convert_text(
            source,
            to="html5",
            format="markdown-smart+raw_html",
            extra_args=["--mathml", "--wrap=none", "--fail-if-warnings", "--sandbox"],
        ).replace("\r\n", "\n")
    except RuntimeError as error:
        raise ValueError(f"Pandoc rendering failed: {error}") from error
    # The page contains native mathematics, not TeX waiting for a runtime renderer.
    # Canonical TeX remains in work/content; source annotations are not reading content.
    html = re.sub(
        r'<annotation encoding="application/x-tex">.*?</annotation>', "", html, flags=re.S
    )
    fragments: dict[str, str] = {}
    endnotes = ""
    for block in reader.Blocks(html).blocks:
        if not block.raw.strip():
            continue
        key = block.attrs.get("id")
        if block.tag == "div" and key in documents and key not in fragments:
            fragments[key] = block.raw[block.raw.index(">") + 1 : block.raw.rfind("</div>")]
        elif block.tag == "section" and "footnotes" in block.attrs.get("class", "").split():
            endnotes += block.raw
        else:
            raise ValueError("Pandoc lost a document boundary; check balanced fenced divs/HTML")
    if set(fragments) != set(documents):
        raise ValueError("Pandoc lost a document boundary; check balanced fenced divs/HTML")
    fragments[next(reversed(documents))] += endnotes
    return fragments, version
