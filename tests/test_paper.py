"""Unit tests for the paper manifest loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import paper


def _manifest(**overrides: object) -> dict[str, object]:
    """Return a minimal valid manifest, with overrides applied."""
    data: dict[str, object] = {
        "title": "示例论文",
        "subtitle": "副标题",
        "author": "某人",
        "source": {"pdf": ".local/source/demo/paper.pdf"},
        "sections": [{"name": "00-front", "first": 1, "last": 2}],
        "expectations": {"headings": ["## 摘要"], "figures": [1], "tables": [1], "equations": [1]},
    }
    data.update(overrides)
    return data


@pytest.fixture
def papers_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the loader at a temporary papers directory."""
    root = tmp_path / "papers"
    root.mkdir()
    monkeypatch.setattr(paper, "PAPERS_DIR", root)
    monkeypatch.setattr(paper, "LOCAL_SOURCE_DIR", tmp_path / ".local" / "source")
    monkeypatch.setattr(paper, "DIST_DIR", tmp_path / "dist")
    return root


def _write(root: Path, slug: str, data: dict[str, object]) -> Path:
    """Write a manifest under ``root`` and return its path."""
    directory = root / slug
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / paper.MANIFEST_NAME
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_reads_every_field(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest())
    loaded = paper.load("demo")

    assert loaded.slug == "demo"
    assert loaded.title == "示例论文"
    assert loaded.author == "某人"
    assert loaded.sections == [paper.SectionRange("00-front", 1, 2)]
    assert loaded.expectations.headings == ["## 摘要"]
    assert loaded.expectations.equations == [1]


def test_derived_paths_are_repo_relative(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest())
    loaded = paper.load("demo")

    assert loaded.content_dir == papers_root / "demo" / "content"
    assert loaded.glossary_path == papers_root / "demo" / "glossary.md"
    assert loaded.figures_dir == papers_root / "demo" / "assets" / "figures"
    assert loaded.source_dir.name == "demo"
    assert loaded.report_path.name == "report.json"
    assert loaded.dist_dir.parts[-2:] == ("build", "demo")
    assert loaded.output_name == "示例论文.html"


def test_load_rejects_unknown_slug(papers_root: Path) -> None:
    with pytest.raises(paper.PaperError, match="unknown paper"):
        paper.load("nope")


def test_load_rejects_missing_key(papers_root: Path) -> None:
    data = _manifest()
    del data["author"]
    _write(papers_root, "demo", data)
    with pytest.raises(paper.PaperError, match="missing 'author'"):
        paper.load("demo")


def test_load_rejects_bad_page_range(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest(sections=[{"name": "a", "first": 3, "last": 1}]))
    with pytest.raises(paper.PaperError, match="invalid page range"):
        paper.load("demo")


def test_load_rejects_empty_sections(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest(sections=[]))
    with pytest.raises(paper.PaperError, match="non-empty list"):
        paper.load("demo")


def test_load_rejects_non_integer_expectations(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest(expectations={"figures": ["one"]}))
    with pytest.raises(paper.PaperError, match=r"expectations\.figures"):
        paper.load("demo")


def test_expectations_tolerate_omitted_keys(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest(expectations={}))
    loaded = paper.load("demo")
    assert loaded.expectations == paper.Expectations()


def test_columns_default_to_one(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest())
    assert paper.load("demo").columns == 1


def test_columns_are_read_from_the_manifest(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest(columns=2))
    assert paper.load("demo").columns == 2


def test_columns_reject_nonsense(papers_root: Path) -> None:
    _write(papers_root, "demo", _manifest(columns=0))
    with pytest.raises(paper.PaperError, match="'columns' must be a positive integer"):
        paper.load("demo")


def test_available_lists_registered_slugs(papers_root: Path) -> None:
    _write(papers_root, "beta", _manifest())
    _write(papers_root, "alpha", _manifest())
    assert paper.available() == ["alpha", "beta"]


def test_resolve_requires_slug_when_several_exist(papers_root: Path) -> None:
    _write(papers_root, "alpha", _manifest())
    _write(papers_root, "beta", _manifest())
    with pytest.raises(paper.PaperError, match="pass --paper"):
        paper.resolve(None)


def test_resolve_uses_the_only_paper(papers_root: Path) -> None:
    _write(papers_root, "solo", _manifest())
    assert paper.resolve(None).slug == "solo"


def test_resolve_reports_when_nothing_is_registered(papers_root: Path) -> None:
    with pytest.raises(paper.PaperError, match="no papers registered"):
        paper.resolve(None)


def test_safe_filename_replaces_illegal_characters() -> None:
    assert paper.safe_filename('a<b>c:d"e/f\\g|h?i*j') == "a-b-c-d-e-f-g-h-i-j"


def test_safe_filename_keeps_cjk_and_strips_trailing_dot() -> None:
    assert paper.safe_filename("示例标题 2.1：把中文标题保留下来") == (
        "示例标题 2.1：把中文标题保留下来"
    )
    assert paper.safe_filename("标题... ") == "标题"
    assert paper.safe_filename("   ") == "paper"


def test_registered_papers_are_loadable() -> None:
    """Every local manifest must be valid; a published clone has none, so it skips."""
    real = paper.available()
    if not real:
        pytest.skip("no papers are registered: papers/ is local-only and git-ignored")
    for slug in real:
        loaded = paper.load(slug)
        assert loaded.title and loaded.subtitle and loaded.author
        assert loaded.sections
