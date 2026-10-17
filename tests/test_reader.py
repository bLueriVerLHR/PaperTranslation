"""Synthetic regressions for presentation-only metadata and citation transformations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import build, reader


def test_auxiliary_blocks_leave_technical_prose_and_math_intact() -> None:
    formula = '<div class="equation"><math><mi>x</mi></math></div>'
    source = (
        '<h2 id="info">论文信息</h2><p>Author A</p>'
        '<h2 id="abstract">摘要</h2><p>实际正文。</p>'
        + formula
        + '<h3 id="declaration">声明：给局部量一个位置</h3><p>技术说明。</p>'
        '<h2 id="refs">参考文献</h2><p>保留原文。</p>'
        '<ol class="references"><li>Alpha. Work. https://example.org/work</li></ol>'
        '<h2 id="rights">出版说明（原文）</h2>'
        "<p>© Original Author; exclusive rights retained.</p>"
        "<p>Publisher’s Note Neutrality boilerplate.</p>"
    )
    body, notes, references = reader.split_auxiliary(source)
    assert formula in body
    assert 'id="declaration"' in body
    assert 'id="info"' not in body
    assert "参考文献" not in body
    assert "Author A" in notes
    assert "exclusive rights retained" in notes
    assert "Neutrality boilerplate" not in notes
    assert references["1"]["url"] == "https://example.org/work"


@pytest.mark.parametrize(
    "bibliography",
    [
        "1. Original Author. [Work](https://example.org/work).",
        '<ol markdown="1"><li markdown="1"><p markdown="span">'
        "Original Author. [Work](https://example.org/work).</p></li></ol>",
    ],
)
def test_composed_essay_preserves_original_sections_notes_and_anchors(
    tmp_path: Path, bibliography: str
) -> None:
    content = tmp_path / "work/content"
    content.mkdir(parents=True)
    (content / "00-essay.md").write_text(
        '<div class="translated-essay" markdown="1">\n\n'
        "## 正文 {#original-body}\n\n原有论证 [1] 与注释[^one]。\n\n"
        "## 致谢 {#original-ack}\n\n原有致谢。\n\n"
        "## References {#original-refs}\n\n"
        + bibliography
        + "\n\n[^one]: 完整原有注释。\n\n</div>\n",
        encoding="utf-8",
    )
    (content.parent / "reader.json").write_text(
        json.dumps(
            {
                "references": {
                    "1": {"text": "Original Author. Work.", "url": "https://example.org/work"}
                }
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "reader"
    manifest = build.build(output, content, metadata={"title": "Synthetic essay"})
    page = (output / "index.html").read_text(encoding="utf-8")
    body = page.split('<article class="body">', 1)[1].split("</article>", 1)[0]
    for anchor in ("original-body", "original-ack", "original-refs", "fn:one"):
        assert f'id="{anchor}"' in body
    assert "原有论证" in body and "原有致谢。" in body
    assert "Original Author." in body and "完整原有注释。" in body
    assert manifest["citations_linked"] == 1


def test_reference_numbering_and_explicit_doi() -> None:
    references = reader.ReferenceItems(
        '<ol start="3"><li>First. 10.1000/example.</li>'
        '<li value="8"><em>Second</em>. <a href="https://example.org/two">source</a></li></ol>'
    ).items
    assert list(references) == ["3", "8"]
    assert references["3"]["url"] == "https://doi.org/10.1000/example"
    assert "Second" in references["8"]["text"]


def test_numbered_ranges_and_protected_subtrees() -> None:
    refs = {
        str(i): {"text": f"Original reference {i}", "url": f"https://example.org/{i}"}
        for i in range(1, 6)
    }
    code = "<pre><code>array[1]; [1–5]</code></pre>"
    math = "<math><mtext>[1]</mtext><mi>&#95;</mi></math>"
    existing = '<a href="https://example.org/other">[1]</a>'
    source = f"<p>见 [1–5]；数值域 [0,1]。</p>{code}{math}{existing}<!-- keep -->"
    result = reader.CitationLinker(source, refs, "https://example.org/paper")
    text = "".join(result.output)
    assert result.linked == 1
    assert code in text and math in text and existing in text
    assert "数值域 [0,1]" in text
    assert "[1–5]</a>" in text
    assert "<!-- keep -->" in text
    assert reader.citation_numbers("[1–3, 5, 2]") == ["1", "2", "3", "5"]
    assert reader.citation_numbers("[5–1]") == []
    assert reader.citation_numbers("[1–999]") == []


def test_author_year_and_unknown_entry_are_honest() -> None:
    refs = {
        "known": {
            "text": 'A. Alpha. "Original title" (2024).',
            "label": "Alpha 2024",
            "url": "https://example.org/work",
            "aliases": ["Alpha et al., 2024"],
        }
    }
    result = reader.CitationLinker(
        "<p>（Alpha et al., 2024; Beta, 2025）与 [9]。</p>", refs, "https://example.org/paper"
    )
    text = "".join(result.output)
    assert result.linked == 3
    assert result.unresolved == {"Beta, 2025", "9"}
    assert "&quot;Original title&quot;" in text
    assert "未能确定对应参考文献" in text
    assert 'href="https://example.org/work"' in text
    assert text.count('href="https://example.org/paper"') == 2
    assert "没有" not in text
    assert "Alpha 2024" in text
    assert 'aria-label="引用 Alpha et al., 2024，点击查看来源详情"' in text


def test_entity_boundaries_and_author_year_numeric_intervals() -> None:
    refs = {"entry": {"text": "Original bibliography", "aliases": ["Alpha & Beta, 2024"]}}
    code = "<code>&#91;1&#93; &amp;</code>"
    source = "<p>（Alpha &amp; Beta, 2024）与 Alpha &amp; Beta, 2024；数值区间 [1,8]。</p>" + code
    result = reader.CitationLinker(source, refs, "https://example.org/paper", "author-year")
    text = "".join(result.output)
    assert result.linked == 2
    assert result.unresolved == set()
    assert "数值区间 [1,8]" in text
    assert code in text
    assert "Alpha &amp; Beta, 2024</a>" in text


def test_no_source_or_records_means_no_fabricated_link() -> None:
    result = reader.CitationLinker("<p>[1]（Alpha, 2024）</p>", {}, None)
    assert "".join(result.output) == "<p>[1]（Alpha, 2024）</p>"


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///C:/private.pdf",
        "//example.org/paper",
        "https://user:secret@example.org/",
    ],
)
def test_unsafe_urls_are_refused(url: str, tmp_path: Path) -> None:
    (tmp_path / "reader.json").write_text(json.dumps({"source_url": url}), encoding="utf-8")
    with pytest.raises(ValueError, match="URL"):
        reader.load_profile(tmp_path)


def test_ambiguous_alias_is_refused() -> None:
    references = {str(i): {"text": "original", "aliases": ["Alpha, 2024"]} for i in (1, 2)}
    with pytest.raises(ValueError, match="ambiguous"):
        reader.CitationLinker("<p>Alpha, 2024</p>", references, None)


def test_build_moves_metadata_but_preserves_canonical_inputs(tmp_path: Path) -> None:
    work = tmp_path / "work"
    content = work / "content"
    content.mkdir(parents=True)
    original = "## 论文信息\n\nAuthor original\n\n## 摘要\n\n见 [1]。\n\n## 参考文献\n\n1. A. Work. https://example.org/work\n"
    section = content / "00-front.md"
    section.write_text(original, encoding="utf-8")
    notes = work / "reader-meta.md"
    notes.write_text("译自真实来源；保留第一人称。", encoding="utf-8")
    profile = work / "reader.json"
    profile.write_text(json.dumps({"source_url": "https://example.org/paper"}), encoding="utf-8")
    manifest = build.build(
        tmp_path / "out", content, metadata={"title": "A < B", "author": "A & B"}
    )
    result = (tmp_path / "out/index.html").read_text(encoding="utf-8")
    header, body = result.split('<article class="body">')
    assert "Author original" in header and "保留第一人称" in header
    assert "Author original" not in body and "保留第一人称" not in body
    assert "<footer" not in result
    assert "论文信息</a>" not in result and "参考文献</a>" not in result
    assert "摘要</a>" in result
    assert 'class="citation"' in body
    assert "A &lt; B" in result and "A &amp; B" in result
    assert "译文与图示的版权归原作者" in header
    assert "非出版社版本" not in header
    assert "公开传播授权" not in header
    assert section.read_text(encoding="utf-8") == original
    assert manifest["citations_linked"] == 1
    first_hash = manifest["content_hash"]
    notes.write_text("补充译注", encoding="utf-8")
    second = build.build(tmp_path / "out", content, metadata={"title": "test"})
    assert second["content_hash"] != first_hash
