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
        write(tmp_path / name, "{}" if name == "a/manifest.json" else "fixture")
    assert [p.relative_to(tmp_path).as_posix() for p in pages.public_files(tmp_path)] == [
        "a/assets/figure.svg",
        "a/index.html",
        "a/papers/detail.html",
    ]


def test_excluded_projects_never_export_but_local_sources_survive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / ".pagesignore"
    policy.write_text("# Local only\nhidden-project\n", encoding="utf-8")
    monkeypatch.setattr(pages, "excluded_projects", lambda: {"hidden-project"})
    write(tmp_path / "dist/hidden-project/index.html", "<title>Hidden</title>")
    write(tmp_path / "dist/hidden-project/work/keep.md", "canonical")
    write(tmp_path / "dist/visible/index.html", "<title>Visible</title>")
    out = tmp_path / "out"
    entries = pages.export(tmp_path / "dist", out)
    assert entries == [{"path": "visible/index.html", "title": "Visible"}]
    assert not (out / "hidden-project").exists()
    assert (tmp_path / "dist/hidden-project/work/keep.md").read_text() == "canonical"
    write(out / "hidden-project/index.html", "stale")
    assert any("publication-excluded" in error for error in pages.check_site(out))


def test_local_only_profile_never_exports_html_or_figures(tmp_path: Path) -> None:
    """A private translation remains excluded even during a full library export."""
    write(tmp_path / "dist/private-paper/work/reader.json", '{"public_export": false}')
    write(tmp_path / "dist/private-paper/index.html", "<title>Private translation</title>")
    write(tmp_path / "dist/private-paper/assets/figures/figure-01.svg", "<svg/>")
    write(tmp_path / "dist/approved/index.html", "<title>Approved</title>")
    out = tmp_path / "site"
    entries = pages.export(tmp_path / "dist", out)
    assert entries == [{"path": "approved/index.html", "title": "Approved"}]
    assert not (out / "private-paper").exists()
    assert (tmp_path / "dist/private-paper/index.html").exists()


@pytest.mark.parametrize("flag", [None, True, False])
def test_translation_is_local_regardless_of_export_flag(tmp_path: Path, flag: bool | None) -> None:
    import json

    dist = tmp_path / "dist"
    profile = {"kind": "translation"}
    if flag is not None:
        profile["public_export"] = flag
    write(dist / "paper/work/reader.json", json.dumps(profile))
    write(dist / "paper/work/content/00-front.md", "canonical translation")
    write(dist / "paper/index.html", "<title>Translation</title>")
    write(dist / "paper/assets/figures/figure.svg", "<svg/>")
    write(dist / "paper.html", "<title>Packed translation</title>")
    write(dist / "book/work/reader.json", '{"kind": "analysis"}')
    write(dist / "book/index.html", "<title>Authored book</title>")
    out = tmp_path / "out"
    assert pages.export(dist, out) == [{"path": "book/index.html", "title": "Authored book"}]
    assert not (out / "paper").exists() and not (out / "paper.html").exists()
    assert (dist / "paper/work/content/00-front.md").read_text() == "canonical translation"
    assert (dist / "paper/assets/figures/figure.svg").is_file()


def test_paper_without_reader_profile_stays_local(tmp_path: Path) -> None:
    write(tmp_path / "external/work/paper.json", "{}")
    write(tmp_path / "external/index.html", "<title>External paper</title>")
    write(tmp_path / "external.html", "<title>Packed paper</title>")
    assert pages.public_files(tmp_path) == []


def test_frozen_project_manifest_excludes_all_readers(tmp_path: Path) -> None:
    write(tmp_path / "old-survey/manifest.json", '{"public_export": false}')
    write(tmp_path / "old-survey/index.html", "<title>Experimental survey</title>")
    write(tmp_path / "old-survey/papers/a.html", "<title>Translated abstract</title>")
    write(tmp_path / "old-survey/assets/figure.svg", "<svg/>")
    write(tmp_path / "old-survey.html", "<title>Packed prototype</title>")
    assert pages.public_files(tmp_path) == []
    assert (tmp_path / "old-survey/papers/a.html").is_file()


@pytest.mark.parametrize("name", ["a/work/reader.json", "a/manifest.json"])
def test_duplicate_publication_fields_are_rejected(tmp_path: Path, name: str) -> None:
    write(tmp_path / name, '{"public_export": false, "public_export": true}')
    write(tmp_path / "a/index.html", "<title>Ambiguous</title>")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        pages.public_files(tmp_path)


@pytest.mark.parametrize("value", ['"false"', "0", "null"])
def test_publication_flag_requires_boolean(tmp_path: Path, value: str) -> None:
    write(tmp_path / "a/manifest.json", '{"public_export": ' + value + "}")
    with pytest.raises(ValueError, match="public_export must be a boolean"):
        pages.public_files(tmp_path)


def test_inventory_writes_git_stable_newlines(tmp_path: Path) -> None:
    import hashlib
    import json

    write(tmp_path / "index.html", "<p>原文\nsecond line</p>\n")
    write(tmp_path / "site-manifest.json", '{"pages": []}')
    pages.write_inventory(tmp_path)
    raw = (tmp_path / "site-manifest.json").read_bytes()
    assert b"\r\n" not in raw
    inventory = json.loads(raw)
    assert (
        inventory["files"]["index.html"]
        == hashlib.sha256((tmp_path / "index.html").read_bytes()).hexdigest()
    )


def test_exclusion_config_accepts_only_project_slugs(tmp_path: Path) -> None:
    config = tmp_path / ".pagesignore"
    config.write_text("# comment\n/one-project/ # restricted\n\ntwo-project\n", encoding="utf-8")
    assert pages.excluded_projects(config) == {"one-project", "two-project"}
    config.write_text("../outside", encoding="utf-8")
    with pytest.raises(ValueError, match="project slug"):
        pages.excluded_projects(config)


def test_citation_cards_contribute_glyphs() -> None:
    info = pages.inspect_page(
        '<a data-citations="[{&quot;text&quot;:&quot;Góes 中文&quot;}]">[1]</a>'
    )
    assert "Góes 中文" in info.text


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
    # One canonical link list is retained for no-JS use and moved into a modal by JS.
    assert '<details class="library-pages">' in text
    assert '<ul class="library-page-links">' in text
    assert text.count('href="a/papers/test.html"') == 1


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
