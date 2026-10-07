"""Index local evidence in disposable SQLite; retrieval never proves reading or coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import read_source  # noqa: E402

# Byte identity alone cannot validate an extraction produced by an older parser.
PARSER_SIGNATURE = hashlib.sha256(
    Path(__file__).read_bytes() + Path(read_source.__file__).read_bytes()
).hexdigest()
DOCUMENTS = """
CREATE TABLE IF NOT EXISTS documents(
 id INTEGER PRIMARY KEY, key TEXT UNIQUE, label TEXT, sha TEXT, revision TEXT,
 representation TEXT, refs TEXT, signature TEXT DEFAULT '');
"""
BLOCKS = """
CREATE VIRTUAL TABLE IF NOT EXISTS blocks USING fts5(
 doc UNINDEXED, pos UNINDEXED, locator UNINDEXED, scope UNINDEXED, body);
"""


def temp_path(path: Path) -> Path:
    """Keep indexes outside canonical material and refuse indirect escapes."""
    if not path.is_absolute() or not path.resolve().is_relative_to(
        Path(tempfile.gettempdir()).resolve()
    ):
        raise ValueError("cache/log/report must be an absolute system TEMP path")
    return path.resolve()


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    """Migrate only disposable caches; refuse legacy/stale caches during a query."""
    path = temp_path(path)
    if readonly:
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.executescript(DOCUMENTS)
    columns = {r[1] for r in connection.execute("PRAGMA table_info(documents)")}
    block_columns = {r[1] for r in connection.execute("PRAGMA table_info(blocks)")}
    if readonly:
        if "signature" not in columns or "scope" not in block_columns:
            connection.close()
            raise ValueError("legacy index: rebuild with build before querying")
        stale = connection.execute(
            "SELECT 1 FROM documents WHERE substr(signature,1,64) != ? LIMIT 1", (PARSER_SIGNATURE,)
        ).fetchone()
        if stale:
            connection.close()
            raise ValueError("parser changed: rebuild the cache before querying")
    else:
        if "signature" not in columns:
            connection.execute("ALTER TABLE documents ADD COLUMN signature TEXT DEFAULT ''")
        if block_columns and "scope" not in block_columns:
            connection.execute("DROP TABLE blocks")
            connection.execute("UPDATE documents SET signature=''")
        connection.executescript(BLOCKS)
    connection.row_factory = sqlite3.Row
    return connection


def line_blocks(text: str, *, width: int = 60, first_line: int = 1) -> list[tuple[str, str]]:
    """Keep real source lines in overlapping windows, never fabricated symbol ranges."""
    if width <= 10 or first_line < 1:
        raise ValueError("width must exceed 10 and first_line must be positive")
    lines = text.splitlines(keepends=True)
    return [
        (
            f"L{first_line + start}-L{first_line + min(start + width, len(lines)) - 1}",
            "".join(lines[start : start + width]),
        )
        for start in range(0, len(lines), width - 10)
    ]


def chunks(text: str, *, html_view: bool, fragment: str = "") -> list[tuple[str, str]]:
    """Extract an explicit URL target; never widen an unsupported fragment to the file."""
    if html_view:
        blocks = read_source.content_blocks(
            text, element_id=unquote(fragment) if fragment else None
        )
        return [
            (f"block {i + 1}{' #' + b.anchor if b.anchor else ''}", b.text)
            for i, b in enumerate(blocks)
            if b.text.strip()
        ]
    if not fragment:
        return line_blocks(text)
    match = re.fullmatch(r"L([1-9]\d*)(?:-L?([1-9]\d*))?", fragment)
    if not match:
        raise ValueError("unsupported source-line fragment")
    first, last = int(match[1]), int(match[2] or match[1])
    lines = text.splitlines(keepends=True)
    if not 1 <= first <= last <= len(lines):
        raise ValueError("reference line range is outside its fixed source")
    return line_blocks("".join(lines[first - 1 : last]), first_line=first)


def put(
    connection: sqlite3.Connection,
    *,
    key: str,
    label: str,
    data: bytes,
    revision: str,
    representation: str,
    refs: list[str],
    html_view: bool = False,
    scopes: dict[str, str] | None = None,
) -> bool:
    """Invalidate on source bytes, parser implementation or declared URL-scope changes."""
    if len(data) > 16 * 1024 * 1024:
        raise ValueError("source exceeds the 16 MiB indexing limit")
    scopes = scopes or {}
    sha = hashlib.sha256(data).hexdigest()
    signature = (
        PARSER_SIGNATURE
        + ":"
        + hashlib.sha256(json.dumps(scopes, sort_keys=True).encode()).hexdigest()
    )
    old = connection.execute("SELECT sha,signature FROM documents WHERE key=?", (key,)).fetchone()
    if old and old["sha"] == sha and old["signature"] == signature:
        connection.execute(
            "UPDATE documents SET label=?,revision=?,representation=?,refs=? WHERE key=?",
            (label, revision, representation, json.dumps(sorted(set(refs))), key),
        )
        return False
    text = data.decode("utf-8-sig")
    views = {"": chunks(text, html_view=html_view)}
    for ref, fragment in scopes.items():
        # Missing/unsupported anchors deliberately have no exact-scope rows.
        try:
            views[ref] = chunks(text, html_view=html_view, fragment=fragment)
        except ValueError:
            continue
    connection.execute(
        "INSERT INTO documents(key,label,sha,revision,representation,refs,signature) VALUES(?,?,?,?,?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET label=excluded.label,sha=excluded.sha,revision=excluded.revision, "
        "representation=excluded.representation,refs=excluded.refs,signature=excluded.signature",
        (key, label, sha, revision, representation, json.dumps(sorted(set(refs))), signature),
    )
    doc = connection.execute("SELECT id FROM documents WHERE key=?", (key,)).fetchone()["id"]
    connection.execute("DELETE FROM blocks WHERE doc=?", (doc,))
    connection.executemany(
        "INSERT INTO blocks(doc,pos,locator,scope,body) VALUES(?,?,?,?,?)",
        [
            (doc, i + 1, locator, scope, body)
            for scope, view in views.items()
            for i, (locator, body) in enumerate(view)
        ],
    )
    return True


def archive_sources(
    connection: sqlite3.Connection, index: Path, references: dict | None = None
) -> int:
    """Use recorded snapshot identities and URL anchors, not inferred reading ranges."""
    data = json.loads(index.read_text(encoding="utf-8-sig"))
    references = references or {}
    changed = 0
    for snapshot in data["snapshots"]:
        if not snapshot.get("file"):
            continue
        original = index.parent / snapshot["file"]
        path = original.resolve()
        if not path.is_relative_to(index.parent.resolve()) or original.is_symlink():
            raise ValueError("snapshot path escapes its archive")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != snapshot["sha256"]:
            raise ValueError(f"snapshot hash mismatch: {snapshot['key']}")
        representation = (
            snapshot.get("representation") or snapshot.get("representation_kind") or "unspecified"
        )
        if not isinstance(representation, str):
            representation = json.dumps(representation, ensure_ascii=False)
        refs = [str(r) for r in snapshot.get("references", [])]
        urls = {
            urlsplit(snapshot.get(k, ""))._replace(fragment="").geturl()
            for k in ("url", "final_url")
        }
        scopes = {}
        for ref in refs:
            target = urlsplit(references.get(ref, {}).get("url", ""))
            if (
                target._replace(fragment="").geturl()
                and target._replace(fragment="").geturl() in urls
            ):
                scopes[ref] = target.fragment
        changed += put(
            connection,
            key=path.as_uri(),
            label=snapshot["key"],
            data=payload,
            revision=snapshot["sha256"],
            representation=representation,
            refs=refs,
            html_view=path.suffix.lower() in {".html", ".htm"},
            scopes=scopes,
        )
    return changed


def git(repo: Path, *args: str) -> bytes:
    """Inspect local committed objects only, with no shell or upstream execution."""
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],  # noqa: S607
        capture_output=True,
        check=False,
        timeout=60,
    )
    if result.returncode:
        raise ValueError("local Git object read failed")
    return result.stdout


def repo_sources(
    connection: sqlite3.Connection, repo: Path, files: list[str], revision: str, references: dict
) -> int:
    """Read named files at one commit; reference scopes come only from URL line anchors."""
    commit = git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    changed = 0
    for name in dict.fromkeys(files):
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or "\n" in name or "\r" in name:
            raise ValueError("source files must be relative repository paths")
        refs, scopes = [], {}
        for number, record in references.items():
            url = urlsplit(record.get("url", ""))
            if f"/blob/{commit}/{path.as_posix()}" == url.path[url.path.find("/blob/") :]:
                ref = str(number)
                refs.append(ref)
                if url.fragment:
                    scopes[ref] = url.fragment
        changed += put(
            connection,
            key=f"git:{repo.resolve()}:{commit}:{path.as_posix()}",
            label=f"{repo.name}/{path.as_posix()}",
            data=git(repo, "show", f"{commit}:{path.as_posix()}"),
            revision=commit,
            representation="committed-source",
            refs=refs,
            scopes=scopes,
        )
    return changed


def search(
    connection: sqlite3.Connection,
    query: str,
    *,
    source: str = "",
    ref: str = "",
    linked_ref: str = "",
    limit: int = 3,
) -> list[sqlite3.Row]:
    """Search declared URL targets, or explicitly discover whole linked files."""
    if not query.strip() or not 1 <= limit <= 20 or (ref and linked_ref):
        raise ValueError("nonempty query, limit 1..20 and at most one reference filter required")
    if (
        ref
        and not connection.execute("SELECT 1 FROM blocks WHERE scope=? LIMIT 1", (ref,)).fetchone()
    ):
        raise ValueError("no resolvable URL scope; use --linked-ref only to discover the source")
    where, order = "blocks MATCH ?", "bm25(blocks)"
    terms = " AND ".join('"' + t.replace('"', '""') + '"' for t in query.split())
    if re.search(r"[\u3400-\u9fff]", query):
        where, order, terms = "instr(body, ?) > 0", "documents.id, CAST(pos AS INTEGER)", query
    sql = (
        "SELECT documents.*,pos,locator,scope,body FROM blocks JOIN documents ON doc=documents.id "  # noqa: S608
        f"WHERE {where} AND instr(label, ?) > 0 AND scope=? "
        "AND (?='' OR EXISTS(SELECT 1 FROM json_each(refs) WHERE value=?)) "
        f"ORDER BY {order} LIMIT ?"
    )
    return connection.execute(sql, (terms, source, ref, linked_ref, linked_ref, limit)).fetchall()


def show(
    connection: sqlite3.Connection, doc: int, block: int, count: int, *, ref: str = ""
) -> list[sqlite3.Row]:
    """Recover only adjoining blocks in the selected source/scope."""
    if min(doc, block, count) < 1 or count > 20:
        raise ValueError("positive IDs/count required; count <= 20")
    return connection.execute(
        "SELECT documents.*,pos,locator,scope,body FROM blocks JOIN documents ON doc=documents.id "
        "WHERE doc=? AND scope=? AND CAST(pos AS INTEGER)>=? ORDER BY CAST(pos AS INTEGER) LIMIT ?",
        (doc, ref, block, count),
    ).fetchall()


def render(rows: list[sqlite3.Row], *, max_chars: int = 4000, within: int = 0) -> str:
    """Preserve identity/scope and require explicit continuation after truncation."""
    if max_chars < 200 or within < 0:
        raise ValueError("max-chars >= 200 and within >= 0 required")
    if not rows:
        return "No cached matches in selected scope; this does not establish source absence."
    parts = []
    for index, row in enumerate(rows):
        offset = within if not index else 0
        body = row["body"]
        if offset >= len(body) and offset:
            raise ValueError("within exceeds this block")
        ref = f" --ref {row['scope']}" if row["scope"] else ""
        target = f"show --doc {row['id']} --block {row['pos']}{ref}"
        title = (
            f"[{row['id']}:{row['pos']}{' ref ' + row['scope'] if row['scope'] else ''}] "
            f"{row['label']} {row['locator']} ({row['representation']}, identity {row['revision'][:12]})\n"
        )
        available = max_chars - sum(len(p) for p in parts) - len(title)
        if available <= 0:
            parts.append("CONTINUE: " + target)
            break
        excerpt = body[offset : offset + available]
        parts.append(title + excerpt)
        if offset + len(excerpt) < len(body):
            parts.append(f"INCOMPLETE: {target} --within {offset + len(excerpt)}")
            break
    parts.append(
        "Cached excerpts only; URL location is not proof of claim support or completed reading."
    )
    return "\n\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    """Build/query private caches without fetching, editing inputs or promoting coverage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--archive", type=Path)
    build.add_argument("--repo", type=Path)
    build.add_argument("--file", action="append", default=[])
    build.add_argument("--revision", default="HEAD")
    build.add_argument("--reader", type=Path)
    find = commands.add_parser("search")
    find.add_argument("query")
    find.add_argument("--source", default="")
    find.add_argument("--ref", default="")
    find.add_argument("--linked-ref", default="")
    find.add_argument("--limit", type=int, default=3)
    browse = commands.add_parser("show")
    browse.add_argument("--doc", type=int, required=True)
    browse.add_argument("--block", type=int, required=True)
    browse.add_argument("--ref", default="")
    browse.add_argument("--count", type=int, default=3)
    for child in (find, browse):
        child.add_argument("--max-chars", type=int, default=4000)
        child.add_argument("--within", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        with connect(args.db, readonly=args.command != "build") as connection:
            if args.command == "build":
                if not args.archive and not (args.repo and args.file):
                    raise ValueError("supply an archive or explicit repository/file selection")
                refs = (
                    json.loads(args.reader.read_text(encoding="utf-8"))["references"]
                    if args.reader
                    else {}
                )
                changed = archive_sources(connection, args.archive, refs) if args.archive else 0
                if args.repo:
                    if not args.file:
                        raise ValueError("repository indexing requires explicit --file selections")
                    changed += repo_sources(connection, args.repo, args.file, args.revision, refs)
                documents = connection.execute("SELECT count(*) FROM documents").fetchone()[0]
                print(
                    f"Index ready: {documents} sources; {changed} changed. Private cache, not coverage."
                )
            else:
                rows = (
                    search(
                        connection,
                        args.query,
                        source=args.source,
                        ref=args.ref,
                        linked_ref=args.linked_ref,
                        limit=args.limit,
                    )
                    if args.command == "search"
                    else show(connection, args.doc, args.block, args.count, ref=args.ref)
                )
                print(render(rows, max_chars=args.max_chars, within=args.within))
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        sqlite3.Error,
        subprocess.TimeoutExpired,
    ) as error:
        parser.exit(1, f"Index operation failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
