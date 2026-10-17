"""Upgrade explicitly identified fixed-version excerpts without guessing source identity."""

from __future__ import annotations

import re
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

# Compatibility with the complete caption emitted by the existing excerpt generator.
# Partial captions, arbitrary paths and unrelated paragraphs deliberately do not match.
CAPTION = re.compile(
    r"<p><strong>源码摘录：(?P<purpose>[^<>]+)。</strong>\s*"
    r"仓库 <code>(?P<repository>[^<>]+)</code>，固定提交 "
    r"<code>(?P<commit>[a-fA-F0-9]{40}|[a-fA-F0-9]{64})</code>；"
    r"文件 <code>(?P<path>[^<>]+)</code>，第 (?P<first>\d+)–(?P<last>\d+) 行，"
    r"符号 <code>(?P<symbol>[^<>]+)</code>。"
    r'<a href="(?P<url>[^"]+)">对应源码</a>。</p>\s*'
    r"(?P<pre><pre(?:\s[^>]*)?><code(?:\s[^>]*)?>.*?</code></pre>)",
    re.DOTALL,
)


class _CodeText(HTMLParser):
    """Read source text through token spans without interpreting escaped markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text = ""

    def handle_data(self, data: str) -> None:
        """Retain whitespace and code characters exactly."""
        self.text += data


def upgrade(text: str) -> str:
    """Wrap only complete legacy captions whose permalink agrees with every locator.

    The original pre/code subtree is retained verbatim. No repository is read, no URL is
    fetched, and no claim is made that the excerpt has been reverified against upstream.
    Already upgraded cards are unchanged, making snapshot refresh idempotent.
    """

    def replace(match: re.Match[str]) -> str:
        record = {key: unescape(value) for key, value in match.groupdict().items()}
        first, last = int(record["first"]), int(record["last"])
        path = PurePosixPath(record["path"])
        try:
            url = urlsplit(record["url"])
        except ValueError:
            return match.group(0)
        components = unquote(url.path).strip("/").split("/")
        if (
            first < 1
            or last < first
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in record["path"]
            or url.scheme != "https"
            or url.netloc.lower() != "github.com"
            or url.username
            or url.password
            or url.query
            or len(components) < 5
            or components[2] != "blob"
            or components[3] != record["commit"]
            or "/".join(components[4:]) != record["path"]
            or url.fragment != f"L{first}-L{last}"
        ):
            return match.group(0)
        code = _CodeText()
        code.feed(match["pre"])
        if len(code.text.splitlines()) != last - first + 1:
            return match.group(0)
        fields = (
            ("仓库", record["repository"]),
            ("提交", record["commit"]),
            ("路径", record["path"]),
            ("符号", record["symbol"]),
            ("行范围", f"{first}–{last}"),
        )
        details = "".join(
            f"<dt>{label}</dt><dd><code>{escape(value)}</code></dd>" for label, value in fields
        )
        return (
            '<figure class="source-excerpt">'
            f"<figcaption>{escape(record['purpose'])}</figcaption>"
            '<details class="code-source"><summary><span class="source-brief">'
            f'<span class="source-repo">{escape(record["repository"])}</span>'
            f'<span class="source-file">{escape(path.name)}</span>'
            f'<span class="source-lines">L{first}–{last}</span></span>'
            '<span class="source-toggle">出处</span></summary>'
            f'<dl class="source-fields">{details}<dt>原始来源</dt><dd>'
            f'<a href="{escape(record["url"], quote=True)}" target="_blank" '
            'rel="noopener noreferrer">查看固定版本源码 ↗</a></dd>'
            "<dt>归属</dt><dd>代码保留原项目的许可与权利归属。</dd></dl></details>"
            + match["pre"]
            + '<p class="source-tools"><span class="source-indent-note" hidden>'
            "公共缩进仅视觉收起，复制保留原文</span>"
            '<button type="button" data-copy-code hidden>复制原文</button></p></figure>'
        )

    return CAPTION.sub(replace, text)
