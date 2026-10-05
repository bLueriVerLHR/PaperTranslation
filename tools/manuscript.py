"""Compose local Markdown modules and highlight explicit-language code offline."""

from __future__ import annotations

import re
from html import unescape
from pathlib import Path

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

INCLUDE = re.compile(r"^ {0,3}\{\{include:([^{}\n]+)\}\}\s*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
CODE = re.compile(r'<pre><code class="language-([^"<>]+)">(.*?)</code></pre>', re.DOTALL)
MAX_DEPTH = 24
MAX_BYTES = 8 * 1024 * 1024


def expand(path: Path, root: Path) -> tuple[str, list[Path]]:
    """Resolve relative includes inside root, rejecting escapes, cycles and oversized input.

    Only standalone directives outside fenced/indented code are interpreted. Included
    fragments are expanded in place before Markdown, so headings and references share
    the parent's namespace. Each returned dependency is unique, in first-read order.
    """
    root = root.resolve()
    dependencies: list[Path] = []
    size = 0

    def visit(current: Path, stack: tuple[Path, ...]) -> str:
        nonlocal size
        current = current.resolve()
        if not current.is_relative_to(root):
            raise ValueError(f"include escapes content root: {current}")
        if current in stack:
            chain = " -> ".join(str(p.relative_to(root)) for p in (*stack, current))
            raise ValueError(f"include cycle: {chain}")
        if len(stack) >= MAX_DEPTH:
            raise ValueError(f"include depth exceeds {MAX_DEPTH}: {current}")
        if current.suffix != ".md":
            raise ValueError(f"include must name a Markdown file: {current}")
        try:
            data = current.read_bytes()
        except FileNotFoundError as error:
            raise FileNotFoundError(f"missing include: {current}") from error
        size += len(data)
        if size > MAX_BYTES:
            raise ValueError(f"expanded manuscript exceeds {MAX_BYTES} bytes: {current}")
        if current not in dependencies:
            dependencies.append(current)
        lines = []
        fence_char, fence_length = "", 0
        for line in data.decode("utf-8").splitlines():
            fence = FENCE.match(line)
            if fence:
                marker, rest = fence.groups()
                if not fence_char:
                    fence_char, fence_length = marker[0], len(marker)
                elif marker[0] == fence_char and len(marker) >= fence_length and not rest.strip():
                    fence_char, fence_length = "", 0
                lines.append(line)
                continue
            directive = INCLUDE.fullmatch(line) if not fence_char else None
            if directive:
                target = directive.group(1).strip()
                # Backslashes are rejected so the same manuscript has the same semantics
                # on Windows and POSIX. resolve() also checks symlink/junction escapes.
                if not target or "\\" in target or ":" in target or Path(target).is_absolute():
                    raise ValueError(f"invalid include path in {current}: {target}")
                lines.extend(("", visit(current.parent / target, (*stack, current)), ""))
            else:
                lines.append(line)
        return "\n".join(lines) + "\n"

    return visit(path, ()), dependencies


class _Highlight(Postprocessor):
    """Add token spans without changing pre/code structure or guessing a language."""

    def run(self, text: str) -> str:
        """Highlight explicit known languages; unknown ones stay escaped plaintext."""

        def render(match: re.Match[str]) -> str:
            language, source = match.groups()
            try:
                lexer = get_lexer_by_name(unescape(language), stripnl=False, ensurenl=False)
            except ClassNotFound:
                return match.group(0)
            tokens = highlight(
                unescape(source), lexer, HtmlFormatter(nowrap=True, classprefix="syn-")
            )
            return f'<pre><code class="language-{language}">{tokens}</code></pre>'

        return CODE.sub(render, text)


class HighlightExtension(Extension):
    """Install a build-time highlighter after Markdown restores escaped HTML."""

    def extendMarkdown(self, md) -> None:  # noqa: N802 - Python-Markdown API
        """Keep fenced_code's compatible HTML and language classes."""
        md.postprocessors.register(_Highlight(md), "offline_highlight", 5)
