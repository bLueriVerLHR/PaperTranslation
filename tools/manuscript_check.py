"""Report typography and terminology candidates in local manuscript source files.

This is the mechanical half of the `docs/chinese-writing.md` review: it locates problems, it
does not judge them. Fenced code, inline code, MathML/HTML blocks and tags, link targets,
heading anchors, include directives, table boundaries and dates are masked before matching, so
the same rules apply to prose only. Excerpts and counts still need paragraph-level reading.

A line may opt out explicitly with ``<!-- manuscript-check: ignore -->`` or
``<!-- manuscript-check: ignore rule-a rule-b -->``; the comment itself is masked.

Blocking findings are unambiguous rule violations and gate ``--strict``. Advisory findings
(number grouping, range connectors, term case without a listed spelling, acronyms missing from
``work/glossary.md``, in-paragraph Latin/Chinese term mixing, list-style wording, literal inline
code inside a raw HTML block) depend on project convention or on reading the paragraph, so they
are reported without gating.

Usage::

    python tools/manuscript_check.py
    python tools/manuscript_check.py --paper my-review --examples 3
    python tools/manuscript_check.py --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `python tools/manuscript_check.py` to import the package
    sys.path.insert(0, str(ROOT))

CJK = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
CJK_RE = re.compile(f"[{CJK}]")
DEFAULT_DIST = ROOT / "dist"

#: Maintenance material, not canonical manuscript prose; kept out of the prose rules.
MAINTENANCE_FILES = frozenset(
    {"README.md", "source-map.md", "coverage-map.md", "reading-list.md", "download-needed.md"}
)

MASK_CODE = "\x01"
MASK_MATH = "\x02"
MASK_OTHER = "\x03"

IGNORE_DIRECTIVE = re.compile(r"<!--\s*manuscript-check:\s*ignore\s*([^>]*?)-->")

#: Spellings the writing standard names explicitly; other entries only back consistency checks.
DOC_TERMS = frozenset(
    {
        "MySQL",
        "InnoDB",
        "MyISAM",
        "Redis",
        "PostgreSQL",
        "SQLite",
        "GitHub",
        "Linux",
        "Windows",
        "TCP",
        "UDP",
        "HTTP",
        "TLS",
        "MVCC",
        "GTID",
    }
)

CANONICAL_TERMS: dict[str, tuple[str, ...]] = {
    "GitHub": ("Github", "GITHUB", "gitHub"),
    "GitLab": ("Gitlab", "GITLAB"),
    "Linux": ("LINUX", "linux"),
    "Windows": ("WINDOWS", "windows"),
    "MySQL": ("Mysql", "MYSQL"),
    "PostgreSQL": ("Postgres", "POSTGRESQL", "PostgreSql"),
    "SQLite": ("Sqlite", "SQLITE", "sqlite"),
    "Redis": ("REDIS", "redis"),
    "InnoDB": ("Innodb", "INNODB"),
    "MyISAM": ("Myisam", "MYISAM"),
    "Python": ("python", "PYTHON"),
    "JavaScript": ("Javascript", "JAVASCRIPT"),
    "JSON": ("Json", "json"),
    "YAML": ("Yaml", "yaml"),
    "HTML": ("Html", "html"),
    "CSS": ("Css", "css"),
    "XML": ("Xml", "xml"),
    "HTTP": ("Http", "http"),
    "HTTPS": ("Https", "https"),
    "TCP": ("Tcp", "tcp"),
    "UDP": ("Udp", "udp"),
    "TLS": ("Tls", "tls"),
    "SSH": ("Ssh", "ssh"),
    "DNS": ("Dns", "dns"),
    "API": ("Api", "api"),
    "SDK": ("Sdk", "sdk"),
    "CLI": ("Cli", "cli"),
    "URL": ("Url", "url"),
    "LLVM": ("Llvm", "llvm"),
    "TVM": ("Tvm", "tvm"),
    "Triton": ("TRITON", "triton"),
    "PyTorch": ("Pytorch", "PYTORCH", "pytorch"),
    "TensorFlow": ("Tensorflow", "TENSORFLOW", "tensorflow"),
    "NumPy": ("Numpy", "NUMPY", "numpy"),
    "CUDA": ("Cuda", "cuda"),
    "MPI": ("Mpi", "mpi"),
    "NCCL": ("Nccl", "nccl"),
    "RDMA": ("Rdma", "rdma"),
    "GPU": ("Gpu", "gpu"),
    "CPU": ("Cpu", "cpu"),
    "NPU": ("Npu", "npu"),
    "Markdown": ("MarkDown", "markdown"),
    "MathML": ("Mathml", "mathml"),
    "SVG": ("Svg", "svg"),
    "gRPC": ("GRPC", "Grpc", "grpc"),
    "Protobuf": ("ProtoBuf", "protobuf"),
    "Kafka": ("KAFKA", "kafka"),
    "ZooKeeper": ("Zookeeper", "zookeeper"),
    "MongoDB": ("Mongodb", "mongodb"),
    "NGINX": ("Nginx",),
    "Rust": ("RUST", "rust"),
    "MVCC": ("Mvcc", "mvcc"),
    "GTID": ("Gtid", "gtid"),
    "SIMD": ("Simd",),
    "SPMD": ("Spmd", "spmd"),
}

#: Acronyms that need no glossary entry because they are ordinary units or universal labels.
ACRONYM_WHITELIST = frozenset(
    {
        "PDF",
        "PNG",
        "JPG",
        "JPEG",
        "GIF",
        "TIFF",
        "ID",
        "OK",
        "IO",
        "OS",
        "RAM",
        "ROM",
        "USB",
        "SSD",
        "HDD",
        "TXT",
        "CSV",
        "ASCII",
        "UTF",
        "MS",
        "PC",
        "CI",
        "PR",
    }
)

META_CHATTER = (
    "本次任务",
    "本次交付",
    "按照要求",
    "根据要求",
    "用户要求",
    "交付清单",
    "TODO",
    "FIXME",
    "写作要求",
    "任务说明",
    "题面",
    "审校记录",
    "改稿",
    "精修记录",
    "以下回答",
    "待补充",
    "待核对",
    "尚未核对",
)

CHECKLIST_STYLE = (
    r"注意：",
    r"需注意",
    r"请注意",
    r"请确保",
    r"(?<![要得])不要",
    r"应避免",
    r"建议使用",
    r"建议先",
    r"务必",
    r"切记",
    r"切忌",
    r"尽量避免",
    r"应当注意",
)

#: Latin form and the Chinese term the project glossary maps it to.
TERM_PAIRS = (
    ("token", "词元"),
    ("embedding", "嵌入"),
    ("attention", "注意力"),
    ("inference", "推理"),
    ("pretraining", "预训练"),
    ("pre-training", "预训练"),
    ("fine-tuning", "微调"),
    ("throughput", "吞吐"),
    ("latency", "时延"),
    ("quantization", "量化"),
    ("pruning", "剪枝"),
    ("distillation", "蒸馏"),
    ("prompt", "提示词"),
    ("checkpoint", "检查点"),
    ("router", "路由"),
)

UNIT = (
    "MiB|GiB|KiB|TiB|PiB|EiB|kB|KB|MB|GB|TB|PB|EB|"
    "GHz|MHz|kHz|Hz|ms|us|ns|fps|IOPS|TFLOPS|GFLOPS|FLOPS|"
    "Gbps|Mbps|kbps|bps|kbit|Mbit|Gbit|KiB/s|MiB/s|GiB/s|KB/s|MB/s|GB/s|"
    "kWh|mA|kV|kW|MW|GW|V|A|W|bit|byte"
)

FULLWIDTH_PUNCT = "，。、；：！？（）【】《》〈〉“”‘’…～"

#: ``(rule, pattern, blocking)``; blocking findings are unambiguous rule violations.
RULES: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("digit-cjk-space", re.compile(f"(?<![0-9A-Za-z.])[0-9]+(?=[{CJK}])"), True),
    ("cjk-digit-space", re.compile(f"[{CJK}](?=[0-9])"), True),
    ("latin-cjk-space", re.compile(f"[A-Za-z](?=[{CJK}])|[{CJK}](?=[A-Za-z])"), True),
    (
        "fullwidth-punct-space",
        re.compile(f"[ \\t](?=[{FULLWIDTH_PUNCT}])(?![|])|(?<=[{FULLWIDTH_PUNCT}])[ \\t](?![|])"),
        True,
    ),
    (
        "halfwidth-punct",
        re.compile(f"[{CJK}][,;:?!]|[{CJK}]\\.|[;,?!][{CJK}]|(?<=[{CJK}]),"),
        True,
    ),
    (
        "halfwidth-paren",
        re.compile(f"[(][^)\\n]*[{CJK}][^)\\n]*[)]|[{CJK}][(]|[)][{CJK}]"),
        True,
    ),
    ("straight-quote", re.compile(f"[{CJK}][\"']|[\"'][{CJK}]"), True),
    ("fullwidth-digit", re.compile("[０-９]"), True),
    ("duplicate-punct", re.compile("([！？。，、；：])\\1+|[！？!?]{2,}|…{3,}"), True),
    ("unit-no-space", re.compile(rf"(?<![0-9A-Za-z_.\-])(\d+(?:\.\d+)?)({UNIT})\b"), True),
    ("percent-space", re.compile(r"\d[ \t]+%|\d[ \t]+°"), True),
    ("inline-code-space", re.compile(f"[{CJK}]{MASK_CODE}|{MASK_CODE}[{CJK}]"), True),
    ("ideographic-space", re.compile("\u3000"), True),
    ("fullwidth-latin", re.compile("[Ａ-Ｚａ-ｚ]"), True),
    ("tilde-range", re.compile(r"(?<=[0-9\u4e00-\u9fff])~(?=[0-9])"), True),
    (
        "big-number",
        re.compile(rf"(?<![0-9A-Za-z_.\-{CJK}])(\d{{5,}})(?![\w.,])"),
        False,
    ),
    (
        "ascii-range",
        re.compile(r"(?<![0-9A-Za-z_.\-])(\d+(?:\.\d+)?)[ \t]*[-~][ \t]*(\d+(?:\.\d+)?)(?![\w])"),
        False,
    ),
    ("double-space", re.compile(r"(?<=\S)[ \t]{2,}(?=[^\s])"), False),
)

INLINE_MASKS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"`+[^`]*?`+"), MASK_CODE),
    # Inline markup first: the generic tag rule below would leave element text visible.
    (re.compile(r"<math\b[^>]*>.*?</math>", re.DOTALL), MASK_MATH),
    (re.compile(r"<svg\b[^>]*>.*?</svg>", re.DOTALL), MASK_MATH),
    (re.compile(r"<pre\b[^>]*>.*?</pre>", re.DOTALL), MASK_CODE),
    (re.compile(r"<code\b[^>]*>.*?</code>", re.DOTALL), MASK_CODE),
    (re.compile(r"\$\$[^$]*\$\$|\$[^$\n]*\$"), MASK_MATH),
    (re.compile(r"\\\(.*?\\\)|\\\[.*?\\\]"), MASK_MATH),
    (re.compile(r"<!--.*?-->"), MASK_OTHER),
    (re.compile(r"<[^>\n]{1,400}>"), MASK_OTHER),
    (re.compile(r"\]\([^)\n]*\)"), MASK_OTHER),
    (re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$"), MASK_OTHER),
    (re.compile(r"^\s*\{\{include:[^}\n]*\}\}\s*$"), MASK_OTHER),
    (re.compile(r"(?:https?|ftp)://\S+"), MASK_OTHER),
    (re.compile(r"&[a-zA-Z#0-9]{2,8};"), MASK_OTHER),
    (re.compile(r"\[\^[^\]]+\]"), MASK_OTHER),
    (re.compile(r"[ \t]*\{[.#][^}\n]*\}"), MASK_OTHER),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), MASK_OTHER),
)

TABLE_ROW = re.compile(r"[ \t]*\|[ \t]*")
BLOCK_OPENERS = ("<math", "<svg")
BLOCK_CLOSERS = {"math": "</math", "svg": "</svg"}
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
ALIGNMENT_ROW = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
INDENTED_CODE = re.compile(r"^\s{4,}\S")


@dataclass(frozen=True)
class Finding:
    """One candidate rule violation."""

    rule: str
    line: int
    text: str
    blocking: bool


@dataclass
class FileReport:
    """Findings and terminology signals for one source file."""

    path: Path
    prose_lines: int = 0
    findings: list[Finding] = field(default_factory=list)
    acronyms: Counter[str] = field(default_factory=Counter)
    mixed_terms: list[str] = field(default_factory=list)


@dataclass
class ProjectReport:
    """Aggregated findings for one registered project."""

    name: str
    files: int = 0
    prose_lines: int = 0
    counts: Counter[str] = field(default_factory=Counter)
    blocking: int = 0
    examples: dict[str, list[str]] = field(default_factory=dict)
    acronyms_missing: list[str] = field(default_factory=list)
    mixed_terms: list[str] = field(default_factory=list)
    skipped_files: int = 0

    @property
    def ok(self) -> bool:
        """True when the project has no blocking finding."""
        return self.blocking == 0


def mask_line(line: str) -> str:
    """Replace code, math, markup, URLs, anchors and table boundaries with sentinels.

    Sentinels keep the original length, so a masked index still maps to the same
    character in the raw line.
    """
    out = line
    rules = list(INLINE_MASKS)
    if line.count("|") >= 2:
        rules.append((TABLE_ROW, MASK_OTHER))
    for pattern, mark in rules:
        out = pattern.sub(lambda match, k=mark: k * (match.end() - match.start()), out)
    return out


def prose_lines(text: str) -> list[tuple[int, str, str]]:
    """Return ``(line number, masked text, raw text)`` for prose lines only."""
    rows: list[tuple[int, str, str]] = []
    lines = text.splitlines()
    index = 0
    if lines and lines[0].strip() == "---":
        index = 1
        while index < len(lines) and lines[index].strip() != "---":
            index += 1
        index += 1
    fence: str | None = None
    closing: str | None = None
    while index < len(lines):
        raw = lines[index]
        number = index + 1
        stripped = raw.strip()
        marker = FENCE.match(raw)
        if fence:
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                fence = None
            index += 1
            continue
        if marker:
            fence = marker.group(1)
            index += 1
            continue
        if closing:
            if closing in stripped:
                closing = None
            index += 1
            continue
        opener = next(
            (tag for tag in BLOCK_OPENERS if stripped.lower().startswith(tag)),
            None,
        )
        if opener:
            tag = opener[1:]
            if BLOCK_CLOSERS[tag] in stripped.lower() or stripped.endswith("/>"):
                index += 1
                continue
            closing = BLOCK_CLOSERS[tag]
            index += 1
            continue
        if stripped.startswith(("$$", "\\[", "\\(")):
            if stripped.count("$$") < 2:
                closing = "$$"
            index += 1
            continue
        if ALIGNMENT_ROW.match(raw) and "|" in raw:
            index += 1
            continue
        if INDENTED_CODE.match(raw):
            index += 1
            continue
        rows.append((number, mask_line(raw), raw))
        index += 1
    return rows


def excerpt(raw: str, start: int, end: int, width: int = 24) -> str:
    """Return a readable window of ``raw`` around a match."""
    return raw[max(0, start - width) : min(len(raw), end + width)].strip()


def ignored_rules(raw: str) -> set[str] | None:
    """Return the rules a line ignores, an empty set for all rules, or None for no directive."""
    directive = IGNORE_DIRECTIVE.search(raw)
    if not directive:
        return None
    return set(directive.group(1).split())


def audit_file(path: Path) -> FileReport:
    """Apply every rule to one file and collect terminology signals."""
    report = FileReport(path=path)
    rows = prose_lines(path.read_text(encoding="utf-8"))
    report.prose_lines = len(rows)
    paragraphs: list[str] = []
    for number, masked, raw in rows:
        if not CJK_RE.search(masked):
            paragraphs.append("")
            continue
        paragraphs.append(masked)
        skip = ignored_rules(raw)
        if (
            raw.lstrip().startswith("<")
            and "`" in raw
            and (skip is None or not skip or "raw-html-code" in skip)
        ):
            # Inline code inside a raw HTML block is not processed by Markdown and would
            # render as literal backticks, so it needs an explicit ``<code>`` element.
            report.findings.append(Finding("raw-html-code", number, excerpt(raw, 0, 0, 40), False))
        for rule, pattern, blocking in RULES:
            if skip is not None and (not skip or rule in skip):
                continue
            for match in pattern.finditer(masked):
                report.findings.append(
                    Finding(rule, number, excerpt(raw, match.start(), match.end()), blocking)
                )
        for token in META_CHATTER:
            if token in masked:
                report.findings.append(Finding("meta-chatter", number, token, False))
        for pattern in CHECKLIST_STYLE:
            match = re.search(pattern, masked)
            if match:
                report.findings.append(
                    Finding(
                        "checklist-style",
                        number,
                        excerpt(masked, match.start(), match.end()),
                        False,
                    )
                )
        for match in re.finditer(r"\b[A-Z][A-Z0-9]{1,5}\b", masked):
            report.acronyms[match.group(0)] += 1
        for canonical, variants in CANONICAL_TERMS.items():
            for variant in variants:
                for match in re.finditer(re.escape(variant), masked):
                    before = masked[match.start() - 1 : match.start()]
                    after = masked[match.end() : match.end() + 1]
                    # ASCII-only adjacency test: CJK characters are alphanumeric to Python but
                    # are prose neighbours, not identifier characters.
                    touching = (before.isascii() and before.isalnum()) or (
                        after.isascii() and after.isalnum()
                    )
                    # Identifiers such as ``redis.call`` are API names, not prose spellings.
                    if touching or before == "." or after in ".(":
                        continue
                    label = f"{variant} → {canonical}" + (
                        " [doc]" if canonical in DOC_TERMS else ""
                    )
                    context = excerpt(raw, match.start(), match.end())
                    report.findings.append(
                        Finding(
                            "term-case", number, f"{context}  [{label}]", canonical in DOC_TERMS
                        )
                    )
    for paragraph in paragraphs:
        if not paragraph:
            continue
        for latin, chinese in TERM_PAIRS:
            if latin in paragraph and chinese in paragraph:
                report.mixed_terms.append(f"{latin} / {chinese}")
    return report


def project_files(project: Path) -> tuple[list[Path], list[Path]]:
    """Split a project's Markdown into manuscript prose files and maintenance files."""
    kept: list[Path] = []
    skipped: list[Path] = []
    work = project / "work"
    for path in sorted(work.rglob("*.md")):
        relative = path.relative_to(work)
        if relative.parts[0] == "reference" or path.name in MAINTENANCE_FILES:
            skipped.append(path)
        else:
            kept.append(path)
    return kept, skipped


def glossary_terms(project: Path) -> set[str]:
    """Return the Latin terms and acronyms listed in a project's glossary."""
    path = project / "work" / "glossary.md"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    found = set(re.findall(r"\b[A-Z][A-Z0-9]{1,6}\b", text))
    for token in re.findall(r"`([^`\n]+)`", text):
        found.update(re.findall(r"[A-Za-z][A-Za-z0-9+./-]*", token))
    return found


def audit_project(project: Path) -> ProjectReport:
    """Audit one project directory and aggregate its findings."""
    report = ProjectReport(name=project.name)
    kept, skipped = project_files(project)
    report.files = len(kept)
    report.skipped_files = len(skipped)
    acronyms: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for path in kept:
        file_report = audit_file(path)
        report.prose_lines += file_report.prose_lines
        acronyms.update(file_report.acronyms)
        relative = path.relative_to(project)
        for mixed in file_report.mixed_terms:
            report.mixed_terms.append(f"{relative}: {mixed}")
        for finding in file_report.findings:
            report.counts[finding.rule] += 1
            if finding.blocking:
                report.blocking += 1
            if len(examples[finding.rule]) < 10:
                examples[finding.rule].append(f"{relative}:{finding.line}  {finding.text[:180]}")
    listed = glossary_terms(project)
    report.examples = dict(examples)
    report.acronyms_missing = [
        f"{token}({count})"
        for token, count in sorted(acronyms.items(), key=lambda item: -item[1])
        if token not in listed and token not in ACRONYM_WHITELIST and count >= 2
    ]
    return report


def audit(dist: Path, paper: str | None = None) -> dict[str, ProjectReport]:
    """Audit every registered project under ``dist`` (or a single ``--paper`` slug)."""
    projects = sorted(p for p in dist.iterdir() if p.is_dir() and p.name != "assets")
    if paper:
        projects = [p for p in projects if p.name == paper]
    results: dict[str, ProjectReport] = {}
    for project in projects:
        kept, _ = project_files(project)
        if not kept:
            continue
        results[project.name] = audit_project(project)
    return results


def format_report(results: dict[str, ProjectReport], examples: int = 3) -> str:
    """Render a compact human-readable summary."""
    lines: list[str] = []
    total_blocking = 0
    for name, report in results.items():
        total_blocking += report.blocking
        verdict = "ok" if report.ok else f"BLOCKING {report.blocking}"
        counts = " ".join(f"{rule}={count}" for rule, count in report.counts.most_common())
        lines.append(f"{name}: files={report.files} prose_lines={report.prose_lines} {verdict}")
        if counts:
            lines.append(f"    counts: {counts}")
        for rule, items in report.examples.items():
            for item in items[:examples]:
                lines.append(f"    [{rule}] {item}")
        if report.acronyms_missing:
            lines.append(
                "    [glossary-gap] "
                + ", ".join(report.acronyms_missing[:10])
                + " (advisory: confirm what needs registration)"
            )
        for mixed in report.mixed_terms[:examples]:
            lines.append(f"    [term-mixing] {mixed}")
    lines.append(f"blocking findings: {total_blocking}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", default=str(DEFAULT_DIST), help="library root to scan")
    parser.add_argument("--paper", default=None, help="single registered project slug")
    parser.add_argument("--examples", type=int, default=3, help="examples printed per rule")
    parser.add_argument("--json", dest="json_path", default=None, help="write findings as JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when blocking findings remain",
    )
    args = parser.parse_args(argv)

    results = audit(Path(args.dist), args.paper)
    if not results:
        print("no manuscript source files found")
        return 0
    print(format_report(results, args.examples))
    if args.json_path:
        payload = {
            name: {
                "files": report.files,
                "prose_lines": report.prose_lines,
                "blocking": report.blocking,
                "counts": dict(report.counts.most_common()),
                "examples": report.examples,
                "acronyms_missing": report.acronyms_missing,
                "mixed_terms": report.mixed_terms,
            }
            for name, report in results.items()
        }
        Path(args.json_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.strict and any(not report.ok for report in results.values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
