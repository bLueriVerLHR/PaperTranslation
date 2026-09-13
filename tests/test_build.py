"""Unit tests for the build pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import build

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CONTENT = Path(__file__).resolve().parent / "fixtures" / "sample-content"
FIXTURE_FIGURES = Path(__file__).resolve().parent / "fixtures" / "assets" / "figures"
FIXTURE_METADATA = {"title": "样例标题", "subtitle": "样例副标题", "author": "样例作者"}


def test_slugify_ascii() -> None:
    assert build.slugify("Hello World!") == "hello-world"
    assert build.slugify("2.1 Overview") == "21-overview"


def test_slugify_keeps_cjk() -> None:
    assert build.slugify("2.1 总览") == "21-总览"
    assert build.slugify("样例机制（CSA2）") == "样例机制csa2"


def test_slugify_empty_has_fallback() -> None:
    assert build.slugify("！！！") == "section"


def test_render_toc_nests_children() -> None:
    tokens = [
        {
            "level": 2,
            "id": "a",
            "name": "A",
            "children": [{"level": 3, "id": "b", "name": "B", "children": []}],
        }
    ]
    html = build.render_toc(tokens)
    assert '<a href="#a">A</a>' in html
    assert '<a href="#b">B</a>' in html
    assert html.count("<ol>") == 2


def test_render_toc_empty() -> None:
    assert build.render_toc([]) == ""


def test_wrap_tables_wraps_once() -> None:
    html = "<p>x</p>\n<table><tr><td>1</td></tr></table>\n"
    once = build.wrap_tables(html)
    assert '<div class="table-wrap"><table>' in once
    assert build.wrap_tables(once) == once


def test_combine_toc_merges_sections(tmp_path: Path) -> None:
    (tmp_path / "01-a.md").write_text("## 甲\n\ntext\n", encoding="utf-8")
    (tmp_path / "02-b.md").write_text("## 乙\n\n## 丙\n", encoding="utf-8")
    sections = build.read_sections(tmp_path)
    toc = build.combine_toc(sections)
    assert toc.count("<li>") == 3


def test_build_end_to_end(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "01-intro.md").write_text(
        "## 1 引言\n\n这是一个测试。\n\n"
        '<div class="equation"><math display="block"><mi>x</mi></math>'
        '<span class="eqno">(1)</span></div>\n',
        encoding="utf-8",
    )
    dist = tmp_path / "dist"

    manifest = build.build(
        dist=dist,
        build_date="2026-01-01",
        content_dir=content,
        template_path=REPO_ROOT / "src" / "templates" / "page.html",
        styles_dir=tmp_path / "no-styles",
        scripts_dir=tmp_path / "no-scripts",
        figures_dir=None,
        fonts_dir=None,
        metadata=FIXTURE_METADATA,
    )

    page = (dist / "index.html").read_text(encoding="utf-8")
    assert "这是一个测试。" in page
    assert "样例作者" in page
    assert '<a href="#1-引言">1 引言</a>' in page
    assert "<math" in page
    assert "{{" not in page
    assert manifest["content_hash"] == build.content_hash(build.read_sections(content))
    assert (dist / "manifest.json").exists()


def test_build_rejects_unknown_placeholder(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "01-a.md").write_text("## 甲\n", encoding="utf-8")
    template = tmp_path / "page.html"
    template.write_text("<p>{{MYSTERY}}</p>", encoding="utf-8")
    with pytest.raises(ValueError, match="unresolved template placeholders"):
        build.build(
            dist=tmp_path / "dist",
            content_dir=content,
            template_path=template,
            styles_dir=tmp_path / "s",
            scripts_dir=tmp_path / "j",
            figures_dir=None,
            fonts_dir=None,
            metadata=FIXTURE_METADATA,
        )


def test_build_is_additive_across_sections(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "01-a.md").write_text("## 甲\n\n第一段。\n", encoding="utf-8")
    (content / "02-b.md").write_text("## 乙\n\n第二段。\n", encoding="utf-8")
    dist = tmp_path / "dist"

    build.build(
        dist=dist,
        content_dir=content,
        template_path=REPO_ROOT / "src" / "templates" / "page.html",
        styles_dir=tmp_path / "s",
        scripts_dir=tmp_path / "j",
        figures_dir=None,
        fonts_dir=None,
        metadata=FIXTURE_METADATA,
    )
    (content / "03-c.md").write_text("## 丙\n\n第三段。\n", encoding="utf-8")
    build.build(
        dist=dist,
        content_dir=content,
        template_path=REPO_ROOT / "src" / "templates" / "page.html",
        styles_dir=tmp_path / "s",
        scripts_dir=tmp_path / "j",
        figures_dir=None,
        fonts_dir=None,
        metadata=FIXTURE_METADATA,
    )

    page = (dist / "index.html").read_text(encoding="utf-8")
    assert "第一段。" in page and "第二段。" in page and "第三段。" in page


def test_sample_fixture_exercises_every_rendering_path(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    build.build(
        dist=dist,
        build_date="2026-01-01",
        content_dir=FIXTURE_CONTENT,
        template_path=REPO_ROOT / "src" / "templates" / "page.html",
        styles_dir=REPO_ROOT / "src" / "styles",
        scripts_dir=REPO_ROOT / "src" / "scripts",
        figures_dir=FIXTURE_FIGURES,
        fonts_dir=REPO_ROOT / "src" / "assets" / "fonts",
        metadata=FIXTURE_METADATA,
    )
    page = (dist / "index.html").read_text(encoding="utf-8")

    # MathML survives Markdown untouched and the equation number stays outside it.
    assert '<math display="block">' in page
    assert '<span class="eqno">(11)</span>' in page
    assert 'class="equation"' in page

    # Figure, table, pseudocode and footnotes render.
    assert "<figure>" in page
    assert "figure-03.png" in page
    assert "<table>" in page
    assert '<div class="table-wrap">' in page
    assert "alg-keyword" in page
    assert 'class="footnote"' in page

    # The TOC is folded by default and keeps CJK anchors, including nesting.
    assert '<details class="toc" id="toc">' in page
    assert '<details class="toc" id="toc" open>' not in page
    assert 'href="#21-样例小节"' in page
    assert 'href="#211-更深一层"' in page

    # Assets are copied next to the page so it works offline from file://.
    assert (dist / "assets" / "styles" / "reader.css").exists()
    assert (dist / "assets" / "scripts" / "reader.js").exists()
    assert (dist / "assets" / "figures" / "figure-03.png").exists()
