"""Verify a pushed reader-only checkout and selected live files; never push or poll."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import pages  # noqa: E402

TEXT_TYPES = {".html", ".css", ".js", ".json", ".txt", ".yml"}


def git(checkout: Path, *arguments: str, data: bytes | None = None) -> bytes:
    """Run one bounded, read-only Git command without shell interpolation."""
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(checkout), *arguments],  # noqa: S607
        input=data,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise ValueError(
            "read-only Git inspection failed; inspect the checkout/remote configuration"
        )
    return result.stdout


def temp_directory(path: Path) -> Path:
    """Require an existing absolute TEMP directory, not a canonical source tree."""
    resolved = path.resolve()
    if not path.is_absolute() or not resolved.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError("checkout/site/report must use absolute system TEMP paths")
    if not resolved.is_dir():
        raise ValueError("checkout/site directory does not exist")
    return resolved


def tracked_blobs(checkout: Path, commit: str = "HEAD") -> dict[str, bytes]:
    """Read the Git tree once and all blobs through one batch process."""
    paths = []
    for row in git(checkout, "ls-tree", "-r", "-z", commit).split(b"\0"):
        if not row:
            continue
        metadata, name = row.split(b"\t", 1)
        mode, kind, _ = metadata.split()
        if mode not in {b"100644", b"100755"} or kind != b"blob":
            raise ValueError("tracked symlinks/submodules are not reader-only files")
        path = name.decode("utf-8")
        if "\n" in path or "\r" in path:
            raise ValueError("unsupported newline in a public filename")
        paths.append(path)
    payload = "".join(f"{commit}:{p}\n" for p in paths).encode("utf-8")
    stream = io.BytesIO(git(checkout, "cat-file", "--batch", data=payload))
    blobs = {}
    for path in paths:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError("Git blob batch did not match the inspected tree")
        content = stream.read(int(header[2]))
        if len(content) != int(header[2]) or stream.read(1) != b"\n":
            raise ValueError("incomplete Git blob response")
        blobs[path] = content
    return blobs


def verify_snapshot(checkout: Path, site: Path, *, check_main: bool = False) -> tuple[dict, dict]:
    """Compare remote commit identity and approved bytes, not Windows checkout newlines."""
    checkout, site = temp_directory(checkout), temp_directory(site)
    if errors := pages.check_site(site):
        raise ValueError("approved site is invalid: " + "; ".join(errors[:3]))
    commit = git(checkout, "rev-parse", "HEAD").decode().strip()
    rows = (
        git(checkout, "ls-remote", "--heads", "origin", "pages-content", "main")
        .decode()
        .splitlines()
    )
    refs = {r.split()[1]: r.split()[0] for r in rows}
    if refs.get("refs/heads/pages-content") != commit:
        raise ValueError(
            "remote content tip differs from this checkout; do not repush automatically"
        )
    if (
        check_main
        and refs.get("refs/heads/main") != git(ROOT, "rev-parse", "HEAD").decode().strip()
    ):
        raise ValueError("remote main differs from the current pipeline commit")
    blobs = tracked_blobs(checkout, commit)
    approved = {
        p.relative_to(site).as_posix(): p
        for p in site.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(site).parts
    }
    if approved.keys() != blobs.keys():
        raise ValueError("published tree differs from the approved file allowlist")
    normalized = []
    for name, path in approved.items():
        wanted, actual = path.read_bytes(), blobs[name]
        if wanted == actual:
            continue
        if path.suffix.lower() not in TEXT_TYPES or wanted.replace(
            b"\r\n", b"\n"
        ) != actual.replace(b"\r\n", b"\n"):
            raise ValueError(f"published content differs: {name}")
        normalized.append(name)
    return {
        "pages_content_commit": commit,
        "files_verified": len(blobs),
        "git_normalized_text_files": normalized,
        "binary_bytes_match": True,
        "remote_verified": True,
        "live_checks": [],
        "scope": "Git/public-file integrity, not semantic coverage or content correctness",
    }, blobs


def verify_live(base_url: str, paths: list[str], blobs: dict[str, bytes]) -> list[dict]:
    """Check selected public URLs once with default TLS and no Actions API dependency."""
    url = urlsplit(base_url)
    if (
        url.scheme != "https"
        or not url.netloc
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError("base URL must be plain HTTPS without credentials, query or fragment")
    results = []
    for name in dict.fromkeys(paths):
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or name not in blobs:
            raise ValueError("live path must be a tracked relative public filename")
        expected = hashlib.sha256(blobs[name]).hexdigest()
        request = urllib.request.Request(  # noqa: S310 (plain HTTPS validated above)
            base_url.rstrip("/") + "/" + quote(name, safe="/-._"),
            headers={
                "User-Agent": "PaperTranslation-publication-check",
                "Accept-Encoding": "identity",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:  # noqa: S310
                actual = hashlib.sha256(response.read()).hexdigest()
                results.append(
                    {
                        "path": name,
                        "status": response.status,
                        "expected_sha256": expected,
                        "actual_sha256": actual,
                        "matches": actual == expected,
                    }
                )
        except (urllib.error.URLError, OSError) as error:
            results.append({"path": name, "matches": False, "error": str(error)})
    return results


def main(argv: list[str] | None = None) -> int:
    """Print compact verification results; write detailed evidence only when requested."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--check-main", action="store_true")
    parser.add_argument("--base-url")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if bool(args.base_url) != bool(args.path):
        parser.error("live verification requires both --base-url and at least one --path")
    try:
        if args.report:
            if not args.report.is_absolute() or not args.report.resolve().is_relative_to(
                Path(tempfile.gettempdir()).resolve()
            ):
                raise ValueError("report must be an absolute system TEMP path")
            if args.report.resolve().is_relative_to(
                args.site.resolve()
            ) or args.report.resolve().is_relative_to(args.checkout.resolve()):
                raise ValueError("report must be outside the approved/published snapshot")
        report, blobs = verify_snapshot(args.checkout, args.site, check_main=args.check_main)
        if args.base_url:
            report["live_checks"] = verify_live(args.base_url, args.path, blobs)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
            )
        print(
            f"Remote verified: {report['pages_content_commit'][:12]}; {report['files_verified']} files; "
            f"{len(report['git_normalized_text_files'])} text newline normalizations; binaries exact."
        )
        for check in report["live_checks"]:
            print(f"Live {'MATCH' if check['matches'] else 'NOT MATCHED'}: {check['path']}")
        if any(not check["matches"] for check in report["live_checks"]):
            print(
                "Push is verified; deployment may be pending or failed. Do not repush automatically."
            )
            return 2
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Verification failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
