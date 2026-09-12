"""Unit tests for the coverage checker."""

from __future__ import annotations

import json
from pathlib import Path

from tools import coverage


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
    content = tmp_path / "content"
    content.mkdir()
    (content / "01.md").write_text("## 摘要\n\n中文。\n", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"figures": [{"number": 1}]}), encoding="utf-8")

    result = coverage.check(content, report)
    assert not result.ok
    assert "## 1 引言" in result.missing_headings
    assert result.missing_figures == [1]
    assert result.missing_tables == [1, 2, 3, 4, 5]
    assert result.missing_equations == list(range(1, 18))


def test_check_passes_when_everything_is_present(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    body = "\n".join(coverage.EXPECTED_HEADINGS)
    body += "\n" + "\n".join(f"figure-{n:02d}.png" for n in coverage.EXPECTED_FIGURES)
    body += "\n" + "\n".join(f"表 {n} | 说明" for n in coverage.EXPECTED_TABLES)
    body += "\n" + "\n".join(
        f'<span class="eqno">({n})</span>' for n in coverage.EXPECTED_EQUATIONS
    )
    (content / "01.md").write_text(body, encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps({"figures": [{"number": n} for n in coverage.EXPECTED_FIGURES]}),
        encoding="utf-8",
    )

    result = coverage.check(content, report)
    assert result.ok, result
