"""Unit tests for font collection and subsetting helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import fonts


def test_collect_chars_skips_math_and_code(tmp_path: Path) -> None:
    (tmp_path / "01.md").write_text(
        "中文甲。\n\n"
        '<div class="equation"><math display="block"><mi>xyz</mi></math></div>\n\n'
        "```\ncode_only\n```\n\n"
        '<figure><img src="a.png"><figcaption>中文乙</figcaption></figure>\n',
        encoding="utf-8",
    )
    chars = fonts.collect_chars([tmp_path])
    assert "中" in chars
    assert "甲" in chars
    assert "乙" in chars
    assert "x" not in chars  # inside <math>
    assert "c" not in chars  # inside fenced code


def test_collect_chars_drops_newlines(tmp_path: Path) -> None:
    (tmp_path / "01.md").write_text("甲\r\n乙\n", encoding="utf-8")
    chars = fonts.collect_chars([tmp_path])
    assert "\n" not in chars and "\r" not in chars


def test_cjk_chars_filters_ascii() -> None:
    result = fonts.cjk_chars({"a", "Z", "1", "。", "中", "ℓ"})
    assert result == {"。", "中", "ℓ"}


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "src/assets/fonts").exists(),
    reason="subset font not built yet",
)
def test_coverage_reports_no_missing_chars() -> None:
    assert fonts.main(["coverage"]) == 0
