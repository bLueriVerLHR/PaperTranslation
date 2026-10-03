"""Reconstruct a translation-ready source from a tutorial published as a web page.

``tools/extract.py`` reads a PDF: it dumps per-page text and crops figures. A web source has
no pages, so this module reads it the other way round. For each section URL it fetches the
rendered page and rewrites the article body into source text a translation pass can read:

* prose becomes plain text with its original line structure;
* LaTeX that the site rendered to vector art becomes **MathML**, recovered from the renderer's
  own output (see :func:`container_to_mathml`), because this pipeline authors equations as
  MathML and ships no runtime math renderer;
* code blocks become fenced blocks carrying their language and caption;
* tables become HTML ``<table>`` markup with a numbered caption;
* images become ``<figure>`` blocks and their bytes are downloaded into the paper's figures
  directory under a numbered ``figure-NN.ext`` name.

Reference text is written under ``dist/<slug>/work/reference/sections/<name>.txt`` plus a
machine-readable inventory at ``dist/<slug>/work/reference/report.json``, so the coverage checker and the figure
listing work the same way they do for a PDF.

Math recovery
-------------
MathJax's SVG output is not a picture: each element keeps a ``data-mml-node`` naming the MathML
node it came from, and each glyph is a ``<use data-c="<codepoint>">``. Walking that structure
yields an exact MathML tree, so no LaTeX parsing or hand-transcription is involved. Glyph
codepoints arrive in their *styled* form (``U+1D410`` is mathematical bold capital Q), so a
light pass folds them back to plain letters and records the styling as ``mathvariant`` instead -
which is both what the source LaTeX meant and what a browser renders from a system font.

Network access
--------------
Fetching is the point of this tool, so it uses the standard library only (``urllib.request``)
rather than adding a dependency. Downloads are skipped when the destination already has the
same bytes, which keeps re-runs cheap and makes the tool idempotent like its PDF counterpart.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import http.client
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `python tools/web.py` to import the package
    sys.path.insert(0, str(ROOT))

from tools import paper  # noqa: E402  (must follow the sys.path bootstrap above)

USER_AGENT = "PaperTranslation/1.0 (+offline reading copy; contact: repo owner)"
TIMEOUT = 60.0
MAX_BYTES = 64 * 1024 * 1024
# A single dropped connection should not fail a run that may fetch a hundred assets.
RETRIES = 4
RETRY_DELAY = 1.5
_TRANSIENT = (urllib.error.URLError, http.client.HTTPException, OSError)

# Elements that never carry article prose.
DROP_TAGS = {
    "script",
    "style",
    "nav",
    "svg",
    "head",
    "meta",
    "link",
    "noscript",
    "template",
}
# Elements whose end implies a line break in the reconstructed text.
BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "main",
    "header",
    "footer",
    "aside",
    "figure",
    "figcaption",
    "pre",
    "table",
    "ul",
    "ol",
    "li",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "tr",
    "br",
    "hr",
    "details",
    "summary",
    "dl",
    "dt",
    "dd",
}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

_MATHML_NODES = {
    "math",
    "mi",
    "mn",
    "mo",
    "mtext",
    "ms",
    "mspace",
    "mrow",
    "mfrac",
    "msqrt",
    "mroot",
    "msup",
    "msub",
    "msubsup",
    "mover",
    "munder",
    "munderover",
    "mtable",
    "mtr",
    "mtd",
    "mstyle",
    "menclose",
    "mpadded",
    "mphantom",
    "annotation",
    "semantics",
    "TeXAtom",
}
# The radical glyph is drawn inside the same element as the radicand it belongs to.
_RADICAL_SIGNS = "\u221a\u221b\u221c"
# Token elements hold glyphs, never other elements.
_TOKEN_ELEMENTS = {"mi", "mn", "mo", "mtext", "ms"}
# Children in these positions inherit the style of their parent when the renderer wrapped them
# in a bare grouping atom. Keeping it would nest an extra element around every fraction.
_INVISIBLE_WRAPPERS = {"mstyle", "mrow"}


class WebSourceError(RuntimeError):
    """Raised when a page cannot be fetched or has no recognisable article body."""


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------


def _request_bytes(url: str) -> bytes:
    """Fetch ``url`` once and return its raw bytes."""
    # Every URL comes from the paper manifest, so the scheme is not attacker-controlled here.
    request = urllib.request.Request(  # noqa: S310
        url, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
        return response.read(MAX_BYTES + 1)


def _fetch_with_retries(url: str, attempts: int = RETRIES) -> bytes:
    """Fetch ``url``, retrying transient transport failures with a short backoff."""
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return _request_bytes(url)
        except _TRANSIENT as error:
            last = error
            if attempt + 1 < attempts:
                time.sleep(RETRY_DELAY * (attempt + 1))
    raise WebSourceError(f"cannot fetch {url}: {last}") from last


def fetch(url: str, cache_dir: Path | None = None) -> str:
    """Fetch ``url`` and return its decoded text, caching the bytes under ``cache_dir``.

    The cache makes re-runs free and lets a fetch be inspected by hand when the site changes.
    Any HTTP or transport failure is raised as :class:`WebSourceError` with the URL in hand.
    """
    if cache_dir is not None:
        cached = cache_dir / f"{_cache_key(url)}.html"
        if cached.exists():
            return cached.read_text(encoding="utf-8")

    raw = _fetch_with_retries(url)
    if len(raw) > MAX_BYTES:
        raise WebSourceError(f"{url} exceeds the {MAX_BYTES} byte download limit")

    text = raw.decode("utf-8", errors="replace")
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{_cache_key(url)}.html").write_text(text, encoding="utf-8")
    return text


def _cache_key(url: str) -> str:
    """Return the cache filename stem for ``url``."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def fetch_bytes(url: str) -> bytes:
    """Fetch ``url`` as raw bytes (used for figures)."""
    return _fetch_with_retries(url)


# --------------------------------------------------------------------------------------
# a small lenient HTML tree
# --------------------------------------------------------------------------------------


class Element:
    """One element of the parsed document, with its attributes and children."""

    __slots__ = ("attrs", "children", "parent", "tag")

    def __init__(self, tag: str, attrs: dict[str, str], parent: Element | None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list[Element | str] = []
        self.parent = parent

    def attr(self, name: str, default: str = "") -> str:
        """Return attribute ``name`` (case-insensitively) or ``default``."""
        if name in self.attrs:
            return self.attrs[name]
        lowered = name.lower()
        for key, value in self.attrs.items():
            if key.lower() == lowered:
                return value
        return default

    def find_all(self, tag: str) -> list[Element]:
        """Return every descendant (and self) with the given tag."""
        found: list[Element] = []
        if self.tag == tag:
            found.append(self)
        for child in self.children:
            if isinstance(child, Element):
                found.extend(child.find_all(tag))
        return found

    def text(self) -> str:
        """Return the concatenated text of this subtree."""
        parts: list[str] = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                parts.append(child.text())
        return "".join(parts)

    def classes(self) -> set[str]:
        """Return the element's CSS class names."""
        return set(self.attr("class").split())


class _Parser(HTMLParser):
    """Build an :class:`Element` tree, tolerating stray end tags and void elements."""

    VOID = frozenset(
        {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
            "path",
            "use",
            "rect",
            "line",
            "circle",
            "ellipse",
            "polygon",
            "polyline",
            "stop",
            "text",
        }
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#document", {}, None)
        self.stack = [self.root]

    def _open(self, tag: str, attrs: list[tuple[str, str | None]], self_closing: bool) -> None:
        # A namespaced SVG tag such as `ns0:path` is flattened to its local name so the
        # DROP_TAGS check can recognise it.
        local = tag.rsplit(":", 1)[-1].lower()
        element = Element(
            local,
            {k.rsplit(":", 1)[-1]: (v or "") for k, v in attrs},
            self.stack[-1],
        )
        self.stack[-1].children.append(element)
        if not self_closing and local not in self.VOID:
            self.stack.append(element)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text() or ""
        self._open(tag, attrs, raw.rstrip().endswith("/>"))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs, True)

    def handle_endtag(self, tag: str) -> None:
        local = tag.rsplit(":", 1)[-1].lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == local:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def parse(html_text: str) -> Element:
    """Parse ``html_text`` into an :class:`Element` tree."""
    parser = _Parser()
    parser.feed(html_text)
    parser.close()
    return parser.root


# --------------------------------------------------------------------------------------
# MathML recovery
# --------------------------------------------------------------------------------------

# Characters the renderer emits, mapped to the source form the author typed.
_CHAR_FIXES = {"\u2061": "", "\u00a0": " ", "\u2212": "-", "\u22c5": "\u00b7"}

# Unicode's mathematical alphanumeric blocks assign each styled letter a predictable offset
# from its plain ASCII counterpart. Reversing that is what lets `mathvariant` replace a
# private-use-style glyph with an ordinary letter a system font can draw.
_ALPHABET_BASES = {
    "bold": (0x1D400, 0x1D41A, 0x1D7CE),
    "italic": (0x1D434, 0x1D44E, None),
    "bold-italic": (0x1D468, 0x1D482, None),
    "script": (0x1D49C, 0x1D4B6, None),
    "bold-script": (0x1D4D0, 0x1D4EA, None),
    "fraktur": (0x1D504, 0x1D51E, None),
    "bold-fraktur": (0x1D56C, 0x1D586, None),
    "double-struck": (0x1D538, 0x1D552, 0x1D7D8),
    "bold-sans-serif": (0x1D5D4, 0x1D5EE, 0x1D7EC),
    "sans-serif": (0x1D5A0, 0x1D5BA, None),
    "sans-serif-italic": (0x1D608, 0x1D622, None),
    "sans-serif-bold-italic": (0x1D63C, 0x1D656, None),
    "monospace": (0x1D670, 0x1D68A, 0x1D7F6),
}

# The Greek letters MathJax draws from the italic block sit in one contiguous run.
_GREEK_ITALIC_BASE = 0x1D6FC
_GREEK_PLAIN_BASE = 0x03B1
_GREEK_ITALIC_NAMES = (
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "eta",
    "theta",
    "iota",
    "kappa",
    "lambda",
    "mu",
    "nu",
    "xi",
    "omicron",
    "pi",
    "rho",
    "final sigma",
    "sigma",
    "tau",
    "upsilon",
    "phi",
    "chi",
    "psi",
    "omega",
)

# The renderer encodes a few characters in a mathematical-class variant that carries no extra
# meaning here; they are folded to the ordinary symbol.
_CLASS_KEEP = {"N", "B", "I", "V"}


def _variant_char(codepoint: int) -> tuple[str, str]:
    """Return ``(character, mathvariant)`` for a styled mathematical codepoint.

    ``mathvariant`` is ``""`` when the character needs no styling.
    """
    try:
        name = unicodedata.name(chr(codepoint))
    except ValueError:
        return chr(codepoint), ""

    if "MATHEMATICAL" not in name:
        return chr(codepoint), ""

    for variant, (upper, lower, digit) in _ALPHABET_BASES.items():
        for base, letter_base in ((upper, 0x41), (lower, 0x61)):
            span = 26
            if base <= codepoint < base + span:
                return chr(letter_base + codepoint - base), variant
        if digit is not None and digit <= codepoint < digit + 10:
            return chr(0x30 + codepoint - digit), variant

    if _GREEK_ITALIC_BASE <= codepoint < _GREEK_ITALIC_BASE + len(_GREEK_ITALIC_NAMES):
        index = codepoint - _GREEK_ITALIC_BASE
        return chr(_GREEK_PLAIN_BASE + index), "italic" if index != 17 else ""

    # Fall back to the decomposition/compatibility form when Unicode offers one.
    folded = unicodedata.normalize("NFKC", chr(codepoint))
    if folded and folded != chr(codepoint):
        return folded, ""
    return chr(codepoint), ""


def _glyph_text(codepoint: int) -> str:
    """Return the source character for one glyph codepoint."""
    char, variant = _variant_char(codepoint)
    if variant:
        # A styled letter is recorded through mathvariant on its parent; the character itself
        # is emitted plain.
        return char
    return _CHAR_FIXES.get(char, char)


def _glyph_variant(codepoint: int) -> str:
    """Return the ``mathvariant`` that a glyph codepoint implies, or ``""``."""
    _char, variant = _variant_char(codepoint)
    return variant


def _strike_notation(element: Element) -> str:
    """Return the ``notation`` a ``menclose`` must carry, read off the line that was drawn.

    MathJax draws a cancellation as a stroked ``<line>`` rather than writing the MathML
    attribute, and its SVG coordinate system has y pointing up (the document is wrapped in a
    ``scale(1, -1)`` to reach screen space). A line whose y increases therefore rises from left
    to right, which is ``updiagonalstrike``. Anything that was not drawn as a line -- a box, a
    circle -- yields ``""`` so the element is left unadorned rather than given a wrong strike.
    """
    for line in element.find_all("line"):
        try:
            x1 = float(line.attr("x1") or 0.0)
            y1 = float(line.attr("y1") or 0.0)
            x2 = float(line.attr("x2") or 0.0)
            y2 = float(line.attr("y2") or 0.0)
        except ValueError:
            continue
        if x2 == x1:
            continue
        return "updiagonalstrike" if y2 > y1 else "downdiagonalstrike"
    return ""


class MmlNode:
    """One node of a reconstructed MathML tree."""

    __slots__ = ("children", "mathvariant", "name", "notation", "text")

    def __init__(self, name: str) -> None:
        self.name = name
        self.children: list[MmlNode] = []
        self.text: str = ""
        self.mathvariant: str = ""
        self.notation: str = ""

    def to_xml(self) -> str:
        """Serialize this node and its subtree as MathML."""
        if self.name == "mspace":
            return "<mspace/>"
        if self.name == "text":
            return html.escape(self.text)
        attrs = f' mathvariant="{self.mathvariant}"' if self.mathvariant else ""
        if self.notation:
            attrs += f' notation="{self.notation}"'
        if not self.children:
            body = html.escape(self.text)
            if not body:
                return f"<{self.name}{attrs}/>"
            return f"<{self.name}{attrs}>{body}</{self.name}>"
        inner = "".join(child.to_xml() for child in self.children)
        return f"<{self.name}{attrs}>{inner}</{self.name}>"


def _collapse(node: MmlNode) -> MmlNode:
    """Fold redundant single-child wrappers out of a reconstructed tree.

    The renderer wraps a `\\mathbf{Q}` in a grouping atom holding one `mi`; the same holds for a
    fraction's operands. Recursing through such a wrapper with one child and no own text keeps
    the output close to the MathML a person would write, and propagation of `mathvariant`
    downwards means the style is not lost on the way.
    """
    node.children = [_collapse(child) for child in node.children]
    if node.name == "msqrt":
        # MathJax draws the radical sign as an ordinary glyph and puts it inside the ``msqrt``
        # beside the radicand. MathML has a dedicated element that draws the sign over whatever
        # the element contains, so keeping the glyph would render a second one next to the root.
        if not node.text.strip(_RADICAL_SIGNS):
            node.text = ""
        node.children = [
            child
            for child in node.children
            if not (
                child.name == "mo" and not child.children and not child.text.strip(_RADICAL_SIGNS)
            )
        ]
    if (
        node.name in _TOKEN_ELEMENTS
        and not node.text
        and node.children
        and all(child.name in _TOKEN_ELEMENTS and not child.children for child in node.children)
    ):
        # The renderer draws some multi-glyph operators as several text runs inside one token:
        # ``:=`` arrives as two ``text`` children. Their text is that token's text, and a token
        # holding elements instead of text would lay those runs out one per line.
        node.text = "".join(child.text for child in node.children)
        node.children = []
    if node.name in _INVISIBLE_WRAPPERS and not node.text and len(node.children) == 1:
        inner = node.children[0]
        if not node.mathvariant:
            return inner
        if not inner.mathvariant:
            inner.mathvariant = node.mathvariant
        return inner
    if node.mathvariant:
        _apply_variant(node, node.mathvariant)
    return node


def _apply_variant(node: MmlNode, variant: str) -> None:
    """Push a parent's variant onto any child that does not set its own."""
    for child in node.children:
        if child.name in {"mi", "mn"} and not child.mathvariant:
            child.mathvariant = variant
        _apply_variant(child, variant)


def _element_to_mml(element: Element) -> MmlNode | None:
    """Convert one MathJax SVG ``<g data-mml-node>`` element into an :class:`MmlNode`.

    ``TeXAtom`` is a TeX grouping atom, the renderer's equivalent of a plain ``mrow``, so it is
    emitted as one; emitting it as ``mi`` would put element children inside a token element and
    stack them vertically.
    """
    raw_name = element.attr("data-mml-node")
    if not raw_name:
        return None
    name = "mrow" if raw_name == "TeXAtom" else raw_name
    if raw_name == "text":
        name = "mtext"

    node = MmlNode(name)
    if name == "menclose":
        node.notation = _strike_notation(element)
    for child in element.children:
        if isinstance(child, str):
            continue
        if child.tag == "use":
            codepoint = child.attr("data-c")
            if not codepoint:
                continue
            value = int(codepoint, 16)
            variant = _glyph_variant(value)
            char = _glyph_text(value)
            if variant and not node.mathvariant and node.name in {"mi", "mn"}:
                node.mathvariant = variant
            node.text += char
            continue
        if child.tag == "g" and not child.attr("data-mml-node"):
            # MathJax puts a construct's content in a layout group that carries no
            # ``data-mml-node`` of its own: a radical's radicand and the struck term of a
            # menclose are both in there. Skipping the bare group would drop that content and
            # leave an empty ``<msqrt/>`` behind, so descend through it instead.
            for grandchild in child.children:
                if isinstance(grandchild, str):
                    continue
                converted = _element_to_mml(grandchild)
                if converted is not None:
                    node.children.append(converted)
            continue
        converted = _element_to_mml(child)
        if converted is not None:
            node.children.append(converted)

    if raw_name in {"TeXAtom", "mstyle"} and not node.text and len(node.children) == 1:
        # A bracing wrapper around a single operand: drop it once the variant is pushed down.
        inner = node.children[0]
        if node.mathvariant and not inner.mathvariant:
            inner.mathvariant = node.mathvariant
        return inner
    return node


def container_to_mathml(container: Element) -> str:
    """Reconstruct the MathML of one ``<mjx-container>`` from its rendered SVG.

    Returns an empty string when the container holds no recoverable math, which the caller
    treats as "nothing to emit" rather than as an error.
    """
    groups = container.find_all("g")
    root = next((g for g in groups if g.attr("data-mml-node") == "math"), None)
    if root is None:
        return ""
    node = _element_to_mml(root)
    if node is None:
        return ""
    node = _collapse(node)
    node.name = "math"
    return node.to_xml()


def sanitize_svg(data: bytes) -> bytes:
    """Strip embedded fonts and editor metadata from a fetched SVG figure.

    The hand-drawn diagrams carry a base64 WOFF2 web font and the original editor document in
    their metadata. This repository never embeds, downloads or vendors a font: the stylesheet
    only names font families and the reader's own fonts supply the glyphs. Removing the payload
    also cuts each diagram's size substantially, so a shipped SVG stays a plain XML drawing.
    """
    text = data.decode("utf-8", errors="replace")
    original = len(text)
    # Excalidraw writes every tag with an ``ns0:`` prefix, so the element name must tolerate one.
    prefix = r"(?:[A-Za-z_][\w.-]*:)?"
    # An SVG's embedded @font-face can only live inside a <style> block.
    text = re.sub(
        rf"<{prefix}style\b[^>]*>.*?</{prefix}style>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # The editor document blob is dead weight for a reader.
    text = re.sub(
        rf"<{prefix}metadata\b[^>]*>.*?</{prefix}metadata>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if len(text) == original:
        return data
    return text.encode("utf-8")


# --------------------------------------------------------------------------------------
# article extraction
# --------------------------------------------------------------------------------------


@dataclass
class FigureRecord:
    """One figure downloaded from the source site."""

    number: int
    section: str
    order: int
    source_url: str
    path: str
    bytes: int
    changed: bool
    caption: str = ""


@dataclass
class Report:
    """Extraction inventory for a web source, shaped like the PDF extractor's report."""

    slug: str
    base: str
    sections: list[dict[str, object]] = field(default_factory=list)
    figures: list[FigureRecord] = field(default_factory=list)
    equations: list[dict[str, object]] = field(default_factory=list)


@dataclass
class ExtractContext:
    """Bookkeeping shared while walking one page."""

    slug: str
    section: str
    base: str
    figures_dir: Path
    figure_start: int
    number_offset: int | None = None
    image_counter: int = 0
    table_counter: int = 0
    figures_counter: _Counter | None = None
    tables_counter: _Counter | None = None

    def number(self, kind: str, key: str | None = None) -> int:
        """Return the next number in the figure or table sequence."""
        counters = {"figure": self.figures_counter, "table": self.tables_counter}
        counter = counters[kind]
        if counter is None:
            raise WebSourceError(f"extract context has no {kind} counter")
        return counter.take(key)


class _Counter:
    """A monotonic number sequence for one kind of numbered object.

    The source site does not number its figures or tables at all, so the pipeline assigns the
    numbers itself, keeping the figures' and the tables' sequences separate the way the rest
    of the repository does. A number already issued for a given key is reused, so an asset
    shown on several pages keeps a single identity.
    """

    def __init__(self, start: int = 0) -> None:
        self.value = start
        self.taken: dict[str, int] = {}

    def take(self, key: str | None = None) -> int:
        """Return the next number, reusing the one already issued for ``key``."""
        if key is not None and key in self.taken:
            return self.taken[key]
        self.value += 1
        if key is not None:
            self.taken[key] = self.value
        return self.value


class _Walker:
    """Render an article subtree as translation-ready source text."""

    def __init__(self, context: ExtractContext, figures: list[FigureRecord]) -> None:
        self.context = context
        self.figures = figures
        self.lines: list[str] = []
        self.buffer: list[str] = []
        self.in_pre = False
        self.pre_language = ""
        self.pre_caption = ""
        self.skip_depth = 0
        self.list_depth = 0

    # -- text accumulation -------------------------------------------------------------

    def _flush(self) -> None:
        text = "".join(self.buffer)
        self.buffer = []
        text = re.sub(r"[ \t\u00a0]+", " ", text).strip()
        if text:
            self.lines.append(text)

    def _emit(self, line: str = "") -> None:
        self._flush()
        if line:
            self.lines.append(line)

    def _blank(self) -> None:
        self._flush()
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    # -- subtree rendering -------------------------------------------------------------

    def run(self, element: Element) -> str:
        """Render ``element`` and return the produced text."""
        self.visit(element)
        self._flush()
        text = "\n".join(self.lines).strip() + "\n"
        return re.sub(r"\n{3,}", "\n\n", text)

    def visit(self, element: Element) -> None:
        tag = element.tag
        if self.skip_depth:
            return
        if tag in DROP_TAGS:
            return
        classes = element.classes()
        if "lightbox-wrapper" in classes:
            self._visit_children(element)
            return
        # The site marks its own injected chrome (heading anchor links, the table-of-contents
        # popover button) so it can be excluded; the pipeline generates its own anchors.
        if element.attr("role") == "anchor" or "anchor" in classes or "popover" in classes:
            return
        if tag == "mjx-container":
            self._math(element)
            return
        if tag == "figure" and element.find_all("pre"):
            self._code_block(element)
            return
        if tag == "pre" and not self.in_pre:
            self._code_block(element)
            return
        if tag == "figcaption":
            # A caption that is not part of a figure or code block was already attached to the
            # preceding image or table, so emitting it again would duplicate the caption text.
            walker = element.parent
            while walker is not None and walker.tag not in {
                "figure",
                "blockquote",
                "article",
                "body",
            }:
                walker = walker.parent
            if walker is None or walker.tag != "figure":
                return
        if tag == "table":
            self._table(element)
            return
        if tag == "img":
            self._image(element)
            return
        if tag == "a":
            self._link(element)
            return
        if tag == "blockquote" and "transclude" in classes:
            self._transclude(element)
            return
        if tag in HEADING_TAGS:
            level = int(tag[1])
            self._blank()
            self._flush()
            self.lines.append(f"{'#' * min(level, 6)} {self._inline(element).strip()}")
            self.lines.append("")
            return
        if tag == "li":
            self._flush()
            marker = "-"
            parent = element.parent
            if parent is not None and parent.tag == "ol":
                index = 1
                for sibling in parent.children:
                    if isinstance(sibling, Element) and sibling is element:
                        break
                    if isinstance(sibling, Element) and sibling.tag == "li":
                        index += 1
                marker = f"{index}."
            indent = "  " * self.list_depth
            text = self._item_inline(element).strip()
            self.lines.append(f"{indent}{marker} {text}".rstrip())
            for child in element.children:
                if isinstance(child, Element) and child.tag in {"ul", "ol"}:
                    self.list_depth += 1
                    self.visit(child)
                    self.list_depth -= 1
            return
        if tag == "td" or tag == "th":
            # Table cells are consumed by _table; reaching here means a stray cell.
            self.buffer.append(self._inline(element))
            return
        if tag in {"ul", "ol"} and not self.list_depth:
            self._blank()
        if tag in {"div", "section"} and self.lines and self.lines[-1] != "":
            self._blank()
        if tag in BLOCK_TAGS:
            self._visit_block(element)
            return
        self._visit_children(element)

    def _visit_children(self, element: Element) -> None:
        for child in element.children:
            if isinstance(child, str):
                self.buffer.append(child)
            else:
                self.visit(child)

    def _visit_block(self, element: Element) -> None:
        """Handle a block element, keeping inline runs on one line."""
        if element.tag in {"p", "div", "blockquote", "figure", "figcaption", "dd", "dt"}:
            self._blank()
        self._visit_children(element)
        if element.tag in {"p", "div", "blockquote", "figure", "figcaption", "dd", "dt"}:
            self._flush()

    # -- element handlers --------------------------------------------------------------

    def _math(self, element: Element) -> None:
        mathml = container_to_mathml(element)
        if mathml:
            self.buffer.append(mathml)

    def _inline(self, element: Element) -> str:
        """Render a subtree as a single line of text (headings, list items, cells)."""
        saved_lines, saved_buffer = self.lines, self.buffer
        self.lines, self.buffer = [], []
        self._visit_children(element)
        self._flush()
        produced = " ".join(line for line in self.lines if line).strip()
        self.lines, self.buffer = saved_lines, saved_buffer
        return produced

    def _item_inline(self, element: Element) -> str:
        """Render a list item's own text, leaving any nested list for separate emission.

        A nested list inside an item is emitted by :meth:`visit` with an indent, so it must not
        be folded into the item's own line the way :meth:`_inline` would fold it.
        """
        saved_lines, saved_buffer = self.lines, self.buffer
        self.lines, self.buffer = [], []
        for child in element.children:
            if isinstance(child, str):
                self.buffer.append(child)
            elif child.tag not in {"ul", "ol"}:
                self.visit(child)
        self._flush()
        produced = " ".join(line for line in self.lines if line).strip()
        self.lines, self.buffer = saved_lines, saved_buffer
        return produced

    def _link(self, element: Element) -> None:
        href = element.attr("href")
        text = self._inline(element)
        if not text:
            return
        if href.startswith("#") or not href:
            self.buffer.append(text)
            return
        absolute = href
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", href):
            from urllib.parse import urljoin

            absolute = urljoin(f"{self.context.base}/", href)
        self.buffer.append(f"[{text}]({absolute})")

    def _transclude(self, element: Element) -> None:
        """Render a transcluded block, keeping the embedded content and its provenance.

        The site inlines a fragment of another page here. The fragment is rendered as ordinary
        blocks so a list stays a list, and a comment records where it came from so a translator
        can tell an intentional repeat from an accidental one.
        """
        self._blank()
        self._visit_children(element)
        self._flush()
        target = element.attr("data-url")
        if target:
            alias = element.attr("data-embed-alias")
            self._blank()
            self.lines.append(f"<!-- transcluded from {target}: {alias} -->")
        self.lines.append("")

    def _code_block(self, element: Element) -> None:
        caption = ""
        for candidate in element.find_all("figcaption"):
            caption = self._inline(candidate).strip()
            break
        language = element.attr("data-language")
        pre = next((p for p in element.find_all("pre")), element)
        if not language:
            language = pre.attr("data-language")
        code = pre.text()
        # The renderer splits every line into a <span data-line>; the text content already
        # carries the newlines, so only indentation of the first line needs restoring.
        code = code.replace("\r\n", "\n").strip("\n")
        self._blank()
        if caption:
            self.lines.append(f"<!-- {caption} -->")
        self.lines.append(f"```{language}")
        self.lines.extend(code.split("\n"))
        self.lines.append("```")
        self.lines.append("")

    def _table(self, element: Element) -> None:
        number = self.context.number("table")
        caption = ""
        for candidate in element.find_all("caption"):
            caption = self._caption_text(candidate)
            break
        if not caption:
            caption = self._figure_caption(element)
        header_row: list[str] = []
        body_rows: list[list[str]] = []
        for row in element.find_all("tr"):
            cells = [c for c in row.children if isinstance(c, Element) and c.tag in {"td", "th"}]
            values = [self._inline(cell) for cell in cells]
            is_header = any(cell.tag == "th" for cell in cells)
            if is_header and not header_row:
                header_row = values
            else:
                body_rows.append(values)
        if not header_row and not body_rows:
            return
        width = max(len(header_row), *(len(row) for row in body_rows))
        header_row = header_row + [""] * (width - len(header_row))
        self._blank()
        self.lines.append(f"表 {number} | {caption}".rstrip())
        self.lines.append("")
        self.lines.append("| " + " | ".join(header_row) + " |")
        self.lines.append("|" + "---|" * width)
        for row in body_rows:
            padded = row + [""] * (width - len(row))
            self.lines.append("| " + " | ".join(padded) + " |")
        self.lines.append("")

    def _image(self, element: Element) -> None:
        source = element.attr("src") or element.attr("data-src")
        if not source:
            return
        from urllib.parse import urljoin

        absolute = urljoin(f"{self.context.base}/", source)
        # The same asset is often shown on several pages, so its number is issued once and
        # reused; the caption still comes from this occurrence.
        number = self.context.number("figure", absolute)
        caption = self._figure_caption(element)
        if not any(f.source_url == absolute for f in self.figures):
            suffix = Path(absolute.split("?")[0]).suffix.lower() or ".bin"
            target = self.context.figures_dir / f"figure-{number:02d}{suffix}"
            self.figures.append(self._download(absolute, target, number, suffix, caption))
        suffix = Path(absolute.split("?")[0]).suffix.lower() or ".bin"
        self._blank()
        alt = element.attr("alt") or element.attr("data-alt") or ""
        self.lines.append("<figure>")
        self.lines.append(f'<img src="assets/figures/figure-{number:02d}{suffix}" alt="{alt}">')
        if caption:
            self.lines.append(f"<figcaption>图 {number} | {caption}</figcaption>")
        else:
            self.lines.append(f"<figcaption>图 {number}</figcaption>")
        self.lines.append("</figure>")
        self.lines.append("")

    def _download(
        self, url: str, target: Path, number: int, suffix: str, caption: str = ""
    ) -> FigureRecord:
        data = fetch_bytes(url)
        if suffix == ".svg":
            data = sanitize_svg(data)
        changed = True
        if target.exists() and target.read_bytes() == data:
            changed = False
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return FigureRecord(
            number=number,
            section=self.context.section,
            order=len(self.figures) + 1,
            source_url=url,
            path=str(target.relative_to(ROOT)).replace("\\", "/"),
            bytes=len(data),
            changed=changed,
            caption=caption,
        )

    def _enclosing_scope(self, element: Element) -> Element | None:
        """Return the nearest figure/transclusion boundary above ``element``.

        A transcluded fragment repeats captions that belong to its own block, so assignment by
        proximity must never cross a blockquote or figure boundary.
        """
        walker = element.parent
        while walker is not None and walker.tag not in {"blockquote", "figure", "article", "body"}:
            walker = walker.parent
        return walker

    def _figure_caption(self, element: Element) -> str:
        """Return the caption for an image or table, whether nested or a loose sibling."""
        figure = element.parent
        while figure is not None and figure.tag not in {"figure", "body"}:
            figure = figure.parent
        if figure is not None and figure.tag == "figure":
            for caption in figure.find_all("figcaption"):
                text = self._caption_text(caption)
                if text:
                    return text

        # A loose caption follows the whole content block, so each ancestor up to the
        # transclusion boundary is tried, not just the element itself.
        scope = self._enclosing_scope(element)
        walker = element
        while walker is not None:
            parent = walker.parent
            if parent is None:
                break
            siblings = parent.children
            index = next((i for i, c in enumerate(siblings) if c is walker), None)
            if index is not None:
                for child in siblings[index + 1 :]:
                    if not isinstance(child, Element):
                        continue
                    if child.tag == "figcaption":
                        text = self._caption_text(child)
                        if text:
                            return text
                        break
                    if child.tag in {"p", "div"} and child.find_all("figcaption"):
                        continue
                    if child.tag in {"img", "table", "p", "div", "figure", "h2", "h3", "h4"}:
                        break
            if parent is scope:
                break
            walker = parent
        return element.attr("alt") or element.attr("data-alt") or ""

    def _caption_text(self, element: Element) -> str:
        """Render a caption to plain text without registering figures or tables.

        Caption lookup happens while the surrounding content is still being walked, so it must
        not download an image or consume a number as a side effect.
        """
        parts: list[str] = []

        def collect(node: Element) -> None:
            for child in node.children:
                if isinstance(child, str):
                    parts.append(child)
                elif child.tag == "mjx-container":
                    parts.append(container_to_mathml(child))
                elif child.tag != "img":
                    collect(child)

        collect(element)
        return re.sub(r"[ \t\u00a0]+", " ", "".join(parts)).strip()


def find_article(root: Element) -> Element:
    """Return the article body element, or raise when the page has none."""
    for candidate in root.find_all("article"):
        if "popover-hint" in candidate.classes() or candidate.find_all("h2"):
            return candidate
    articles = root.find_all("article")
    if articles:
        return articles[0]
    raise WebSourceError("no <article> element found in the page")


def extract_page(
    page_html: str,
    context: ExtractContext,
    figures: list[FigureRecord],
    figures_counter: _Counter | None = None,
    tables_counter: _Counter | None = None,
) -> tuple[str, int, int]:
    """Extract one page and return ``(text, figure_count, equation_count)``."""
    root = parse(page_html)
    article = find_article(root)
    context.figures_counter = figures_counter if figures_counter is not None else _Counter()
    context.tables_counter = tables_counter if tables_counter is not None else _Counter()
    text = _Walker(context, figures).run(article)
    equations = len(re.findall(r"<math\b", text))
    return text, len(figures), equations


# --------------------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------------------


def extract(
    current: paper.Paper,
    cache_dir: Path | None = None,
    figures_dir: Path | None = None,
) -> Report:
    """Extract every section of a web-sourced paper and write its report."""
    if current.source_web is None:
        raise WebSourceError(f"paper {current.slug!r} does not name a web source")
    web = current.source_web
    sections_dir = current.sections_dir
    sections_dir.mkdir(parents=True, exist_ok=True)
    target_figures = figures_dir or current.figures_dir

    figures: list[FigureRecord] = []
    figures_counter = _Counter()
    tables_counter = _Counter()
    report = Report(slug=current.slug, base=web.base)
    for section in current.sections:
        if section.url is None:
            raise WebSourceError(f"section {section.name!r} has no url")
        url = web.absolute(section.url)
        page_html = fetch(url, cache_dir)
        context = ExtractContext(
            slug=current.slug,
            section=section.name,
            base=web.base,
            figures_dir=target_figures,
            figure_start=len(figures),
        )
        text, _, _ = extract_page(page_html, context, figures, figures_counter, tables_counter)
        target = sections_dir / f"{section.name}.txt"
        target.write_text(text, encoding="utf-8")
        report.sections.append(
            {
                "name": section.name,
                "url": section.url,
                "chars": len(text),
                "figures": sum(1 for f in figures if f.section == section.name),
                "equations": len(re.findall(r"<math\b", text)),
                "tables": len(re.findall(r"^\u8868 \d+ \|", text, re.MULTILINE)),
            }
        )
    report.figures = figures
    current.report_path.parent.mkdir(parents=True, exist_ok=True)
    current.report_path.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", default=None, help="registered paper slug")
    parser.add_argument("--figures-only", action="store_true", help="rebuild figures only")
    parser.add_argument(
        "--no-cache", action="store_true", help="ignore the on-disk page cache and refetch"
    )
    args = parser.parse_args(argv)

    current = paper.resolve(args.paper)
    if not current.is_web:
        parser.error(f"paper {current.slug!r} has a PDF source; use tools/extract.py")
    cache = None if args.no_cache else current.source_dir / "pages"
    report = extract(current, cache_dir=cache)

    print(f"paper            : {current.slug} ({current.title})")
    print(f"base             : {report.base}")
    print(f"sections         : {len(report.sections)}")
    for section in report.sections:
        print(
            f"  {section['name']:<20} {section['chars']:>7} chars  "
            f"{section['figures']:>2} figures  {section['equations']:>3} math  "
            f"{section['tables']:>2} tables"
        )
    figures = report.figures
    written = sum(1 for f in figures if f.changed)
    print(
        f"figures          : {len(figures)} ({written} written, {len(figures) - written} unchanged)"
    )
    print(f"report           : {current.report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
