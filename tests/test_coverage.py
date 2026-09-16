"""Unit tests for the coverage checker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import coverage, paper

EXPECTATIONS = paper.Expectations(
    headings=["## 摘要", "## 1 引言"],
    figures=[1, 2],
    tables=[1],
    equations=[3],
)


def _content(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    content.mkdir()
    return content


def test_find_english_prose_flags_a_sentence() -> None:
    text = (
        "这是一段中文。\nThis is a long English sentence that should be flagged by the checker.\n"
    )
    hits = coverage.find_english_prose(text)
    assert len(hits) == 1
    assert hits[0][0] == 2


def test_find_english_prose_ignores_math_code_and_tables() -> None:
    text = (
        '<math display="block"><mtext>Argument requires the full text here now</mtext></math>\n'
        "<pre><code>Require: Weight and gradient and momentum and coefficient</code></pre>\n"
        "<table><tr><td>Benchmark name and metric and shots and score</td></tr></table>\n"
    )
    assert coverage.find_english_prose(text) == []


def test_find_english_prose_allows_short_name_runs() -> None:
    text = "在 Terminal-Bench 2.1 与 DeepSWE v1.1 上，模型表现相当。\n"
    assert coverage.find_english_prose(text) == []


def test_check_reports_missing_elements(tmp_path: Path) -> None:
    content = _content(tmp_path)
    (content / "01.md").write_text("## 摘要\n\n中文。\n", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"figures": [{"number": 1}]}), encoding="utf-8")

    result = coverage.check(content, EXPECTATIONS, report)
    assert not result.ok
    assert "## 1 引言" in result.missing_headings
    assert result.missing_figures == [1, 2]
    assert result.missing_tables == [1]
    assert result.missing_equations == [3]


def test_check_uses_expectations_when_there_is_no_report(tmp_path: Path) -> None:
    content = _content(tmp_path)
    (content / "01.md").write_text("## 摘要\n", encoding="utf-8")
    result = coverage.check(content, EXPECTATIONS, tmp_path / "absent.json")
    assert result.missing_figures == [1, 2]


def test_check_passes_when_everything_is_present(tmp_path: Path) -> None:
    content = _content(tmp_path)
    body = "\n".join(EXPECTATIONS.headings)
    body += "\n" + "\n".join(f"figure-{n:02d}.png" for n in EXPECTATIONS.figures)
    body += "\n" + "\n".join(f"表 {n} | 说明" for n in EXPECTATIONS.tables)
    body += "\n" + "\n".join(f'<span class="eqno">({n})</span>' for n in EXPECTATIONS.equations)
    (content / "01.md").write_text(body, encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps({"figures": [{"number": n} for n in EXPECTATIONS.figures]}),
        encoding="utf-8",
    )

    result = coverage.check(content, EXPECTATIONS, report)
    assert result.ok, result


def test_registered_papers_pass_coverage() -> None:
    """Every registered paper that has content must satisfy its own expectation table."""
    checked = 0
    for slug in paper.available():
        current = paper.load(slug)
        if not list(current.content_dir.glob("*.md")):
            continue  # registered but not translated yet
        result = coverage.check(current.content_dir, current.expectations, current.report_path)
        assert result.ok, (slug, result)
        checked += 1
    assert checked or not paper.available(), "a registered paper has content but none was checked"
    if not checked:
        pytest.skip("no translated paper is present: papers/ is local-only and git-ignored")
