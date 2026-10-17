"""Cross-platform LF policy and byte-stable publication on isolated Git fixtures."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools import pages, pages_verify, publish_pages

ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run synthetic local Git commands without user hooks or signing."""
    executable = shutil.which("git")
    if not executable:
        pytest.skip("Git is not installed")
    return subprocess.run(  # noqa: S603
        [executable, "-c", "core.hooksPath=", "-c", "commit.gpgSign=false", "-C", str(root), *args],
        check=True,
        capture_output=True,
    )


def _write(path: Path, data: bytes) -> None:
    """Create an exact-byte fixture, independent of platform text I/O."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_repository_attributes_override_windows_autocrlf(tmp_path: Path) -> None:
    repo, clone = tmp_path / "source", tmp_path / "clone"
    _git(tmp_path, "init", str(repo))
    _git(repo, "config", "user.name", "Synthetic Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "core.autocrlf", "true")
    _write(repo / ".gitattributes", (ROOT / ".gitattributes").read_bytes())
    text = {
        "sample.py": b"value = 1\n",
        "sample.ps1": b"Write-Host 'test'\n",
        "sample.md": "中文\n正文\n".encode(),
        "sample.svg": b"<svg>\n</svg>\n",
    }
    binary = {"sample.png": b"\x89PNG\r\nsynthetic", "sample.woff2": b"wOF2\r\nsynthetic"}
    for name, data in (text | binary).items():
        _write(repo / name, data)
    added = _git(repo, "add", ".")
    assert b"will be replaced" not in added.stderr
    _git(repo, "commit", "-m", "synthetic attributes")
    _git(tmp_path, "-c", "core.autocrlf=true", "clone", str(repo), str(clone))
    for name, data in (text | binary).items():
        assert (clone / name).read_bytes() == data


def test_inventory_normalizes_text_before_hashing_but_never_binary(tmp_path: Path) -> None:
    text = {
        "index.html": "<title>原文</title>\r\n<p>正文</p>\r\n".encode(),
        "assets/styles/custom.css": b"p { color: black; }\r\n",
        "assets/scripts/custom.js": b'const value = "\\r\\n";\r\n',
        "assets/fonts/NOTICE.txt": b"Synthetic notice\r\n",
        "a/figure.svg": "<svg>\r\n<text>原图</text>\r\n</svg>\r\n".encode(),
        ".github/workflows/pages.yml": b"name: Synthetic\r\n",
        "site-manifest.json": b'{"pages": []}\r\n',
    }
    binary = {
        "a/figure.png": b"\x89PNG\r\n\x00synthetic",
        "assets/fonts/math.woff2": b"wOF2\r\n\x00synthetic",
    }
    for name, data in (text | binary).items():
        _write(tmp_path / name, data)
    _write(tmp_path / ".git/config", b"untouched\r\n")
    pages.write_inventory(tmp_path)
    for name, data in text.items():
        if name != "site-manifest.json":
            assert (tmp_path / name).read_bytes() == data.replace(b"\r\n", b"\n")
    for name, data in binary.items():
        assert (tmp_path / name).read_bytes() == data
    assert (tmp_path / ".git/config").read_bytes() == b"untouched\r\n"
    inventory = json.loads((tmp_path / "site-manifest.json").read_bytes())
    for name, digest in inventory["files"].items():
        assert digest == hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
    assert pages.normalize_public_text(tmp_path) == []


def test_live_checks_require_exact_canonical_lf_and_keep_font_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = b"<svg>\n</svg>\n"

    def respond(request, timeout):
        response = io.BytesIO(body)
        response.status = 200
        return response

    monkeypatch.setattr(pages_verify.urllib.request, "urlopen", respond)
    blobs = {"figure.svg": b"<svg>\r\n</svg>\r\n"}
    result = pages_verify.verify_live("https://example.invalid/", ["figure.svg"], blobs)[0]
    assert result["matches"] and result["canonical_lf_text"]
    assert result["git_sha256"] != result["expected_sha256"]
    body = blobs["figure.svg"]
    assert not pages_verify.verify_live("https://example.invalid/", ["figure.svg"], blobs)[0][
        "matches"
    ]
    body = b"wOF2\r\n\x00synthetic"
    font = pages_verify.verify_live(
        "https://example.invalid/", ["math.woff2"], {"math.woff2": body}
    )[0]
    assert font["matches"] and not font["canonical_lf_text"]


def test_invalid_text_is_rejected_before_any_normalization(tmp_path: Path) -> None:
    _write(tmp_path / "index.html", b"<title>Keep</title>\r\n")
    _write(tmp_path / "assets/fonts/NOTICE.txt", b"\xff\r\n")
    with pytest.raises(ValueError, match="UTF-8"):
        pages.normalize_public_text(tmp_path)
    assert (tmp_path / "index.html").read_bytes() == b"<title>Keep</title>\r\n"


def test_normalization_cannot_target_outside_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    allowed, other = tmp_path / "allowed", tmp_path / "other"
    allowed.mkdir()
    _write(other / "index.html", b"<title>Keep</title>\r\n")
    monkeypatch.setattr(pages.tempfile, "gettempdir", lambda: str(allowed))
    with pytest.raises(ValueError, match="system TEMP"):
        pages.normalize_public_text(other)
    assert (other / "index.html").read_bytes() == b"<title>Keep</title>\r\n"


def test_publication_roundtrip_needs_no_git_newline_exceptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    global_config = tmp_path / "synthetic-global.config"
    config_bytes = b"[core]\n\tautocrlf = true\n"
    global_config.write_bytes(config_bytes)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    site, checkout, remote = [tmp_path / name for name in ("site", "checkout", "remote.git")]
    _write(site / "index.html", b"<title>Approved</title>\r\n")
    _write(site / "a/figure.svg", b"<svg>\r\n</svg>\r\n")
    _write(site / "assets/fonts/math.woff2", b"wOF2\r\n\x00synthetic")
    _write(site / "site-manifest.json", b'{"pages": []}\r\n')
    pages.write_inventory(site)
    _git(tmp_path, "init", "--bare", str(remote))
    repo = tmp_path / "source"
    _git(tmp_path, "init", str(repo))
    _git(repo, "config", "user.name", "Synthetic Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "remote", "add", "origin", str(remote))
    _write(repo / "work/keep.md", b"canonical source\r\n")
    assert _git(repo, "config", "core.autocrlf").stdout.strip() == b"true"
    checkout = publish_pages.publish_site(site, push=True, repo=repo, state=tmp_path / "state")
    report, _ = pages_verify.verify_snapshot(checkout, site)
    assert report["git_normalized_text_files"] == []
    assert report["binary_bytes_match"]
    assert _git(checkout, "config", "core.autocrlf").stdout.strip() == b"false"
    assert _git(checkout, "config", "core.eol").stdout.strip() == b"lf"
    repeat = publish_pages.publish_site(site, repo=repo, state=tmp_path / "state")
    assert _git(repeat, "rev-parse", "HEAD").stdout == _git(checkout, "rev-parse", "HEAD").stdout
    assert (repo / "work/keep.md").read_bytes() == b"canonical source\r\n"
    assert _git(repo, "config", "core.autocrlf").stdout.strip() == b"true"
    assert global_config.read_bytes() == config_bytes
    script = (ROOT / "tools/publish-pages.ps1").read_text(encoding="utf-8")
    assert "publish_pages.py" in script and "git -C" not in script
