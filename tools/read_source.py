"""Read bounded content from saved HTML without fetching or executing it."""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.web import Element, _Parser  # noqa: E402

DROP = {
    "head",
    "script",
    "style",
    "nav",
    "footer",
    "noscript",
    "template",
    "form",
    "button",
    "input",
    "select",
    "textarea",
}
BLOCK = {
    "p",
    "div",
    "section",
    "article",
    "main",
    "header",
    "aside",
    "blockquote",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "details",
    "summary",
    "figure",
    "figcaption",
    "pre",
    "table",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}


@dataclass(frozen=True)
class ContentBlock:
    """One extracted block; its number is not an HTML source line."""

    text: str
    kind: str
    anchor: str


class ReadingParser(_Parser):
    """Recover common omitted end tags; reject deep trees before recursive rendering.

    This local reading view is not an HTML5 browser parser. The pipeline's existing
    parser is unchanged, and unsupported malformed input is never accepted as evidence.
    """

    MAX_DEPTH = 96
    P_BREAKS = BLOCK | {"hr", "address"}

    def _open(self, tag: str, attrs: list[tuple[str, str | None]], self_closing: bool) -> None:
        local = tag.rsplit(":", 1)[-1].lower()
        if local in self.P_BREAKS:
            for index in range(len(self.stack) - 1, 0, -1):
                if self.stack[index].tag == "p":
                    del self.stack[index:]
                    break
                if self.stack[index].tag in {"body", "main", "table", "td", "th"}:
                    break
        if local in {"li", "dt", "dd"}:
            siblings = {"li"} if local == "li" else {"dt", "dd"}
            boundary = {"ul", "ol"} if local == "li" else {"dl"}
            for index in range(len(self.stack) - 1, 0, -1):
                if self.stack[index].tag in boundary:
                    break
                if self.stack[index].tag in siblings:
                    del self.stack[index:]
                    break
        if not self_closing and local not in self.VOID and len(self.stack) >= self.MAX_DEPTH:
            raise ValueError(
                "HTML nesting exceeds reading limit; select/repair the original source"
            )
        super()._open(tag, attrs, self_closing)


def walk(node: Element):
    """Visit document elements iteratively in source order."""
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(c for c in reversed(current.children) if isinstance(c, Element))


def serialize(node: Element) -> str:
    """Retain MathML tree structure, not a byte-identical original serialization."""
    attrs = "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in node.attrs.items())
    body = "".join(html.escape(c) if isinstance(c, str) else serialize(c) for c in node.children)
    return f"<{node.tag}{attrs}>{body}</{node.tag}>"


def inline(node: Element) -> str:
    """Expose inline prose without joining separate code tokens with invented spaces."""
    if node.tag in DROP:
        return ""
    if node.tag == "math":
        return serialize(node)
    if node.tag == "svg":
        return "[SVG graphic: inspect original/visual source for meaning]"
    if node.tag == "img":
        return f"[image: {node.attr('alt') or 'no alternative text'}]"
    if node.tag == "br":
        return "\n"
    return "".join(c if isinstance(c, str) else inline(c) for c in node.children)


def content_blocks(source: str, *, element_id: str | None = None) -> list[ContentBlock]:
    """Extract source-order content with explicit scope and preserved code/math."""
    parser = ReadingParser()
    parser.feed(source)
    parser.close()
    root = parser.root
    if element_id:
        found = [n for n in walk(root) if n.attr("id") == element_id]
        if len(found) != 1:
            raise ValueError("--id must identify exactly one element; no scope guessed")
        root = found[0]
    else:
        mains = root.find_all("main")
        bodies = root.find_all("body")
        if len(mains) == 1:
            root = mains[0]
        elif len(bodies) == 1:
            root = bodies[0]
    result: list[ContentBlock] = []

    def visit(node: Element, inherited: str = "") -> None:
        if node.tag in DROP:
            return
        anchor = node.attr("id") or inherited
        if node.tag == "pre":
            result.append(ContentBlock(inline(node), "code", anchor))
            return
        if node.tag == "table":
            rows = [
                " | ".join(
                    inline(c).strip()
                    for c in row.children
                    if isinstance(c, Element) and c.tag in {"th", "td"}
                )
                for row in node.find_all("tr")
            ]
            captions = [inline(c).strip() for c in node.find_all("caption")]
            result.append(ContentBlock("\n".join(captions + rows), "table", anchor))
            return
        buffer: list[str] = []

        def flush() -> None:
            parts = re.split(r"(<math\b.*?</math>)", "".join(buffer), flags=re.S)
            text = "".join(
                p if p.startswith("<math") else re.sub(r"\s+", " ", p) for p in parts
            ).strip()
            buffer.clear()
            if text:
                result.append(ContentBlock(text, node.tag, anchor))

        for child in node.children:
            if isinstance(child, Element) and child.tag in BLOCK:
                flush()
                visit(child, anchor)
            else:
                buffer.append(child if isinstance(child, str) else inline(child))
        flush()

    visit(root)
    return result


def render(
    blocks: list[ContentBlock],
    *,
    start: int = 1,
    count: int = 12,
    find: str | None = None,
    outline: bool = False,
    max_chars: int = 6000,
    within: int = 0,
) -> str:
    """Produce bounded plain output with visible selection/continuation information."""
    if start < 1 or count < 1 or max_chars < 200 or within < 0:
        raise ValueError("start/count must be positive; max-chars >= 200; within >= 0")
    eligible = [
        i
        for i in range(start - 1, len(blocks))
        if (not outline or re.fullmatch(r"h[1-6]", blocks[i].kind))
        and (find is None or find.casefold() in blocks[i].text.casefold())
    ]
    selected = eligible[:count]
    lines = [f"HTML content: {len(blocks)} blocks (not source lines; page chrome omitted)."]
    if not selected:
        return "\n".join([*lines, "No matching blocks; this is not a full-reading result."])
    used = 0
    for index in selected:
        block = blocks[index]
        offset = within if index == selected[0] else 0
        if offset >= len(block.text) and offset:
            raise ValueError("--within is outside the first selected block")
        label = f"\n[{index + 1} {block.kind}{' #' + block.anchor if block.anchor else ''}]\n"
        remaining = max_chars - used - len(label)
        if remaining <= 0:
            lines.append(f"CONTINUE: --start {index + 1}; selected output is incomplete.")
            break
        text = block.text[offset : offset + remaining]
        lines.append(label + text)
        used += len(label) + len(text)
        if offset + len(text) < len(block.text):
            lines.append(f"INCOMPLETE BLOCK: --start {index + 1} --within {offset + len(text)}")
            break
    else:
        next_index = eligible[len(selected)] + 1 if len(eligible) > len(selected) else None
        lines.append(
            f"CONTINUE: --start {next_index}"
            if next_index
            else "End of selected scope; search/outline alone does not prove full reading."
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Read a local saved HTML file; never create a derivative or make network requests."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--id", dest="element_id")
    parser.add_argument("--outline", action="store_true")
    parser.add_argument("--find", help="literal phrase in extracted content, not HTML attributes")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--within", type=int, default=0)
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--encoding", default="utf-8-sig")
    args = parser.parse_args(argv)
    try:
        if args.file.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("file exceeds the 16 MiB reading limit; select a smaller source")
        blocks = content_blocks(
            args.file.read_text(encoding=args.encoding), element_id=args.element_id
        )
        print(
            render(
                blocks,
                start=args.start,
                count=args.count,
                within=args.within,
                find=args.find,
                outline=args.outline,
                max_chars=args.max_chars,
            )
        )
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"Cannot read source: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
