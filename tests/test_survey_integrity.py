"""Regression checks for expanded surveys and incomplete citation metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tools import survey


@pytest.mark.parametrize("count", [None, 0, 123])
def test_unknown_citations_are_not_zero(count: int | None, tmp_path: Path) -> None:
    """Unknown, verified zero and positive counts remain distinct in both views."""
    paper = survey.Paper(
        "example",
        tmp_path,
        {"cites": count, "cites_asof": "2026-09-19", "cites_source": "Recorded API result"},
    )
    for rendered in (survey.card_html(paper), survey.facts_html(paper)):
        if count is None:
            assert "未核实" in rendered
            assert "引用 0" not in rendered
            assert "2026-09-19" not in rendered
        else:
            assert f"引用 {count}" in rendered
            assert "2026-09-19" in rendered


def test_cross_section_repeats_hashes_and_stale_pages(tmp_path: Path) -> None:
    """Repeats stay navigable; abstract-only edits affect hashes; stale output is removed."""
    hub = tmp_path / "hub"
    hub.mkdir()
    (hub / "01-first.md").write_text("## First\n\n{{paper:example}}\n", encoding="utf-8")
    (hub / "02-second.md").write_text("## Second\n\n{{paper:example}}\n", encoding="utf-8")
    papers = tmp_path / "papers"
    directory = papers / "example"
    directory.mkdir(parents=True)
    meta = {
        "title_en": 'A title with "quotes" & <markup>',
        "cites": None,
        "notes": "A **qualified** result, not part of the abstract.",
    }
    (directory / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    abstract = directory / "abstract.md"
    abstract.write_text("First abstract.", encoding="utf-8")
    dist = tmp_path / "dist"
    kwargs = {"dist": dist, "hub_dir": hub, "papers_dir": papers, "info": {"title": "A & B"}}
    first = survey.build(**kwargs)
    page = (dist / "index.html").read_text(encoding="utf-8")
    ids = re.findall(r'\bid="([^"]+)"', page)
    assert len(ids) == len(set(ids))
    assert 'id="paper-example"' in page
    assert 'id="paper-example--2"' in page
    assert first["papers"] == ["example"]
    assert len(first["pages"]) == 2
    detail = (dist / "papers/example.html").read_text(encoding="utf-8")
    assert "&quot;quotes&quot; &amp; &lt;markup&gt;" in detail
    assert "<strong>qualified</strong>" in detail
    assert "data:" not in detail
    assert "data:" not in page
    assert "{{" not in detail

    (dist / "papers/stale.html").write_text("old generated page", encoding="utf-8")
    abstract.write_text("Revised abstract.", encoding="utf-8")
    second = survey.build(**kwargs)
    assert first["content_hash"] != second["content_hash"]
    assert not (dist / "papers/stale.html").exists()
    assert second["content_hash"] == survey.build(**kwargs)["content_hash"]
