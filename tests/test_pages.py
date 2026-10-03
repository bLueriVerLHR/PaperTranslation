"""Publication boundary, navigation and font-preparation regression tests."""

from pathlib import Path

import pytest

from tools import pages


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_public_files_never_include_sources(tmp_path: Path) -> None:
    for name in (
        "a/index.html",
        "a/assets/figure.svg",
        "a/papers/detail.html",
        "a/work/index.html",
        "a/work/assets/leak.png",
        "a/original.pdf",
        "a/manifest.json",
        "a/notes/source.md",
        "a/assets/private.json",
    ):
        write(tmp_path / name, "fixture")
    assert [p.relative_to(tmp_path).as_posix() for p in pages.public_files(tmp_path)] == [
        "a/assets/figure.svg",
        "a/index.html",
        "a/papers/detail.html",
    ]


def test_info_uses_visible_text_and_collects_code() -> None:
    info = pages.inspect_page(
        "<title>A &amp; B</title><style>ignore</style><pre><code>x</code>中文</pre><p>正文</p>"
    )
    assert info.title == "A & B"
    assert "ignore" not in info.text
    assert info.code == "x中文"


def test_home_lists_all_pages_and_escapes_titles() -> None:
    text = pages.render_home(
        [
            {"path": "a/index.html", "title": "<title>"},
            {"path": "a/papers/test.html", "title": '摘要 & "信息"'},
        ]
    )
    assert 'href="a/index.html"' in text
    assert 'href="a/papers/test.html"' in text
    assert "&lt;title&gt;" in text
    assert "2 个阅读页面" in text


def test_public_paths_hide_user_identity_but_keep_repository_and_commit() -> None:
    source = r"<code>C:\Users\Alice\Documents\redis</code><p>commit abc123</p>"
    assert pages.redact_local_paths(source) == "<code>$LOCAL_REPOS/redis</code><p>commit abc123</p>"
    assert (
        pages.redact_local_paths("C:/Users/Bob/Documents/llvm-project")
        == "$LOCAL_REPOS/llvm-project"
    )


def test_relative_urls_support_project_pages_prefix() -> None:
    assert pages.relative_url(Path("project/index.html"), "index.html") == "../index.html"
    assert (
        pages.relative_url(Path("project/papers/a.html"), "assets/fonts/fonts.css")
        == "../../assets/fonts/fonts.css"
    )


def test_check_blocks_sources_and_bad_links(tmp_path: Path) -> None:
    write(
        tmp_path / "a.html",
        '<img src="work/leak.png"><a href="/absolute">x</a><a href="../../escape">y</a>',
    )
    write(tmp_path / "work/leak.png", "private")
    write(tmp_path / "secret.pdf", "private")
    errors = pages.check_site(tmp_path)
    assert any("private" in e for e in errors)
    assert any("unsupported file" in e for e in errors)
    assert any("non-portable" in e for e in errors)
    assert any("escaping" in e for e in errors)


def test_check_accepts_nested_local_and_external_citations(tmp_path: Path) -> None:
    write(
        tmp_path / "a/index.html",
        '<link href="../assets/a.css"><a href="https://example.com/paper">source</a>',
    )
    write(tmp_path / "assets/a.css", 'a { background: url("image.svg"); }')
    write(tmp_path / "assets/image.svg", "<svg></svg>")
    assert pages.check_site(tmp_path) == []


def test_export_rejects_existing_output(tmp_path: Path) -> None:
    write(tmp_path / "out/keep.txt", "keep")
    with pytest.raises(ValueError, match="empty"):
        pages.export(tmp_path / "dist", tmp_path / "out")
    assert (tmp_path / "out/keep.txt").read_text() == "keep"


def test_export_preserves_work_and_adds_navigation(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    write(
        dist / "a/index.html",
        '<html><head><title>中文</title></head><body><main class="page">content</main></body></html>',
    )
    write(
        dist / "a/papers/detail.html",
        "<html><head><title>详情</title></head><body><main>detail</main></body></html>",
    )
    write(dist / "a/work/keep.md", "canonical")
    out = tmp_path / "out"
    entries = pages.export(dist, out)
    assert len(entries) == 2
    assert (dist / "a/work/keep.md").read_text() == "canonical"
    assert not (out / "a/work").exists()
    assert 'href="../../index.html"' in (out / "a/papers/detail.html").read_text(encoding="utf-8")
    assert '<main class="page"><a class="site-home"' in (out / "a/index.html").read_text(
        encoding="utf-8"
    )


def test_export_rejects_workspace_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pages.tempfile, "gettempdir", lambda: str(tmp_path / "temp"))
    with pytest.raises(ValueError, match="system TEMP"):
        pages.export(tmp_path / "dist", tmp_path / "workspace")


def test_check_forbids_network_render_dependencies(tmp_path: Path) -> None:
    write(tmp_path / "index.html", '<script src="https://example.com/code.js"></script>')
    assert any("external render" in error for error in pages.check_site(tmp_path))


def test_check_blocks_external_css_and_loose_source_text(tmp_path: Path) -> None:
    write(tmp_path / "assets/a.css", '@import "https://example.invalid/theme.css";')
    write(tmp_path / "page-text.txt", "extracted source")
    errors = pages.check_site(tmp_path)
    assert any("external CSS" in error for error in errors)
    assert any("text/source" in error for error in errors)
