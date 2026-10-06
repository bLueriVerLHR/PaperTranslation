"""Validate opt-in question/answer banks without rewriting their canonical HTML."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser

from tools.reader import VOID


@dataclass
class Node:
    """Minimal HTML tree used only for structural validation."""

    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    text: list[str] = field(default_factory=list)

    def has(self, name: str) -> bool:
        """Check a complete class token, not a substring."""
        return name in (self.attrs.get("class") or "").split()

    def walk(self):
        """Yield this node and its descendants in document order."""
        yield self
        for child in self.children:
            yield from child.walk()

    def readable(self) -> str:
        """Collect text for detecting empty questions and answers."""
        return " ".join(text for node in self.walk() for text in node.text).strip()


class Tree(HTMLParser):
    """Read already-rendered trusted manuscript HTML; do not sanitize or serialize it."""

    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.feed(source)
        self.close()

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Append one element and descend into non-void tags."""
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        """Treat self-closing MathML and HTML as leaves."""
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag: str) -> None:
        """Leave the matching element, preserving HTML's permissive outer parsing."""
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        """Keep text, not markup or entity spellings."""
        self.stack[-1].text.append(data)


def validate(source: str) -> list[dict]:
    """Return bank inventories; reject malformed opt-in pairs and ambiguous identifiers.

    The canonical HTML stays fully expanded. No question syntax is inferred from normal
    prose or headings; only explicit qa-bank/qa-item/qa-question/qa-answer classes opt in.
    """
    root = Tree(source).root
    nodes = list(root.walk())
    roles = {"qa-bank", "qa-item", "qa-question", "qa-answer"}
    marked = [node for node in nodes if roles.intersection((node.attrs.get("class") or "").split())]
    if not marked:
        return []
    for node in marked:
        if len(roles.intersection((node.attrs.get("class") or "").split())) != 1:
            raise ValueError("each question-bank element must have exactly one structural role")
        if "hidden" in node.attrs:
            raise ValueError(
                "canonical question banks and pairs must remain visible without JavaScript"
            )
    identifiers = Counter(node.attrs["id"] for node in nodes if node.attrs.get("id"))
    duplicates = [key for key, count in identifiers.items() if count > 1]
    if duplicates:
        raise ValueError(f"question banks require unique document IDs: {duplicates}")
    consumed = set()
    result = []
    for bank in (node for node in nodes if node.has("qa-bank")):
        if bank.tag != "div" or not re.fullmatch(r"[a-z][a-z0-9-]*", bank.attrs.get("id") or ""):
            raise ValueError("qa-bank must be a div with a stable ASCII id")
        consumed.add(id(bank))
        items = [child for child in bank.children if child.has("qa-item")]
        if not items:
            raise ValueError("qa-bank must contain direct qa-item children")
        item_ids = []
        for item in items:
            key = item.attrs.get("id") or ""
            if item.tag != "article" or not re.fullmatch(r"[a-z][a-z0-9-]*", key):
                raise ValueError("qa-item must be an article with a stable ASCII id")
            if len(item.children) != 2:
                raise ValueError(f"{key}: require exactly one question followed by one answer")
            question, answer = item.children
            if not (
                question.tag == "p"
                and question.has("qa-question")
                and answer.tag == "div"
                and answer.has("qa-answer")
            ):
                raise ValueError(f"{key}: require p.qa-question then div.qa-answer")
            if not question.readable() or not answer.readable():
                raise ValueError(f"{key}: question and answer cannot be empty")
            if any(
                node.tag in {"a", "button", "input", "select", "textarea", "details"}
                for node in question.walk()
            ):
                raise ValueError(f"{key}: question cannot contain interactive elements")
            consumed.update((id(item), id(question), id(answer)))
            item_ids.append(key)
        result.append({"id": bank.attrs["id"], "questions": item_ids})
    if any(id(node) not in consumed for node in marked):
        raise ValueError(
            "question/answer markers must belong to a valid direct pair; nested banks are not supported"
        )
    return result
