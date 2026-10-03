"""Reader presentation: compact source notes and citations, without rewriting originals.

Optional work/reader.json holds a verified citation map and public source URL;
work/reader-meta.md holds header-only notes. Both remain local maintenance inputs.
Reference/declaration sections are extracted from rendered Markdown, not deleted from source.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

VOID = {
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
}
META_HEADINGS = {
    "论文信息",
    "作者信息",
    "翻译说明",
    "阅读说明",
    "版权声明",
    "致谢",
    "致谢与声明",
    "出版说明",
    "Acknowledgements",
    "Acknowledgment",
    "Declarations",
}
REFERENCE_HEADINGS = {"参考文献", "References", "Bibliography"}
NUMBER_CITATION = r"\[(?:[1-9]\d*)(?:\s*(?:[,，;；]|[-–—])\s*[1-9]\d*)*\]"
PAREN_CITATION = re.compile(r"[（(]([^()（）]*\b(?:19|20)\d{2}[a-z]?[^()（）]*)[）)]")
AUTHOR_YEAR = re.compile(r"^[A-Za-z][A-Za-z0-9 .,'’&–-]*[,\s]+(?:19|20)\d{2}[a-z]?$", re.IGNORECASE)


def normalize(text: str) -> str:
    """Normalize layout whitespace, never factual names, spelling or numbering."""
    return re.sub(r"\s+", " ", text).strip()


def safe_url(value: str | None) -> str | None:
    """Allow only actual HTTP(S) source links, not local paths or executable schemes."""
    if not value:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        raise ValueError(f"invalid citation/source URL: {value!r}")
    return value


@dataclass
class Block:
    """One top-level HTML block, preserved byte-for-byte as a string."""

    tag: str
    raw: str
    text: str
    attrs: dict

    @property
    def level(self) -> int:
        """Heading level, or zero for non-headings."""
        return int(self.tag[1]) if re.fullmatch(r"h[1-6]", self.tag) else 0


class Blocks(HTMLParser):
    """Locate top-level blocks without serializing or damaging MathML/figures."""

    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.starts = [0]
        for line in source.splitlines(keepends=True):
            self.starts.append(self.starts[-1] + len(line))
        self.blocks: list[Block] = []
        self.stack: list[str] = []
        self.last = 0
        self.start = 0
        self.tag = ""
        self.attrs: dict = {}
        self.text: list[str] = []
        self.feed(source)
        self.close()
        if self.stack:
            raise ValueError(f"unbalanced reader HTML: {self.stack}")
        self._gap(len(source))

    def position(self) -> int:
        """Return the character offset for the parser's current token."""
        line, column = self.getpos()
        return self.starts[line - 1] + column

    def _gap(self, end: int) -> None:
        if end > self.last:
            raw = self.source[self.last : end]
            self.blocks.append(Block("", raw, normalize(raw), {}))
        self.last = end

    def _finish(self, end: int) -> None:
        self.blocks.append(
            Block(
                self.tag, self.source[self.start : end], normalize(" ".join(self.text)), self.attrs
            )
        )
        self.last = end

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Start a block or descend into its markup."""
        if not self.stack:
            self._gap(self.position())
            self.start, self.tag, self.attrs, self.text = self.position(), tag, dict(attrs), []
        if tag in VOID:
            if not self.stack:
                self._finish(self.position() + len(self.get_starttag_text()))
        else:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        """Keep self-closing XML/HTML elements intact."""
        if not self.stack:
            self._gap(self.position())
            self.start, self.tag, self.attrs, self.text = self.position(), tag, dict(attrs), []
            self._finish(self.position() + len(self.get_starttag_text()))

    def handle_endtag(self, tag: str) -> None:
        """Complete the outer block after nested tags have closed."""
        if tag in self.stack:
            while self.stack.pop() != tag:
                pass
            if not self.stack:
                self._finish(self.source.index(">", self.position()) + 1)

    def handle_data(self, data: str) -> None:
        """Collect readable text for identifying auxiliary headings."""
        if self.stack:
            self.text.append(data)


class ReferenceItems(HTMLParser):
    """Collect original bibliography list items with their explicit numbering/links."""

    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.items: dict[str, dict] = {}
        self.number = 0
        self.depth = 0
        self.text: list[str] = []
        self.url = None
        self.feed(source)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Read list numbering and a reference's first real hyperlink."""
        values = dict(attrs)
        if tag == "ol" and not self.depth:
            self.number = int(values.get("start") or 1) - 1
        if tag == "li":
            if not self.depth:
                self.number = int(values.get("value") or self.number + 1)
                self.text, self.url = [], None
            self.depth += 1
        if self.depth and tag == "a" and not self.url:
            self.url = safe_url(values.get("href"))

    def handle_endtag(self, tag: str) -> None:
        """Save a reference when its outer list item ends."""
        if tag == "li" and self.depth:
            self.depth -= 1
            if not self.depth:
                text = normalize(" ".join(self.text))
                self.items[str(self.number)] = {"text": text, "url": self.url or url_in_text(text)}

    def handle_data(self, data: str) -> None:
        """Collect reference text including inline markup."""
        if self.depth:
            self.text.append(data)


def url_in_text(text: str) -> str | None:
    """Recover explicitly written URLs/DOIs/arXiv IDs, never guess a paper's identity."""
    match = re.search(r"https?://[^\s<>]+", text)
    if match:
        return safe_url(match.group().rstrip(".,;。)"))
    match = re.search(r"\b10\.\d{4,9}/[^\s<>]+", text)
    if match:
        return safe_url("https://doi.org/" + match.group().rstrip(".,;。)"))
    match = re.search(r"arXiv[:\s]+(\d{4}\.\d{4,5}(?:v\d+)?)", text, re.IGNORECASE)
    return "https://arxiv.org/abs/" + match.group(1) if match else None


def split_auxiliary(source: str) -> tuple[str, str, dict[str, dict]]:
    """Move only named metadata/declaration blocks; remove bibliography from the body."""
    body, metadata, references = [], [], {}
    mode, level = "body", 0
    for block in Blocks(source).blocks:
        if block.level and block.level <= level:
            mode, level = "body", 0
        label = re.sub(r"\s*[（(](?:原文|original)[）)]\s*$", "", block.text, flags=re.IGNORECASE)
        if block.level and label in META_HEADINGS | REFERENCE_HEADINGS:
            mode = "references" if label in REFERENCE_HEADINGS else "metadata"
            level = block.level
            continue
        if mode == "body":
            body.append(block.raw)
        elif mode == "metadata":
            # Publisher neutrality boilerplate is not the learner's own statement.
            # Copyright/licensing restrictions, contributions and attribution remain intact.
            if not block.text.startswith(("Publisher’s Note", "Publisher's Note")):
                metadata.append(block.raw)
        elif block.tag in {"ol", "ul"}:
            references.update(ReferenceItems(block.raw).items)
    return "".join(body), "".join(metadata), references


def load_profile(work: Path) -> dict:
    """Read optional canonical presentation metadata without any project constants."""
    path = work / "reader.json"
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(result, dict) or not isinstance(result.get("references", {}), dict):
        raise ValueError("reader.json must contain an object and an optional references object")
    safe_url(result.get("source_url"))
    if result.get("citation_style", "mixed") not in {"mixed", "numeric", "author-year"}:
        raise ValueError("citation_style must be mixed, numeric or author-year")
    for record in result.get("references", {}).values():
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("text"), str)
            or not record["text"].strip()
        ):
            raise ValueError("every reference must have non-empty original text")
        safe_url(record.get("url"))
        if not isinstance(record.get("aliases", []), list) or any(
            not isinstance(a, str) or not a.strip() for a in record.get("aliases", [])
        ):
            raise ValueError("reference aliases must be non-empty strings")
    return result


def citation_numbers(label: str) -> list[str]:
    """Expand original ranges without changing their displayed notation."""
    result = []
    for part in re.split(r"[,，;；]", label[1:-1]):
        ends = re.split(r"[-–—]", part.strip())
        first, last = int(ends[0]), int(ends[-1])
        if last < first or last - first > 100:
            return []
        result.extend(str(n) for n in range(first, last + 1))
    return list(dict.fromkeys(result))


class CitationLinker(HTMLParser):
    """Link cited text only, leaving code, existing links and MathML byte-for-byte intact."""

    def __init__(
        self,
        source: str,
        references: dict[str, dict],
        source_url: str | None,
        citation_style: str = "mixed",
    ):
        super().__init__(convert_charrefs=False)
        self.references, self.source_url = references, source_url
        self.citation_style = citation_style
        self.pending: list[str] = []
        self.output: list[str] = []
        self.skip: list[str] = []
        self.linked = 0
        self.unresolved: set[str] = set()
        self.aliases = {}
        for key, record in references.items():
            for alias in record.get("aliases", []):
                normalized = normalize(alias)
                if normalized in self.aliases and self.aliases[normalized] != key:
                    raise ValueError(f"ambiguous citation alias: {normalized}")
                self.aliases[normalized] = key
        aliases = [
            r"\s+".join(re.escape(s).replace(r"\&", r"(?:&amp;|&)") for s in alias.split())
            for alias in sorted(self.aliases, key=len, reverse=True)
        ]
        patterns = ([NUMBER_CITATION] if citation_style != "author-year" else []) + aliases
        self.pattern = re.compile("|".join(patterns) if patterns else r"(?!)")
        self.feed(source)
        self.close()
        self._flush_data()

    def _link(self, label: str, keys: list[str]) -> str:
        if not keys or (not self.source_url and any(key not in self.references for key in keys)):
            return label
        records = []
        for key in keys:
            record = self.references.get(key)
            if record is None:
                self.unresolved.add(key)
                record = {"text": f"引用 {key}；本地未建立该条引用的可靠映射，请查阅论文原文。"}
            url = record.get("url") or self.source_url
            records.append(
                {
                    "label": record.get("label", key),
                    "text": record["text"],
                    "url": url,
                    "fallback": not bool(record.get("url")),
                }
            )
        notes = "\n\n".join(record["text"] for record in records)
        href = (self.source_url if len(records) > 1 else records[0]["url"]) or records[0]["url"]
        if not href:
            return label
        self.linked += 1
        data = escape(json.dumps(records, ensure_ascii=False), quote=True)
        return (
            f'<a class="citation" href="{escape(href, quote=True)}" title="{escape(notes, quote=True)}" '
            f'aria-label="{escape("引用 " + label + "，点击查看来源详情", quote=True)}" data-citations="{data}">{escape(label)}</a>'
        )

    def _replace(self, match: re.Match) -> str:
        label = unescape(match.group())
        if label.startswith("["):
            return self._link(label, citation_numbers(label))
        return self._link(label, [self.aliases[normalize(label)]])

    def _parenthetical(self, match: re.Match) -> str:
        original = match.group()
        parts = re.split(r"([;；])", unescape(match.group(1)))
        for index, part in enumerate(parts):
            stripped = normalize(part)
            if self.citation_style != "numeric" and AUTHOR_YEAR.fullmatch(stripped):
                leading = part[: len(part) - len(part.lstrip())]
                trailing = part[len(part.rstrip()) :]
                key = self.aliases.get(stripped, stripped)
                parts[index] = leading + self._link(stripped, [key]) + trailing
            else:
                parts[index] = self.pattern.sub(self._replace, escape(part, quote=False))
        return original[0] + "".join(parts) + original[-1]

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Preserve markup and suppress citation rewriting in non-prose nodes."""
        self._flush_data()
        self.output.append(self.get_starttag_text())
        if tag in {
            "a",
            "pre",
            "code",
            "math",
            "script",
            "style",
            "textarea",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.skip.append(tag)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        """Preserve void/XML tags without entering a skip region."""
        self._flush_data()
        self.output.append(self.get_starttag_text())

    def handle_endtag(self, tag: str) -> None:
        """Leave a protected subtree."""
        self._flush_data()
        self.output.append(f"</{tag}>")
        if self.skip and self.skip[-1] == tag:
            self.skip.pop()

    def handle_data(self, data: str) -> None:
        """Buffer prose across entity boundaries; preserve protected nodes verbatim."""
        if self.skip:
            self.output.append(data)
        else:
            self.pending.append(data)

    def _flush_data(self) -> None:
        if not self.pending:
            return
        data = "".join(self.pending)
        self.pending.clear()
        # Process untouched text chunks separately: never match inside generated attributes.
        pieces, end = [], 0
        for match in PAREN_CITATION.finditer(data):
            pieces.append(self.pattern.sub(self._replace, data[end : match.start()]))
            pieces.append(self._parenthetical(match))
            end = match.end()
        pieces.append(self.pattern.sub(self._replace, data[end:]))
        self.output.append("".join(pieces))

    def handle_entityref(self, name: str) -> None:
        """Keep authored entity references."""
        (self.output if self.skip else self.pending).append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """Keep protected numeric MathML character references."""
        (self.output if self.skip else self.pending).append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        """Keep source comments, such as code captions."""
        self._flush_data()
        self.output.append(f"<!--{data}-->")
