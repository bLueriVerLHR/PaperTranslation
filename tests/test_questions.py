"""Structural regression tests for explicit, progressively enhanced question banks."""

from pathlib import Path

import pytest

from tools import build, questions

PAIR = """<article class="qa-item" id="qa-one" markdown="1">
<p class="qa-question">为什么需要 RAII？</p>
<div class="qa-answer" markdown="1">

**回答。** 对象管理资源 [1]。

```cpp
int value = 1;
```

<math><mi>x</mi></math>

</div>
</article>"""


def bank(pair: str = PAIR) -> str:
    """Wrap synthetic paired content in one explicit bank."""
    return '<div class="qa-bank" id="test-bank" markdown="1">\n\n' + pair + "\n\n</div>"


def test_bank_markdown_and_manifest(tmp_path: Path) -> None:
    """Preserve rich answers, citations and dependency provenance without hiding them."""
    content = tmp_path / "work/content"
    parts = content / "questions"
    parts.mkdir(parents=True)
    (content / "06-questions.md").write_text(
        "## 八股文\n\n" + bank("{{include:questions/one.md}}"), encoding="utf-8"
    )
    (parts / "one.md").write_text(PAIR, encoding="utf-8")
    (content.parent / "reader.json").write_text(
        '{"references":{"1":{"text":"Synthetic source","url":"https://example.org/source"}}}',
        encoding="utf-8",
    )
    output = tmp_path / "reader"
    manifest = build.build(output, content, metadata={"title": "Questions", "kind": "review"})
    html = (output / "index.html").read_text(encoding="utf-8")
    assert manifest["question_banks"] == [{"id": "test-bank", "questions": ["qa-one"]}]
    assert manifest["content_dependencies"]["06-questions.md"] == [
        "06-questions.md",
        "questions/one.md",
    ]
    assert 'class="qa-answer"' in html and 'class="syn-kt"' in html
    assert "<math>" in html and "<strong>回答。</strong>" in html
    assert 'class="citation"' in html
    assert 'markdown="1"' not in html
    assert '<div class="qa-answer" hidden' not in html
    assert manifest["citations_without_records"] == []


def test_question_bank_ids_cannot_collide_with_reader_chrome(tmp_path: Path) -> None:
    """Final-page validation covers template IDs as well as Markdown IDs."""
    content = tmp_path / "work/content"
    content.mkdir(parents=True)
    (content / "01.md").write_text(bank().replace('id="test-bank"', 'id="toc"'), encoding="utf-8")
    with pytest.raises(ValueError, match="unique document IDs"):
        build.build(tmp_path / "reader", content, metadata={"title": "Collision", "kind": "review"})


def test_ordinary_question_prose_is_not_a_bank() -> None:
    """Ordinary headings, question marks and Q&A words must not opt in."""
    html = build.make_markdown().convert("## 为什么？\n\n问题：对象是什么？\n\n回答：正文。")
    assert questions.validate(html) == []


@pytest.mark.parametrize(
    "pair",
    [
        PAIR.replace('class="qa-answer"', 'class="answer"'),
        PAIR.replace('class="qa-question"', 'class="question"'),
        PAIR.replace("为什么需要 RAII？", " "),
        PAIR.replace('id="qa-one"', 'id="Bad ID"'),
        PAIR.replace('class="qa-answer"', 'class="qa-answer" hidden'),
        PAIR.replace('class="qa-question"', 'class="qa-question" hidden'),
        PAIR.replace('class="qa-item"', 'class="qa-item" hidden'),
        PAIR.replace('class="qa-answer"', 'class="qa-answer qa-bank"'),
        PAIR.replace("为什么需要 RAII？", '<a href="https://example.org">问题</a>'),
        PAIR + PAIR,
        PAIR.replace("</article>", "<p>额外未配对内容</p></article>"),
    ],
)
def test_invalid_pairs_fail_the_build(pair: str) -> None:
    """Malformed or ambiguous pairs fail instead of becoming inaccessible answers."""
    with pytest.raises(ValueError):
        questions.validate(build.make_markdown().convert(bank(pair)))


@pytest.mark.parametrize(
    "html",
    [
        '<div class="qa-bank" id="empty"></div>',
        bank().replace('class="qa-bank"', 'class="qa-bank" hidden'),
        '<p class="qa-question">没有题库</p>',
        '<div class="qa-bank" id="outer">' + bank() + "</div>",
        '<p id="test-bank">冲突</p>' + bank(),
    ],
)
def test_invalid_bank_ownership_and_ids(html: str) -> None:
    """Reject empty/nested/orphaned banks and IDs colliding with ordinary prose."""
    with pytest.raises(ValueError):
        questions.validate(build.make_markdown().convert(html))
