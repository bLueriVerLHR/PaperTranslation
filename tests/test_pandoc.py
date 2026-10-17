"""Two document-level contracts, not a second test suite for Pandoc's syntax."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tools import build

ROOT = Path(__file__).resolve().parents[1]


class Texts(HTMLParser):
    """Read selected code text and identities without reserializing generated HTML."""

    def __init__(self, html: str):
        super().__init__()
        self.ids = []
        self.code = ""
        self.in_code = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "code":
            self.in_code = True

    def handle_endtag(self, tag):
        if tag == "code":
            self.in_code = False

    def handle_data(self, data):
        if self.in_code:
            self.code += data


def test_document_build_preserves_semantics_and_global_identities(tmp_path: Path) -> None:
    pytest.importorskip("pypandoc")
    work = tmp_path / "work"
    content = work / "content"
    content.mkdir(parents=True)
    (content / "01-main.md").write_bytes((ROOT / "tests/fixtures/pandoc-document.md").read_bytes())
    (content / "02-end.md").write_text(
        "## 中文章节\n\n另一条注释。[^second]\n\n"
        "<math><mi>x</mi><mo>*</mo><mi>y</mi></math>\n\n[^second]: 第二条完整注释。",
        encoding="utf-8",
    )
    (work / "reader.json").write_text(
        json.dumps({"renderer": "pandoc", "show_glossary": True}), encoding="utf-8"
    )
    (work / "reader-meta.md").write_text(
        "出处说明。[^source]\n\n[^source]: 来源条件。", encoding="utf-8"
    )
    (work / "glossary.md").write_text(
        "## 术语\n\n| 英文 | 中文 |\n| --- | --- |\n| token | 词元 |", encoding="utf-8"
    )
    output = tmp_path / "output"
    manifest = build.build(
        output,
        content,
        metadata={"title": "合成文档", "author": "示例"},
        figures_dir=ROOT / "tests/fixtures/assets/figures",
    )
    raw = (output / "index.html").read_bytes()
    html = raw.decode("utf-8")
    parsed = Texts(html)
    assert b"\r" not in raw
    assert len(parsed.ids) == len(set(parsed.ids))
    assert set(re.findall(r'href="#([^\"]+)"', html)) <= set(parsed.ids)
    assert parsed.code == "    def probe(x):\n        return x < 2"
    assert html.count("<math") == 3 and "<mfrac>" in html and "<mtable>" in html
    assert "application/x-tex" not in html and "MathJax" not in html and "katex" not in html
    assert '<figure id="fig-flow">' in html and "<figcaption" in html
    assert html.count('role="doc-endnotes"') == 1
    assert html.count('role="doc-noteref"') == 3
    header, body = html.split("</header>", 1)
    assert "出处说明" in header and "词元" in header and "词元" not in body
    assert 'href="#stable-heading"' in body and 'id="author-ack"' in body
    assert "原作者的致谢属于正文" in body
    assert manifest["renderer"]["name"] == "pandoc" and manifest["renderer"]["version"]
    assert (output / "assets/figures/figure-03.png").is_file()
    assert (tmp_path / "assets/styles/reader.css").is_file()


def test_invalid_math_never_overwrites_an_existing_reader(tmp_path: Path) -> None:
    pytest.importorskip("pypandoc")
    content = tmp_path / "work/content"
    content.mkdir(parents=True)
    (content.parent / "reader.json").write_text('{"renderer": "pandoc"}', encoding="utf-8")
    (content / "01-main.md").write_text(r"$\DefinitelyUnknownMacro{x}$", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    (output / "index.html").write_text("existing reader", encoding="utf-8")
    with pytest.raises(ValueError, match="Pandoc rendering failed"):
        build.build(output, content, metadata={"title": "合成文档"})
    assert (output / "index.html").read_text(encoding="utf-8") == "existing reader"
