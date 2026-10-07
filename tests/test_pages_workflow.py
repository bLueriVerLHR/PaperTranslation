"""Selected reader updates and reusable publication checks on isolated fixtures."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools import pages, pages_verify


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def exported(source: Path, target: Path) -> None:
    pages.export(source, target)
    write(target / "assets/fonts/fonts.css", "/* synthetic fixture */")
    write(target / "assets/fonts/NOTICE.txt", "Synthetic font notice; no font binaries.")
    pages.write_inventory(target)
    assert not pages.check_site(target)


def test_update_only_selected_project_and_preserve_sources(tmp_path: Path) -> None:
    source, baseline, output = [tmp_path / p for p in ("source", "baseline", "output")]
    write(source / "a/index.html", "<title>A old</title><p>Old</p>")
    write(source / "b/index.html", "<title>B approved</title><p>Keep</p>")
    write(source / "b/assets/figure.svg", "<svg>unchanged</svg>")
    write(source / "a/work/keep.md", "canonical")
    exported(source, baseline)
    before = (baseline / "b/index.html").read_bytes()
    write(source / "a/index.html", "<title>A new</title><p>New</p>")
    write(source / "b/index.html", "<title>B unapproved</title><p>Local revision</p>")
    output.mkdir()  # An existing empty TEMP directory is also a valid staging target.
    entries = pages.export_update(source, output, baseline, {"a"})
    assert {e["path"] for e in entries} == {"a/index.html", "b/index.html"}
    assert (output / "b/index.html").read_bytes() == before
    assert (output / "b/assets/figure.svg").read_bytes() == (
        baseline / "b/assets/figure.svg"
    ).read_bytes()
    assert "A new" in (output / "a/index.html").read_text()
    assert "B unapproved" not in (output / "index.html").read_text()
    assert (source / "a/work/keep.md").read_text() == "canonical"
    assert not (output / "a/work").exists()
    assert not pages.check_site(output)
    assert (baseline / "a/index.html").read_bytes() != (output / "a/index.html").read_bytes()


def test_selection_does_not_walk_unselected_or_private_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(tmp_path / "a/index.html", "approved")
    write(tmp_path / "a/work/huge.html", "private")
    write(tmp_path / "b/index.html", "not selected")
    original = pages.os.walk
    visited = []

    def observe(*args, **kwargs):
        for row in original(*args, **kwargs):
            visited.append(Path(row[0]))
            yield row

    monkeypatch.setattr(pages.os, "walk", observe)
    assert pages.public_files(tmp_path, projects={"a"}) == [tmp_path / "a/index.html"]
    assert tmp_path / "a/work" not in visited
    assert tmp_path / "b" not in visited


def test_invalid_and_private_selection_fail_closed(tmp_path: Path) -> None:
    source, baseline = tmp_path / "source", tmp_path / "baseline"
    write(source / "a/index.html", "<title>A</title>")
    exported(source, baseline)
    write(source / "private/index.html", "<title>Private</title>")
    write(source / "private/work/reader.json", '{"public_export": false}')
    for selections in ({"../a"}, {"missing"}, {"private"}, {"assets"}):
        with pytest.raises(ValueError):
            pages.export_update(source, tmp_path / "output", baseline, selections)
        assert not (tmp_path / "output").exists()
    with pytest.raises(ValueError, match="overlap"):
        pages.export_update(source, baseline / "nested", baseline, {"a"})
    with pytest.raises(ValueError, match="requires"):
        pages.export_update(source, tmp_path / "output", baseline, set())


def git(repo: Path, *args: str) -> None:
    executable = shutil.which("git")
    if not executable:
        pytest.skip("Git is not installed")
    subprocess.run(  # noqa: S603
        [
            executable,
            "-c",
            "core.hooksPath=",
            "-c",
            "commit.gpgSign=false",
            "-C",
            str(repo),
            *args,
        ],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def published(tmp_path: Path) -> tuple[Path, Path]:
    site, checkout, remote = [tmp_path / p for p in ("site", "checkout", "origin.git")]
    write(site / "a/index.html", "<title>A</title>\n<p>Approved</p>\n")
    (site / "a/fixture.png").write_bytes(b"\x89PNG\r\n\x00synthetic")
    write(site / "site-manifest.json", '{"pages": [{"path": "a/index.html", "title": "A"}]}')
    git(tmp_path, "init", "--bare", str(remote))
    git(tmp_path, "init", "--initial-branch=pages-content", str(checkout))
    git(checkout, "config", "core.autocrlf", "false")
    git(checkout, "config", "user.name", "Synthetic Test")
    git(checkout, "config", "user.email", "test@example.invalid")
    for p in site.rglob("*"):
        if p.is_file():
            target = checkout / p.relative_to(site)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(p.read_bytes())
    git(checkout, "add", ".")
    git(checkout, "commit", "-m", "synthetic fixture")
    git(checkout, "remote", "add", "origin", str(remote))
    git(checkout, "push", "origin", "pages-content")
    return site, checkout


def test_verify_git_object_bytes_and_text_newlines(published: tuple[Path, Path]) -> None:
    site, checkout = published
    path = site / "a/index.html"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    result, blobs = pages_verify.verify_snapshot(checkout, site)
    assert result["remote_verified"] and result["files_verified"] == 3
    assert result["git_normalized_text_files"] == ["a/index.html"]
    assert b"\r\n" not in blobs["a/index.html"]
    path.write_bytes(b"<title>Changed</title>")
    with pytest.raises(ValueError, match="differs"):
        pages_verify.verify_snapshot(checkout, site)


def test_binary_bytes_must_match_exactly(published: tuple[Path, Path]) -> None:
    site, checkout = published
    path = site / "a/fixture.png"
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    with pytest.raises(ValueError, match="content differs"):
        pages_verify.verify_snapshot(checkout, site)


def test_verification_rejects_extra_files_and_remote_tip_change(
    published: tuple[Path, Path],
) -> None:
    site, checkout = published
    write(checkout / "extra.html", "unapproved")
    git(checkout, "add", ".")
    git(checkout, "commit", "-m", "different fixture")
    with pytest.raises(ValueError, match="tip differs"):
        pages_verify.verify_snapshot(checkout, site)
    git(checkout, "push", "origin", "pages-content")
    with pytest.raises(ValueError, match="allowlist"):
        pages_verify.verify_snapshot(checkout, site)


def test_live_verification_is_one_shot_and_restricted(monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    payload = b"approved"
    calls = []

    class Response(io.BytesIO):
        status = 200

    def respond(request, timeout):
        calls.append(request.full_url)
        assert timeout == 25
        return Response(payload)

    monkeypatch.setattr(pages_verify.urllib.request, "urlopen", respond)
    results = pages_verify.verify_live(
        "https://example.invalid/library/",
        ["a/index.html", "a/index.html"],
        {"a/index.html": payload},
    )
    assert len(calls) == 1 and results[0]["matches"]
    assert results[0]["actual_sha256"] == hashlib.sha256(payload).hexdigest()
    for base in ("http://example.invalid/", "https://user:password@example.invalid/"):
        with pytest.raises(ValueError):
            pages_verify.verify_live(base, ["a/index.html"], {"a/index.html": payload})
    with pytest.raises(ValueError):
        pages_verify.verify_live("https://example.invalid/", ["../private"], {})


def test_cli_keeps_default_output_short_and_live_failure_distinct(
    published: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    site, checkout = published
    args = ["--site", str(site), "--checkout", str(checkout)]
    assert pages_verify.main(args) == 0
    output = capsys.readouterr().out
    assert "Remote verified" in output and "{" not in output
    monkeypatch.setattr(
        pages_verify, "verify_live", lambda *args: [{"path": "a/index.html", "matches": False}]
    )
    assert (
        pages_verify.main(
            [*args, "--base-url", "https://example.invalid/", "--path", "a/index.html"]
        )
        == 2
    )
    assert "Do not repush" in capsys.readouterr().out
    report = site.parent / "report.json"
    assert pages_verify.main([*args, "--report", str(report)]) == 0
    assert json.loads(report.read_text())["remote_verified"]
    with pytest.raises(SystemExit):
        pages_verify.main([*args, "--report", str(site / "leak.json")])
