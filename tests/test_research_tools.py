"""Private evidence indexes and timing logs on disposable synthetic inputs."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools import knowledge, review_log


def test_archive_incremental_search_and_identity(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.html"
    payload = b"<main><p>try_emplace preserves existing keys.</p><pre>  code();\n</pre></main>"
    source.write_bytes(payload)
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps(
            {
                "snapshots": [
                    {
                        "key": "ref-0058",
                        "file": source.name,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "references": ["58"],
                        "representation": "raw-http",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    db = tmp_path / "cache.sqlite"
    with knowledge.connect(db) as connection:
        assert knowledge.archive_sources(connection, index) == 1
        assert knowledge.archive_sources(connection, index) == 0
        rows = knowledge.search(connection, "try_emplace", linked_ref="58")
        assert len(rows) == 1 and rows[0]["representation"] == "raw-http"
        assert "preserves existing" in knowledge.render(rows)
        assert not knowledge.search(connection, "try_emplace", linked_ref="59")
        assert knowledge.show(connection, rows[0]["id"], 1, 2)[1]["body"] == "  code();\n"
    assert source.read_bytes() == payload
    source.write_bytes(b"changed")
    with knowledge.connect(db) as connection, pytest.raises(ValueError, match="hash"):
        knowledge.archive_sources(connection, index)


def test_chinese_literal_and_fts_query_are_data(tmp_path: Path) -> None:
    with knowledge.connect(tmp_path / "cache.sqlite") as connection:
        knowledge.put(
            connection,
            key="a",
            label="document",
            data="引用计数不保护对象字段".encode(),
            revision="known",
            representation="passage-only",
            refs=[],
        )
        assert knowledge.search(connection, "引用计数")[0]["representation"] == "passage-only"
        assert not knowledge.search(connection, '" OR "anything')
        with pytest.raises(ValueError):
            knowledge.search(connection, "")


def test_fixed_git_bytes_not_working_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    commit = "1" * 40
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.tex").write_text("uncommitted misleading bytes", encoding="utf-8")

    def git(repo, *args):
        if args[0] == "rev-parse":
            return (commit + "\n").encode()
        assert args == ("show", commit + ":a.tex")
        return b"committed contract\n"

    monkeypatch.setattr(knowledge, "git", git)
    with knowledge.connect(tmp_path / "cache.sqlite") as connection:
        references = {"183": {"url": f"https://github.com/owner/repo/blob/{commit}/a.tex#L1"}}
        assert knowledge.repo_sources(connection, repo, ["a.tex"], "HEAD", references) == 1
        row = knowledge.search(connection, "committed", ref="183")[0]
        assert row["revision"] == commit and row["locator"] == "L1-L1"
        assert not knowledge.search(connection, "misleading")
        with pytest.raises(ValueError, match="relative"):
            knowledge.repo_sources(connection, repo, ["../escape"], "HEAD", references)


def test_cached_continuation_and_query_without_creation(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite"
    with knowledge.connect(path) as connection:
        knowledge.put(
            connection,
            key="long",
            label="source",
            data=b"x" * 1000,
            revision="known",
            representation="text-window",
            refs=[],
        )
        rows = knowledge.show(connection, 1, 1, 1)
        text = knowledge.render(rows, max_chars=200)
        assert "INCOMPLETE" in text and "--within" in text
        assert "x" * 400 in knowledge.render(rows, within=400, max_chars=2000)
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(sqlite3.Error):
        knowledge.connect(missing, readonly=True)
    assert not missing.exists()
    with pytest.raises(ValueError, match="TEMP"):
        knowledge.temp_path(Path("relative.sqlite"))


def test_line_window_ranges_are_real_and_overlapping() -> None:
    text = "".join(f"line {n}\n" for n in range(1, 66))
    blocks = knowledge.line_blocks(text)
    assert blocks[0][0] == "L1-L60" and blocks[1][0] == "L51-L65"
    assert blocks[0][1].splitlines()[-1] == "line 60"
    assert blocks[1][1].splitlines()[0] == "line 51"


def test_timing_intervals_and_shared_allocation(tmp_path: Path) -> None:
    log = tmp_path / "timing.jsonl"
    now = datetime(2026, 1, 1, tzinfo=UTC)
    for seconds, label in [
        (0, "prepare"),
        (10, "qa-one"),
        (30, "qa-two"),
        (60, "edit"),
        (80, "validate"),
        (90, "done"),
    ]:
        review_log.mark(log, label, timestamp=now + timedelta(seconds=seconds))
    text, count = review_log.summarize(review_log.events(log))
    assert count == 2
    assert "| qa-one | 20.0 | 35.0 |" in text
    assert "| qa-two | 30.0 | 45.0 |" in text
    assert "Preparation: 10.0s" in text
    assert "estimated" in text and "not proof" in text
    with pytest.raises(ValueError, match="immutable"):
        review_log.mark(log, "qa-three")


def test_timing_rejects_incomplete_and_backwards(tmp_path: Path) -> None:
    log = tmp_path / "timing.jsonl"
    now = datetime.now(UTC)
    review_log.mark(log, "qa-one", timestamp=now)
    with pytest.raises(ValueError, match="backwards"):
        review_log.mark(log, "edit", timestamp=now - timedelta(seconds=1))
    with pytest.raises(ValueError, match="incomplete"):
        review_log.summarize(review_log.events(log))
    with pytest.raises(ValueError, match="label"):
        review_log.mark(log, "arbitrary")


def test_exact_scope_does_not_match_other_parts(tmp_path: Path) -> None:
    with knowledge.connect(tmp_path / "cache.sqlite") as connection:
        knowledge.put(
            connection,
            key="a",
            label="containers.tex",
            data=b"unordered unrelated contract\nmap declared contract "
            + b"x" * 400
            + b"\nend of scope\n",
            revision="fixed",
            representation="committed-source",
            refs=["183"],
            scopes={"183": "L2-L3"},
        )
        assert not knowledge.search(connection, "unordered", ref="183")
        assert knowledge.search(connection, "unordered", linked_ref="183")
        rows = knowledge.search(connection, "declared", ref="183")
        assert rows[0]["locator"] == "L2-L3"
        assert "unordered" not in rows[0]["body"]
        assert knowledge.show(connection, rows[0]["id"], 1, 3, ref="183")[0]["scope"] == "183"
        assert "--ref 183" in knowledge.render(rows, max_chars=200, within=0)


def test_html_fragment_keeps_its_subtree_only(tmp_path: Path) -> None:
    with knowledge.connect(tmp_path / "cache.sqlite") as connection:
        knowledge.put(
            connection,
            key="page",
            label="doc",
            data=b'<main><p>outside</p><section id="target"><p id="child">inside evidence</p></section></main>',
            revision="snapshot",
            representation="raw-http",
            refs=["4", "5"],
            html_view=True,
            scopes={"4": "target", "5": "missing"},
        )
        assert not knowledge.search(connection, "outside", ref="4")
        assert knowledge.search(connection, "inside", ref="4")[0]["scope"] == "4"
        with pytest.raises(ValueError, match="scope"):
            knowledge.search(connection, "inside", ref="5")


def test_parser_change_invalidates_identical_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "cache.sqlite"
    args = {
        "key": "same",
        "label": "doc",
        "data": b"same bytes",
        "revision": "fixed",
        "representation": "text",
        "refs": [],
    }
    with knowledge.connect(db) as connection:
        assert knowledge.put(connection, **args)
    monkeypatch.setattr(knowledge, "PARSER_SIGNATURE", "f" * 64)
    with pytest.raises(ValueError, match="parser changed"):
        knowledge.connect(db, readonly=True)
    with knowledge.connect(db) as connection:
        assert knowledge.put(connection, **args)
        assert not knowledge.put(connection, **args)
    with knowledge.connect(db, readonly=True) as connection:
        assert knowledge.search(connection, "same")


def test_legacy_cache_requires_rebuild_and_migrates(tmp_path: Path) -> None:
    db = tmp_path / "legacy.sqlite"
    old = sqlite3.connect(db)
    old.executescript(
        "CREATE TABLE documents(id INTEGER PRIMARY KEY,key TEXT UNIQUE,label TEXT,sha TEXT,revision TEXT,representation TEXT,refs TEXT); CREATE VIRTUAL TABLE blocks USING fts5(doc UNINDEXED,pos UNINDEXED,locator UNINDEXED,body);"
    )
    old.close()
    with pytest.raises(ValueError, match="legacy"):
        knowledge.connect(db, readonly=True)
    with knowledge.connect(db) as connection:
        assert knowledge.put(
            connection,
            key="new",
            label="doc",
            data=b"rebuilt evidence",
            revision="known",
            representation="text",
            refs=[],
        )
    with knowledge.connect(db, readonly=True) as connection:
        assert knowledge.search(connection, "rebuilt")


def test_scope_change_invalidates_identical_source(tmp_path: Path) -> None:
    with knowledge.connect(tmp_path / "cache.sqlite") as connection:
        args = {
            "key": "same",
            "label": "source",
            "data": b"first evidence\nsecond evidence\n",
            "revision": "fixed",
            "representation": "committed-source",
            "refs": ["8"],
        }
        assert knowledge.put(connection, **args, scopes={"8": "L1"})
        assert knowledge.search(connection, "first", ref="8")
        assert knowledge.put(connection, **args, scopes={"8": "L2"})
        assert not knowledge.search(connection, "first", ref="8")
        assert knowledge.search(connection, "second", ref="8")


def test_cli_brief_summary_preserves_event_log(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    log, report = tmp_path / "events.jsonl", tmp_path / "report.md"
    assert review_log.main(["--log", str(log), "mark", "qa-one"]) == 0
    assert review_log.main(["--log", str(log), "mark", "done"]) == 0
    before = log.read_bytes()
    assert review_log.main(["--log", str(log), "summary", "--out", str(report)]) == 0
    assert "Timing report saved: 1 questions" in capsys.readouterr().out
    assert log.read_bytes() == before and report.is_file()
    with pytest.raises(SystemExit):
        review_log.main(["--log", str(log), "summary", "--out", str(log)])
