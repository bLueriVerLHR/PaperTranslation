"""Shared runtime regression tests: no project copies or rebuild-dependent updates."""

from pathlib import Path

import pytest

from tools import assets, build, pack, pages


def write(path: Path, text: str) -> None:
    """Create a small isolated fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_refresh_migrates_only_resource_urls_and_is_idempotent(tmp_path: Path) -> None:
    """An asset update serves all pages without rebuilding/translating any of them."""
    page = '<link href="assets/styles/reader.css"><p>原文 <math><mi>x</mi></math></p><script src="assets/scripts/reader.js"></script>'
    write(tmp_path / "one/index.html", page)
    write(tmp_path / "two/papers/detail.html", page.replace('="assets/', '="../assets/'))
    write(tmp_path / "one/assets/styles/reader.css", "obsolete")
    write(tmp_path / "two/assets/scripts/reader.js", "obsolete")
    write(tmp_path / "one/work/index.html", page)
    write(tmp_path / "one/assets/figures/keep.svg", "<svg/>")
    write(tmp_path / "assets/fonts/fonts.css", "licensed fonts")
    result = assets.refresh(tmp_path)
    assert len(result["pages"]) == 2
    assert len(result["removed_legacy_copies"]) == 2
    assert (tmp_path / "one/index.html").read_text(encoding="utf-8") == page.replace(
        '="assets/', '="../assets/'
    )
    assert (
        'href="../../assets/styles/reader.css"' in (tmp_path / "two/papers/detail.html").read_text()
    )
    assert (tmp_path / "one/work/index.html").read_text(encoding="utf-8") == page
    assert (tmp_path / "assets/fonts/fonts.css").read_text() == "licensed fonts"
    assert (tmp_path / "one/assets/figures/keep.svg").read_text() == "<svg/>"
    assert list(tmp_path.rglob("reader.css")) == [tmp_path / "assets/styles/reader.css"]
    assert assets.refresh(tmp_path) == {
        "shared_assets": [],
        "pages": [],
        "removed_legacy_copies": [],
    }


def test_changed_runtime_needs_no_page_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deployment graph has one writer/asset, not one update operation per project."""
    source = tmp_path / "source.css"
    write(source, "first")
    monkeypatch.setattr(assets, "SOURCES", {"assets/styles/reader.css": source})
    for slug in ["one", "two"]:
        write(
            tmp_path / slug / "index.html", '<link href="../assets/styles/reader.css"><p>正文</p>'
        )
    assets.refresh(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.glob("*/index.html")}
    write(source, "fixed")
    result = assets.refresh(tmp_path)
    assert result == {
        "shared_assets": ["assets/styles/reader.css"],
        "pages": [],
        "removed_legacy_copies": [],
    }
    assert (tmp_path / "assets/styles/reader.css").read_text() == "fixed"
    assert all(p.read_bytes() == text for p, text in before.items())


def test_build_projects_share_one_runtime(tmp_path: Path) -> None:
    """Building paper two does not create another copy of paper one's runtime."""
    write(tmp_path / "work/content/00-front.md", "## 摘要\n\n正文")
    for slug in ["one", "two"]:
        build.build(tmp_path / slug, tmp_path / "work/content", metadata={"title": slug})
    assert list(tmp_path.rglob("reader.css")) == [tmp_path / "assets/styles/reader.css"]
    assert list(tmp_path.rglob("reader.js")) == [tmp_path / "assets/scripts/reader.js"]
    assert (tmp_path / "two/manifest.json").exists()


def test_export_legacy_and_new_pages_share_one_runtime(tmp_path: Path) -> None:
    """Export rewrites different page depths and never duplicates UI assets."""
    dist, out = tmp_path / "dist", tmp_path / "site"
    write(
        dist / "one/index.html",
        '<head><title>One</title><link href="assets/styles/reader.css"></head><main>正文</main>',
    )
    write(
        dist / "two/papers/x.html",
        '<head><title>Two</title><script src="../../assets/scripts/reader.js"></script></head><main>摘要</main>',
    )
    write(dist / "one/assets/styles/reader.css", "obsolete")
    write(dist / "two/assets/scripts/reader.js", "obsolete")
    pages.export(dist, out)
    write(out / "assets/fonts/fonts.css", "")
    write(out / "assets/fonts/NOTICE.txt", "OFL")
    assert pages.check_site(out) == []
    assert list(out.rglob("reader.css")) == [out / "assets/styles/reader.css"]
    assert list(out.rglob("reader.js")) == [out / "assets/scripts/reader.js"]
    assert 'href="../assets/styles/reader.css"' in (out / "one/index.html").read_text()


def test_validator_rejects_reintroduced_project_copies(tmp_path: Path) -> None:
    """CI enforces the shared dependency graph rather than relying on conventions."""
    write(tmp_path / "one/assets/styles/reader.css", "obsolete")
    write(tmp_path / "one/index.html", '<link href="assets/styles/reader.css">')
    errors = pages.check_site(tmp_path)
    assert any("duplicated shared asset" in error for error in errors)
    assert any("noncanonical shared asset URL" in error for error in errors)
    assert pages.check_site(tmp_path, allow_legacy_assets=True) == []
    assets.refresh(tmp_path)
    assert pages.check_site(tmp_path) == []


def test_pack_missing_shared_resources_fails_closed(tmp_path: Path) -> None:
    """figures-as-files must not silently retain unresolved ../assets URLs."""
    write(tmp_path / "one/index.html", '<link rel="stylesheet" href="../assets/styles/reader.css">')
    with pytest.raises(ValueError, match="assets were not inlined"):
        pack.pack(tmp_path / "one", tmp_path / "packed.html", figures_as_files=True)
