"""Unit tests for the manuscript typography/terminology checker."""

from __future__ import annotations

import json
from pathlib import Path

from tools import manuscript_check as check


def _project(tmp_path: Path, name: str = "demo") -> Path:
    project = tmp_path / "dist" / name
    (project / "work" / "content").mkdir(parents=True)
    return project


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _audit_prose(tmp_path: Path, text: str, name: str = "prose.md") -> check.FileReport:
    """Audit one synthetic prose file that always lives under ``tmp_path``."""
    return check.audit_file(_write(tmp_path / name, text))


def _rules(report: check.FileReport) -> set[str]:
    return {finding.rule for finding in report.findings}


def test_mask_line_hides_code_math_markup_and_table_boundaries() -> None:
    masked = check.mask_line(
        "中文 `code` <math><mi>x</mi></math> 见 https://a.b/c 见 [文本](x.md)。"
    )
    for fragment in ("`code`", "<math>", "https://a.b/c", "](x.md)"):
        assert fragment not in masked
    assert masked.count("。") == 1
    assert check.mask_line("| 中文（说明） | 另一列 |").count("|") == 0


def test_prose_lines_skips_fenced_code_and_math_blocks() -> None:
    text = (
        "---\ntitle: 说明\n---\n"
        "# 标题\n\n"
        '```python\nprint("中文")  # 代码\n```\n\n'
        '<math display="block">\n  <mn>16384</mn>\n</math>\n\n'
        "正文一行。\n"
    )
    numbered = [(number, raw) for number, _, raw in check.prose_lines(text) if raw.strip()]
    assert numbered == [(4, "# 标题"), (14, "正文一行。")]


def test_straight_quotes_are_blocking_only_in_prose(tmp_path: Path) -> None:
    text = (
        '他说"没问题"。\n\n'
        '`printf("x")`\n\n'
        '<span id="fnref-1">正文</span>\n\n'
        '```\nval x = "中文"\n```\n'
    )
    report = _audit_prose(tmp_path, text)
    quotes = [finding for finding in report.findings if finding.rule == "straight-quote"]
    assert len(quotes) == 2
    assert all(finding.blocking for finding in quotes)


def test_spacing_and_unit_rules(tmp_path: Path) -> None:
    report = _audit_prose(tmp_path, "使用MySQL 读取10条；占用 512MiB 空间。\n")
    assert {"latin-cjk-space", "cjk-digit-space", "digit-cjk-space", "unit-no-space"} <= _rules(
        report
    )


def test_ignore_directive_suppresses_listed_and_all_rules(tmp_path: Path) -> None:
    listed = _audit_prose(
        tmp_path,
        "使用MySQL。<!-- manuscript-check: ignore latin-cjk-space -->\n",
        "listed.md",
    )
    everything = _audit_prose(tmp_path, "使用MySQL。<!-- manuscript-check: ignore -->\n", "all.md")
    assert "latin-cjk-space" not in _rules(listed)
    assert "latin-cjk-space" not in _rules(everything)


def test_fullwidth_punctuation_spacing_is_reported_but_table_rows_are_not(
    tmp_path: Path,
) -> None:
    prose = _audit_prose(tmp_path, "见 [1]（表 2） HCCL 的说明。\n", "prose.md")
    table = _audit_prose(tmp_path, "| 见 [1]（表 2） | HCCL 的说明 |\n", "table.md")
    assert "fullwidth-punct-space" in _rules(prose)
    assert "fullwidth-punct-space" not in _rules(table)


def test_big_number_and_range_are_advisory(tmp_path: Path) -> None:
    report = _audit_prose(tmp_path, "容量为 16384 个 slot，命中率 99-100%。\n")
    advisory = {finding.rule for finding in report.findings if not finding.blocking}
    assert {"big-number", "ascii-range"} <= advisory
    assert "straight-quote" not in _rules(report)


def test_term_case_marks_the_spelling_the_standard_names(tmp_path: Path) -> None:
    report = _audit_prose(tmp_path, "用 redis 命令读取，再让 Github 拉取。\n")
    term_case = [finding for finding in report.findings if finding.rule == "term-case"]
    labels = [finding.text for finding in term_case]
    assert any("redis → Redis [doc]" in label for label in labels)
    assert any("Github → GitHub [doc]" in label for label in labels)
    assert all(finding.line == 1 for finding in term_case)
    assert all(finding.blocking for finding in term_case)  # both are listed spellings


def test_term_case_ignores_api_identifiers(tmp_path: Path) -> None:
    report = _audit_prose(tmp_path, "脚本里 redis.call 与 redis.pcall 的差别见下。\n")
    assert [finding for finding in report.findings if finding.rule == "term-case"] == []


def test_backticks_inside_a_raw_html_block_are_advisory(tmp_path: Path) -> None:
    report = _audit_prose(
        tmp_path, '<p class="qa-question">Q1 · 怎样理解 `extern "C"` 与 volatile？</p>\n'
    )
    by_rule = {finding.rule: finding for finding in report.findings}
    assert "raw-html-code" in by_rule
    assert not by_rule["raw-html-code"].blocking


def test_backticks_in_markdown_prose_are_expected(tmp_path: Path) -> None:
    report = _audit_prose(tmp_path, "读取 `dict` 的 ht_table 字段。\n")
    assert "raw-html-code" not in _rules(report)


def test_project_audit_skips_maintenance_and_reference_files(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write(project / "work" / "content" / "01.md", "使用MySQL。\n")
    _write(project / "work" / "README.md", "使用MySQL。\n")
    _write(project / "work" / "reference" / "notes.md", "使用MySQL。\n")
    report = check.audit_project(project)
    assert report.files == 1
    assert report.skipped_files == 2
    assert report.counts["latin-cjk-space"] == 1


def test_acronyms_missing_from_glossary_are_advisory(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write(
        project / "work" / "content" / "01.md", "NCCL 与 ABC 都出现，NCCL 再来一次，ABC 也再来。\n"
    )
    _write(project / "work" / "glossary.md", "| NCCL | 集合通信库 |\n")
    report = check.audit_project(project)
    assert "NCCL(2)" not in report.acronyms_missing
    assert "ABC(2)" in report.acronyms_missing
    assert report.blocking == 0


def test_doc_term_mismatch_is_blocking(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write(project / "work" / "content" / "01.md", "用 redis 命令缓存。\n")
    report = check.audit_project(project)
    assert report.counts["term-case"] == 1
    assert report.blocking == 1
    assert not report.ok


def test_audit_and_strict_exit_codes(tmp_path: Path, capsys) -> None:
    dist = tmp_path / "dist"
    project = _project(tmp_path)
    _write(project / "work" / "content" / "01.md", '他说"没问题"。\n')
    assert check.main(["--dist", str(dist), "--strict"]) == 1
    assert "BLOCKING" in capsys.readouterr().out

    _write(project / "work" / "content" / "01.md", "他说“没问题”。\n")
    assert check.main(["--dist", str(dist), "--strict"]) == 0


def test_json_output_lists_counts(tmp_path: Path, capsys) -> None:
    dist = tmp_path / "dist"
    project = _project(tmp_path)
    _write(project / "work" / "content" / "01.md", '他说"没问题"。\n')
    target = tmp_path / "report.json"
    assert check.main(["--dist", str(dist), "--json", str(target), "--examples", "1"]) == 0
    capsys.readouterr()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["demo"]["blocking"] == 2
    assert payload["demo"]["counts"]["straight-quote"] == 2
