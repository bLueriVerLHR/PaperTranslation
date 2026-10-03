"""Unit and integration tests for the folder layout and the optional single-file export."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import build, pack, paper

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
        metadata={"title": "样例标题", "subtitle": "样例副标题", "author": "样例作者"},
    )


def _manifest(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "title": "示例论文",
        "subtitle": "副标题",
        "author": "某人",
        "source": {"pdf": None},
        "sections": [{"name": "00-front", "first": 1, "last": 2}],
        "expectations": {"headings": ["## 摘要"]},
    }
    data.update(overrides)
    return data


def _register(root: Path, slug: str, **overrides: object) -> None:
    directory = root / slug / "work"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / paper.MANIFEST_NAME).write_text(
        json.dumps(_manifest(**overrides), ensure_ascii=False), encoding="utf-8"
    )


def test_deliverable_is_a_folder_named_after_the_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """dist/<slug>/ holds the reader page; the English slug names the folder, not the title."""
    root = tmp_path / "dist"
    root.mkdir()
    monkeypatch.setattr(paper, "DIST_DIR", root)
    _register(root, "on-device-llm-survey")

    current = paper.load("on-device-llm-survey")
    assert current.output_dir == tmp_path / "dist" / "on-device-llm-survey"
    assert current.output_path == current.output_dir / "index.html"


def test_slug_must_be_an_english_folder_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "dist"
    root.mkdir()
    monkeypatch.setattr(paper, "DIST_DIR", root)
    for bad in ("Demo_Paper", "样例论文", "demo paper", "-demo", "demo-"):
        _register(root, bad)
        with pytest.raises(paper.PaperError, match="invalid paper slug"):
            paper.load(bad)


def test_build_writes_page_and_real_assets(tmp_path: Path) -> None:
    """The build output is a deliverable folder: index.html beside assets/, no data URIs."""
    dist = tmp_path / "dist" / "on-device-llm-survey"
    _build_fixture(dist)

    page = (dist / "index.html").read_text(encoding="utf-8")
    assert (dist / "assets" / "styles" / "reader.css").is_file()
    assert (dist / "assets" / "scripts" / "reader.js").is_file()
    assert (dist / "assets" / "figures" / "figure-03.png").is_file()
    # Figures stay relative file references; nothing is base64-encoded into the page.
    assert 'src="assets/figures/figure-03.png"' in page
    assert "base64" not in page
    assert "data:image" not in page


def test_build_preserves_work_and_rebuilds_without_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rebuild reads work/ and never removes retained metadata or references."""
    monkeypatch.setattr(paper, "DIST_DIR", tmp_path / "dist")
    _register(paper.DIST_DIR, "demo")
    current = paper.load("demo")
    shutil.copytree(FIXTURE_CONTENT, current.content_dir)
    shutil.copytree(FIXTURE_FIGURES, current.figures_dir)
    current.sections_dir.mkdir(parents=True)
    (current.sections_dir / "00-front.txt").write_text("reference", encoding="utf-8")
    before = {
        p.relative_to(current.directory): p.read_bytes()
        for p in current.directory.rglob("*")
        if p.is_file()
    }
    assert current.source_pdf is None
    assert build.main(["--paper", "demo"]) == 0
    assert build.main(["--paper", "demo"]) == 0
    after = {
        p.relative_to(current.directory): p.read_bytes()
        for p in current.directory.rglob("*")
        if p.is_file()
    }
    assert after == before
    assert current.output_path.is_file()


def test_build_removes_stale_figure_crops(tmp_path: Path) -> None:
    """A figure dropped from the sources must not survive in the shipped folder."""
    dist = tmp_path / "dist" / "demo"
    _build_fixture(dist)
    stale = dist / "assets" / "figures" / "figure-99.png"
    stale.write_bytes(b"\x89PNG\r\n\x1a\n")

    _build_fixture(dist)
    assert not stale.exists()
    assert (dist / "assets" / "figures" / "figure-03.png").is_file()


def test_build_manifest_lists_the_assets(tmp_path: Path) -> None:
    dist = tmp_path / "dist" / "demo"
    manifest = build.build(
        dist=dist,
        build_date="2026-01-01",
        content_dir=FIXTURE_CONTENT,
        template_path=REPO_ROOT / "src" / "templates" / "page.html",
        styles_dir=REPO_ROOT / "src" / "styles",
        scripts_dir=REPO_ROOT / "src" / "scripts",
        figures_dir=FIXTURE_FIGURES,
        metadata={"title": "样例标题", "subtitle": "副标题", "author": "作者"},
    )
    assert manifest["assets"]["figures"] == ["figure-03.png"]
    assert manifest["assets"]["styles"] == ["reader.css"]
    assert manifest["assets"]["scripts"] == ["reader.js"]


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


def test_inline_images_embeds_figures(tmp_path: Path) -> None:
    figures = tmp_path / "figures"
    figures.mkdir()
    (figures / "figure-01.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    html = '<img src="assets/figures/figure-01.png" alt="x"><img src="assets/figures/none.png">'
    result = pack.inline_images(html, figures, use_webp=False)
    assert result.count("data:image/png;base64,") == 1
    assert 'src="assets/figures/none.png"' in result


def test_export_folds_the_folder_into_one_file(tmp_path: Path) -> None:
    dist = tmp_path / "dist" / "demo"
    _build_fixture(dist)
    target = pack.pack(dist=dist, out=tmp_path / "export.html", use_webp=False)

    assert target == tmp_path / "export.html"
    html = target.read_text(encoding="utf-8")
    assert pack.external_resource_refs(html) == []
    assert "<style>" in html and "<script>" in html
    assert "data:image/png;base64," in html
    # Fonts stay out of the file: the CSS only names families for the browser to resolve.
    assert "@font-face" not in html
    assert "data:font/" not in html


def test_export_can_leave_figures_as_files(tmp_path: Path) -> None:
    """--figures-as-files inlines the stylesheet and script only, keeping images binary."""
    dist = tmp_path / "dist" / "demo"
    _build_fixture(dist)
    target = pack.pack(dist=dist, out=tmp_path / "export" / "index.html", figures_as_files=True)

    html = target.read_text(encoding="utf-8")
    assert "base64" not in html
    assert 'src="figures/figure-03.png"' in html
    assert (target.parent / "figures" / "figure-03.png").is_file()
    # The only remaining resource references are the intended sibling figure files.
    assert pack.external_resource_refs(html) == ["figures/figure-03.png"]


def test_pack_rejects_missing_build(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pack.pack(dist=tmp_path / "nope", out=tmp_path / "x.html")


def test_pack_main_requires_an_output_path(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        pack.main(["--paper", "demo", "--out"])


@pytest.mark.skipif(pack.ffmpeg_path() is None, reason="ffmpeg not installed")
def test_embedded_figure_is_never_larger_than_the_source(tmp_path: Path) -> None:
    """A tiny PNG is embedded as-is: the lossless WebP re-encode would be larger."""
    image = tmp_path / "small.png"
    image.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000a49444154789c6300010000050001"
        )
        + b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    plain = pack.figure_data_uri(image, use_webp=False)
    assert len(pack.figure_data_uri(image, use_webp=True)) <= len(plain)
