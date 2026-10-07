"""Record append-only question/phase timestamps and explicit shared-time estimates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.knowledge import temp_path  # noqa: E402

PHASES = {"prepare", "edit", "validate", "done"}


def events(path: Path) -> list[dict]:
    """Read a small local log; its entries do not modify coverage or task status."""
    path = temp_path(path)
    if not path.exists():
        return []
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("log exceeds 2 MiB")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def mark(path: Path, label: str, note: str = "", *, timestamp: datetime | None = None) -> dict:
    """Close the preceding interval by appending the next actual timestamp."""
    if label not in PHASES and not re.fullmatch(r"qa-[a-z0-9-]+", label):
        raise ValueError("label must be a qa ID or prepare/edit/validate/done")
    old = events(path)
    if old and old[-1]["label"] == "done":
        raise ValueError("completed log is immutable; choose a new batch log")
    now = timestamp or datetime.now(UTC)
    if now.utcoffset() is None:
        raise ValueError("timestamp must carry a timezone")
    if old and now < datetime.fromisoformat(old[-1]["time"]):
        raise ValueError("clock moved backwards; do not fabricate a duration")
    entry = {"time": now.isoformat(), "label": label, "note": note}
    path = temp_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def summarize(rows: list[dict]) -> tuple[str, int]:
    """Separate measured intervals from equally apportioned shared editing/checking."""
    if len(rows) < 2 or rows[-1]["label"] != "done":
        raise ValueError("mark done after the batch checks; incomplete intervals are not reported")
    questions: dict[str, float] = {}
    phases = dict.fromkeys(PHASES, 0.0)
    for current, following in pairwise(rows):
        duration = (
            datetime.fromisoformat(following["time"]) - datetime.fromisoformat(current["time"])
        ).total_seconds()
        if duration < 0:
            raise ValueError("negative elapsed time")
        label = current["label"]
        if label.startswith("qa-"):
            questions[label] = questions.get(label, 0.0) + duration
        elif label in phases:
            phases[label] += duration
        else:
            raise ValueError("unknown phase")
    shared = (phases["edit"] + phases["validate"]) / len(questions) if questions else 0.0
    text = [
        "# Question review timing",
        "",
        "Measured review/proposal intervals plus estimated equal shares of common edits/checks.",
        "Preparation is separate; elapsed time is not proof of coverage or correctness.",
        "",
        "| Stable ID | Review/proposal seconds | Estimated total seconds |",
        "|---|---:|---:|",
    ]
    text.extend(
        f"| {key} | {seconds:.1f} | {seconds + shared:.1f} |" for key, seconds in questions.items()
    )
    text.extend(
        [
            "",
            f"Preparation: {phases['prepare']:.1f}s; common editing: {phases['edit']:.1f}s; "
            f"checking: {phases['validate']:.1f}s; allocated per question: {shared:.1f}s.",
        ]
    )
    return "\n".join(text) + "\n", len(questions)


def main(argv: list[str] | None = None) -> int:
    """Mark one transition or produce a maintained timing report, without one-off scripts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    stamp = commands.add_parser("mark")
    stamp.add_argument("label")
    stamp.add_argument("--note", default="")
    report = commands.add_parser("summary")
    report.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "mark":
            entry = mark(args.log, args.label, args.note)
            print(f"Marked {entry['label']}: {entry['time']}")
        else:
            text, count = summarize(events(args.log))
            if args.out:
                out = temp_path(args.out)
                if out == temp_path(args.log):
                    raise ValueError("report cannot replace the event log")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text, encoding="utf-8", newline="\n")
                print(f"Timing report saved: {count} questions; {out}")
            else:
                print(text, end="")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Timing operation failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
