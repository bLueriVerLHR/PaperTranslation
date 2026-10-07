"""Readable local HTML views, without network or rendered-layout assumptions."""

from pathlib import Path

import pytest

from tools import read_source


def test_content_first_preserves_code_table_and_math() -> None:
    source = """<head><style>noise</style></head><body><nav>navigation</nav>
    <main><h2 id="topic">Actual mechanism</h2><p>A <b>useful</b> condition.</p>
    <pre><code>if (a &lt; b) {\n  use(a);\n}</code></pre>
    <p>Ratio <math><mfrac><mi>x</mi><mn>2</mn></mfrac><mtext>a   b</mtext></math>.</p>
    <table><caption>Cases</caption><tr><th>Key</th><th>Value</th></tr>
    <tr><td>a</td><td>7</td></tr></table><script>steal()</script></main>
    <footer>page chrome</footer></body>"""
    blocks = read_source.content_blocks(source)
    text = "\n".join(b.text for b in blocks)
    assert "noise" not in text and "navigation" not in text and "steal" not in text
    assert "page chrome" not in text
    assert blocks[0].anchor == "topic"
    assert "A useful condition." in text
    assert "if (a < b) {\n  use(a);\n}" in text
    assert "<mfrac><mi>x</mi><mn>2</mn></mfrac>" in text
    assert "<mtext>a   b</mtext>" in text
    assert "Cases\nKey | Value\na | 7" in text


def test_body_keeps_multiple_articles_and_explicit_scope() -> None:
    source = '<body><article id="one"><p>First</p></article><article id="two"><p>Second</p></article></body>'
    assert [b.text for b in read_source.content_blocks(source)] == ["First", "Second"]
    assert [b.text for b in read_source.content_blocks(source, element_id="two")] == ["Second"]
    with pytest.raises(ValueError, match="exactly one"):
        read_source.content_blocks(source, element_id="missing")
    with pytest.raises(ValueError, match="exactly one"):
        read_source.content_blocks('<p id="x">a</p><p id="x">b</p>', element_id="x")


def test_search_and_outline_do_not_claim_full_reading() -> None:
    blocks = read_source.content_blocks(
        "<h2>Heading</h2><p>Macro definitions</p><p>Other content</p>"
    )
    assert "Macro definitions" in read_source.render(blocks, find="macro", count=1)
    assert "Other content" not in read_source.render(blocks, find="macro", count=1)
    assert "Macro definitions" not in read_source.render(blocks, outline=True)
    assert "No matching" in read_source.render(blocks, find="absent")
    assert "does not prove full reading" in read_source.render(blocks, outline=True)
    assert "CONTINUE: --start 2" in read_source.render(blocks, count=1)


def test_large_block_has_lossless_explicit_continuation() -> None:
    text = "0123456789" * 70
    blocks = [read_source.ContentBlock(text, "code", "sample")]
    output = read_source.render(blocks, max_chars=200)
    assert "INCOMPLETE BLOCK" in output
    import re

    offset = int(re.search(r"--within (\d+)", output)[1])
    rest = read_source.render(blocks, start=1, within=offset, max_chars=2000)
    assert text[offset:] in rest
    with pytest.raises(ValueError, match="outside"):
        read_source.render(blocks, within=len(text))


def test_svg_image_and_control_limits_are_visible() -> None:
    blocks = read_source.content_blocks(
        '<p><svg><path d="huge payload"/></svg><img alt="diagram"></p><form>controls</form>'
    )
    text = read_source.render(blocks)
    assert "SVG graphic" in text and "image: diagram" in text
    assert "huge payload" not in text and "controls" not in text
    with pytest.raises(ValueError):
        read_source.render(blocks, start=0)


def test_omitted_paragraph_end_tags_keep_source_order() -> None:
    source = (
        "<body><h2>Section</h2>" + "".join(f"<p>Statement {i}." for i in range(500)) + "</body>"
    )
    blocks = read_source.content_blocks(source)
    assert len(blocks) == 501
    assert blocks[1].text == "Statement 0."
    assert blocks[-1].text == "Statement 499."


def test_omitted_list_ends_do_not_close_outer_item() -> None:
    blocks = read_source.content_blocks(
        "<ul><li>outer<ul><li>inner one<li>inner two</ul><li>next outer</ul>"
    )
    assert [b.text for b in blocks] == ["outer", "inner one", "inner two", "next outer"]


def test_deep_html_fails_before_recursive_rendering(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    source = "<span>" * 150 + "deep" + "</span>" * 150
    with pytest.raises(ValueError, match="nesting"):
        read_source.content_blocks(source)
    path = tmp_path / "deep.html"
    path.write_text(source, encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        read_source.main([str(path)])
    assert error.value.code == 1
    assert "nesting exceeds" in capsys.readouterr().err


def test_cli_is_read_only(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    path = tmp_path / "source.html"
    original = b'<h2 id="title">Title</h2><p>Relevant content</p>'
    path.write_bytes(original)
    assert read_source.main([str(path), "--find", "Relevant"]) == 0
    assert "Relevant content" in capsys.readouterr().out
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]
