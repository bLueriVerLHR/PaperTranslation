"""Check that the translation covers every source element and leaves no English prose.

This is the automated half of the TASK-5 QA pass. It verifies, against the extraction
inventory and a fixed expectation table, that:

* every expected section heading is present in ``src/content/``;
* every extracted figure is referenced by a content file;
* every numbered display equation carries a matching ``(N)`` marker;
* every table caption is present;
* no paragraph or caption outside math/code blocks is still English prose.

Exit code is 0 when everything checks out and 1 otherwise, so the QA step can gate a
release.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "src" / "content"
REPORT_PATH = ROOT / ".local" / "source" / "report.json"

EXPECTED_HEADINGS = [
    "## 摘要",
    "## 1 引言",
    "## 2 架构",
    "## 3 通用基础设施",
    "## 4 预训练",
    "## 5 后训练",
    "## 6 结论、局限与未来方向",
    "## 附录 B 评估细节",
    "## 附录 C 推理强度控制中的指数 token 惩罚",
]
EXPECTED_FIGURES = list(range(1, 13))
EXPECTED_TABLES = list(range(1, 6))
EXPECTED_EQUATIONS = list(range(1, 18))

_MATH_OR_CODE_RE = re.compile(
    r"<math\b.*?</math>|<pre\b.*?</pre>|```.*?```|<table\b.*?</table>",
    re.DOTALL | re.IGNORECASE,
)
_ASCII_RUN_RE = re.compile(r"(?:[A-Za-z][A-Za-z'\u2010-\u2015-]*\s+){7,}[A-Za-z]")


@dataclass
class Report:
    """Coverage findings."""

    missing_headings: list[str] = field(default_factory=list)
    missing_figures: list[int] = field(default_factory=list)
    missing_tables: list[int] = field(default_factory=list)
    missing_equations: list[int] = field(default_factory=list)
    english_prose: list[tuple[str, int, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when nothing is missing and no English prose remains."""
        return not (
            self.missing_headings
            or self.missing_figures
            or self.missing_tables
            or self.missing_equations
            or self.english_prose
        )


def read_content(content_dir: Path = CONTENT_DIR) -> dict[str, str]:
    """Return ``{filename: text}`` for every content file."""
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(content_dir.glob("*.md"))}


def extracted_figures(report_path: Path = REPORT_PATH) -> list[int]:
    """Return the figure numbers the extractor found in the source PDF."""
    if not report_path.exists():
        return list(EXPECTED_FIGURES)
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return [int(fig["number"]) for fig in data.get("figures", [])]


def find_english_prose(text: str) -> list[tuple[int, str]]:
    """Return ``(line_number, line)`` for lines that still look like English prose."""
    stripped = _MATH_OR_CODE_RE.sub(" ", text)
    results: list[tuple[int, str]] = []
    for number, line in enumerate(stripped.splitlines(), start=1):
        candidate = line.strip()
        if not candidate or candidate.startswith(("#", "|", "-", "<", "[", "!")):
            continue
        if _ASCII_RUN_RE.search(candidate):
            results.append((number, candidate[:160]))
    return results


def check(content_dir: Path = CONTENT_DIR, report_path: Path = REPORT_PATH) -> Report:
    """Run every coverage check and return the aggregated report."""
    documents = read_content(content_dir)
    joined = "\n".join(documents.values())
    report = Report()

    for heading in EXPECTED_HEADINGS:
        if not any(heading in text for text in documents.values()):
            report.missing_headings.append(heading)

    for number in extracted_figures(report_path):
        if f"figure-{number:02d}.png" not in joined:
            report.missing_figures.append(number)

    for number in EXPECTED_TABLES:
        if f"表 {number} |" not in joined:
            report.missing_tables.append(number)

    for number in EXPECTED_EQUATIONS:
        if f'<span class="eqno">({number})</span>' not in joined:
            report.missing_equations.append(number)

    for name, text in documents.items():
        for line_number, line in find_english_prose(text):
            report.english_prose.append((name, line_number, line))

    return report


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-dir", type=Path, default=CONTENT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)

    result = check(args.content_dir, args.report)

    print(f"content files        : {len(list(args.content_dir.glob('*.md')))}")
    print(f"missing headings     : {len(result.missing_headings)} {result.missing_headings}")
    print(f"missing figures      : {len(result.missing_figures)} {result.missing_figures}")
    print(f"missing tables       : {len(result.missing_tables)} {result.missing_tables}")
    print(f"missing equations    : {len(result.missing_equations)} {result.missing_equations}")
    print(f"english prose lines  : {len(result.english_prose)}")
    for name, line_number, line in result.english_prose[:30]:
        print(f"  {name}:{line_number}: {line}")
    print("RESULT:", "ok" if result.ok else "FAILED")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
