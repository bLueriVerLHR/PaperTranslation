"""Unit and integration tests for the single-file packer."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools import build, pack

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CONTENT = Path(__file__).resolve().parent / "fixtures" / "sample-content"
FIXTURE_FIGURES = Path(__file__).resolve().parent / "fixtures" / "assets" / "figures"


def _build_fixture(dist: Path) -> None:
    build.build(
        dist=dist,
        build_date="2026-01-01",
        content_dir=FIXTURE_CONTENT,
        template_path=REPO_ROOT / "src" / "templates" / "page.html",
        styles_dir=REPO_ROOT / "src" / "styles",
        scripts_dir=REPO_ROOT / "src" / "scripts",
        figures_dir=FIXTURE_FIGURES,
        fonts_dir=REPO_ROOT / "src" / "assets" / "fonts",
        metadata={"title": "样例标题", "subtitle": "样例副标题", "author": "样例作者"},
    )


def test_safe_filename_replaces_illegal_characters() -> None:
    assert pack.safe_filename('a<b>c:d"e/f\\g|h?i*j') == "a-b-c-d-e-f-g-h-i-j"


def test_safe_filename_keeps_cjk_and_strips_trailing_dot() -> None:
    assert pack.safe_filename("示例标题 2.1：把中文标题保留下来") == (
        "示例标题 2.1：把中文标题保留下来"
    )
    assert pack.safe_filename("标题... ") == "标题"


def test_safe_filename_collapses_and_falls_back() -> None:
    assert pack.safe_filename("a    b") == "a b"
    assert pack.safe_filename("???") == "paper"
    assert pack.safe_filename("   ") == "paper"


def test_inline_css_embeds_fonts_and_keeps_missing_ones(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / "a.woff2").write_bytes(b"wOF2data")
    css = (
        '@font-face { src: url("../fonts/a.woff2") format("woff2"); }\n'
        '@font-face { src: url("../fonts/missing.woff2") format("woff2"); }\n'
    )
    result = pack.inline_css(css, fonts)
    assert "data:font/woff2;base64,d09GMmRhdGE=" in result
    assert 'url("../fonts/missing.woff2")' in result


def test_inline_images_embeds_figures(tmp_path: Path) -> None:
    figures = tmp_path / "figures"
    figures.mkdir()
    (figures / "figure-01.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    html = '<img src="assets/figures/figure-01.png" alt="x"><img src="assets/figures/none.png">'
    result = pack.inline_images(html, figures, use_webp=False)
    assert result.count("data:image/png;base64,") == 1
    assert 'src="assets/figures/none.png"' in result


def test_external_resource_refs_ignores_prose_hyperlinks() -> None:
    html = (
        '<a href="https://huggingface.co/deepseek-ai/x">link</a>'
        '<img src="data:image/webp;base64,AAAA">'
        '<script src="data:,void"></script>'
        '<a href="#toc">jump</a>'
    )
    assert pack.external_resource_refs(html) == []
    assert pack.content_links(html) == ["https://huggingface.co/deepseek-ai/x"]


def test_external_resource_refs_flags_uninlined_assets() -> None:
    assert pack.external_resource_refs('<img src="assets/figures/a.png">') == [
        "assets/figures/a.png"
    ]
    assert pack.external_resource_refs('<link href="assets/styles/a.css">') == [
        "assets/styles/a.css"
    ]


def test_pack_produces_one_self_contained_file(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _build_fixture(dist)
    target = pack.pack(dist=dist, use_webp=False, title="测试标题")

    assert target.name == "测试标题.html"
    assert pack.external_resource_refs(target.read_text(encoding="utf-8")) == []
    html = target.read_text(encoding="utf-8")
    assert "assets/" not in html
    assert "<style>" in html and "<script>" in html
    assert "data:font/woff2;base64," in html
    assert "data:image/png;base64," in html
    assert not re.search(r'(?:src|href)="(?!#)(?!data:)', html)


def test_pack_rejects_missing_build(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pack.pack(dist=tmp_path / "nope")


def test_pack_writes_the_registered_output_name(tmp_path: Path) -> None:
    """The deliverable is named after the paper title, one file per paper."""
    from tools import paper

    current = paper.load("deepseek-v41-flash")
    assert current.output_name == "示例标题 2.1：把中文标题保留下来.html"
    assert current.output_path.parent.name == "dist"


@pytest.mark.skipif(pack.ffmpeg_path() is None, reason="ffmpeg not installed")
def test_lossless_webp_is_smaller_than_png(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _build_fixture(dist)
    png = pack.pack(dist=dist, out=tmp_path / "png.html", use_webp=False).stat().st_size
    webp = pack.pack(dist=dist, out=tmp_path / "webp.html", use_webp=True).stat().st_size
    assert webp < png
    assert "data:image/webp;base64," in (tmp_path / "webp.html").read_text(encoding="utf-8")
