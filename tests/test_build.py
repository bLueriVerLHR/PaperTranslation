"""Unit tests for the build pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import build, paper

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CONTENT = Path(__file__).resolve().parent / "fixtures" / "sample-content"
FIXTURE_FIGURES = Path(__file__).resolve().parent / "fixtures" / "assets" / "figures"
FIXTURE_METADATA = {"title": "样例标题", "subtitle": "样例副标题", "author": "样例作者"}


@pytest.mark.parametrize(
    ("kind", "label", "notice"),
    [
        ("translation", "中文译文", "译文与图示的版权归原作者。"),
        ("analysis", "源码研读笔记", "源码与引用材料遵循各自原有许可证。"),
        ("review", "原创综述", "引用文献与图示遵循各自原有许可与权利要求。"),
    ],
)
def test_reader_kind_has_accurate_presentation(
    tmp_path: Path, kind: str, label: str, notice: str
) -> None:
    build.build(
        tmp_path / "output",
        FIXTURE_CONTENT,
        metadata={**FIXTURE_METADATA, "kind": kind},
    )
    page = (tmp_path / "output/index.html").read_text(encoding="utf-8")
    assert f" · {label} · " in page
    assert notice in page
    if kind == "review":
        assert "中文译文" not in page
        assert "源码研读笔记" not in page


def test_visible_glossary_uses_canonical_source_and_changes_hash(tmp_path: Path) -> None:
    work = tmp_path / "work"
    content = work / "content"
    content.mkdir(parents=True)
    (content / "01-body.md").write_text("## 正文\n\n词元表示。", encoding="utf-8")
    (work / "reader.json").write_text('{"show_glossary": true}', encoding="utf-8")
    glossary = work / "glossary.md"
    glossary.write_text("## 术语对应表\n\ntoken → 词元", encoding="utf-8")
    output = tmp_path / "output"
    first = build.build(output, content, metadata=FIXTURE_METADATA)
    page = (output / "index.html").read_text(encoding="utf-8")
    assert 'id="sec-glossary"' in page
    assert "token → 词元" in page
    assert page.index('id="sec-glossary"') < page.index('id="sec-01-body"')
    assert 'href="#术语对应表"' in page
    glossary.write_text("## 术语对应表\n\ntoken → token（词元）", encoding="utf-8")
    second = build.build(output, content, metadata=FIXTURE_METADATA)
    assert first["content_hash"] != second["content_hash"]


@pytest.mark.parametrize("value", [False, "true", None, 1])
def test_glossary_is_opt_in_and_requires_boolean(tmp_path: Path, value: object) -> None:
    work = tmp_path / "work"
    content = work / "content"
    content.mkdir(parents=True)
    (content / "01-body.md").write_text("## 正文", encoding="utf-8")
    (work / "reader.json").write_text(json.dumps({"show_glossary": value}), encoding="utf-8")
    if value is False:
        build.build(tmp_path / "output", content, metadata=FIXTURE_METADATA)
        page = (tmp_path / "output/index.html").read_text(encoding="utf-8")
        assert 'id="sec-glossary"' not in page
    else:
        with pytest.raises(ValueError, match="show_glossary must be a boolean"):
            build.build(tmp_path / "output", content, metadata=FIXTURE_METADATA)


def test_glossary_missing_or_duplicate_fails(tmp_path: Path) -> None:
    work = tmp_path / "work"
    content = work / "content"
    content.mkdir(parents=True)
    (work / "reader.json").write_text('{"show_glossary": true}', encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        build.build(tmp_path / "output", content, metadata=FIXTURE_METADATA)
    (content / "glossary.md").write_text("## 重复术语", encoding="utf-8")
    with pytest.raises(ValueError, match="already in use"):
        build.build(tmp_path / "output", content, metadata=FIXTURE_METADATA)


def test_nested_reader_uses_one_explicit_library_root(tmp_path: Path) -> None:
    library = tmp_path / "library"
    dist = library / "review/work/reference/source-paper"
    manifest = build.build(
        dist,
        FIXTURE_CONTENT,
        metadata=FIXTURE_METADATA,
        library_root=library,
        figures_dir=FIXTURE_FIGURES,
    )
    page = (dist / "index.html").read_text(encoding="utf-8")
    assert 'href="../../../../assets/styles/reader.css"' in page
    assert 'src="../../../../assets/scripts/reader.js"' in page
    assert manifest["shared_asset_root"] == "../../../../assets"
    assert (library / "assets/scripts/reader.js").is_file()
    assert (dist / "assets/figures/figure-03.png").is_file()
    assert not (dist.parent / "assets").exists()
    assert not (dist / "assets/styles").exists()
    assert not (dist / "assets/scripts").exists()


def test_reader_rejects_output_outside_library_root(tmp_path: Path) -> None:
    dist = tmp_path / "outside"
    with pytest.raises(ValueError, match="inside library_root"):
        build.build(
            dist,
            FIXTURE_CONTENT,
            metadata=FIXTURE_METADATA,
            library_root=tmp_path / "library",
        )
    assert not dist.exists()


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


def test_fenced_code_blocks_become_pre() -> None:
    """A ``` fence must render as a block, not as an inline code run."""
    md = build.make_markdown()
    html = md.convert("正文：\n\n```c++\nint a = 1;\n```\n")
    assert "<pre>" in html
    assert 'class="language-c++"' in html
    assert "```" not in html


def test_code_fence_after_html_comment_still_renders() -> None:
    """A caption comment placed directly above a fence must not swallow the block."""
    md = build.make_markdown()
    html = md.convert(
        "正文：\n\n<!-- ptx_functions.cuh -->\n```assembly\nLDSM.16.M88.4 R32, [R176] ;\n```\n"
    )
    assert "<pre>" in html
    assert 'class="language-assembly"' in html


def test_combine_toc_merges_sections(tmp_path: Path) -> None:
    (tmp_path / "01-a.md").write_text("## 甲\n\ntext\n", encoding="utf-8")
    (tmp_path / "02-b.md").write_text("## 乙\n\n## 丙\n", encoding="utf-8")
    sections = build.read_sections(tmp_path)
    toc = build.combine_toc(sections)
    assert toc.count("<li>") == 3


def test_a_body_table_of_contents_is_dropped(tmp_path: Path) -> None:
    """A section that keeps the source's own contents list must not duplicate the page TOC."""
    (tmp_path / "01-a.md").write_text(
        "## 系列简介\n\n正文。\n\n"
        "## 目录\n\n"
        "- ### [第 1 部分](https://example.invalid/Part-1)\n"
        "- ### [第 2 部分](https://example.invalid/Part-2)\n"
        "- ### 第 3 部分（尚未发布）\n\n"
        "---\n\n本文译自……\n",
        encoding="utf-8",
    )
    sections = build.read_sections(tmp_path)
    html = sections[0].html
    assert "目录" not in html
    assert "第 1 部分" not in html
    # The prose on either side of the dropped block survives.
    assert "正文。" in html
    assert "本文译自" in html
    assert [token["name"] for token in sections[0].tokens] == ["系列简介"]


def test_an_ordinary_heading_before_a_list_is_kept(tmp_path: Path) -> None:
    """Only a list of *headings* is a contents block; a plain list is ordinary prose."""
    (tmp_path / "01-a.md").write_text(
        "## Kernel 列表\n\n1. 基础实现\n2. Swizzling\n", encoding="utf-8"
    )
    sections = build.read_sections(tmp_path)
    assert "基础实现" in sections[0].html
    assert [token["name"] for token in sections[0].tokens] == ["Kernel 列表"]


def test_source_links_are_aimed_at_their_sections() -> None:
    """A source-site cross-reference lands on the section that now holds that part."""
    targets = {"https://example.invalid/Part-2": "#sec-02-part-2"}
    html = (
        '<p>在<a href="https://example.invalid/Part-2#a-heading">第 2 部分</a>中，'
        '我们见<a href="https://example.invalid/Part-2">此处</a>。</p>'
        '<p>代码见<a href="https://github.com/x/y">GitHub</a>。</p>'
    )
    rewritten = build.rewrite_source_links(html, targets)
    assert rewritten.count('href="#sec-02-part-2"') == 2
    # A deep link can only reach the top of its section: the page never recorded the heading.
    assert "#a-heading" not in rewritten
    # Anything that is not a page of this source keeps the URL it was written with.
    assert 'href="https://github.com/x/y"' in rewritten
    assert build.rewrite_source_links(html, {}) == html


def test_source_link_targets_of_a_pdf_paper_are_empty() -> None:
    """A PDF-sourced paper has no web identity, so the rewrite must leave it alone."""
    pdf_paper = paper.Paper(
        slug="sample",
        directory=REPO_ROOT / "papers" / "sample",
        title="t",
        subtitle="s",
        author="a",
        source_pdf=REPO_ROOT / "paper.pdf",
        sections=[paper.SectionRange("00-front", 1, 2)],
        expectations=paper.Expectations(),
    )
    assert build.source_link_targets(pdf_paper) == {}


def test_source_link_targets_follow_the_manifest() -> None:
    """Every web section contributes one absolute source URL to the rewrite map."""
    web_paper = paper.Paper(
        slug="sample",
        directory=REPO_ROOT / "papers" / "sample",
        title="t",
        subtitle="s",
        author="a",
        source_pdf=None,
        sections=[
            paper.SectionRange("00-front", None, None, "index"),
            paper.SectionRange("01-part-1", None, None, "Part-1"),
        ],
        expectations=paper.Expectations(),
        source_web=paper.WebSource(base="https://example.invalid/series/"),
    )
    assert build.source_link_targets(web_paper) == {
        "https://example.invalid/series/index": "#sec-00-front",
        "https://example.invalid/series/Part-1": "#sec-01-part-1",
    }


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

    # Shared code lives once at the library root; figures remain per paper.
    assert (dist.parent / "assets" / "styles" / "reader.css").exists()
    assert (dist.parent / "assets" / "scripts" / "reader.js").exists()
    assert 'href="../assets/styles/reader.css"' in page
    assert not (dist / "assets/styles/reader.css").exists()
    assert (dist / "assets" / "figures" / "figure-03.png").exists()
    assert not (dist / "assets" / "fonts").exists()

    # Figures stay real files referenced by relative path; the page embeds no base64 payload.
    assert 'src="assets/figures/figure-03.png"' in page
    assert "base64" not in page
    assert "data:image" not in page

    # The stylesheet asks the browser for fonts by name and embeds no font bytes.
    assert "@font-face" not in (dist.parent / "assets" / "styles" / "reader.css").read_text(
        encoding="utf-8"
    )
