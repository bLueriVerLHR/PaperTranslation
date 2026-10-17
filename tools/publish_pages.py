"""Publish one explicitly approved TEMP snapshot with portable, non-force Git operations."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    sys.dont_write_bytecode = True
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import dev, pages, pages_verify  # noqa: E402


def git(
    repo: Path, *args: str, allowed: tuple[int, ...] = (0,)
) -> subprocess.CompletedProcess[str]:
    """Run literal Git argv without a shell, preserving useful failure diagnostics."""
    executable = shutil.which("git")
    if not executable:
        raise ValueError("Git is required")
    try:
        result = subprocess.run(  # noqa: S603
            [executable, "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        guidance = (
            "push outcome unknown; inspect the remote and do not repush automatically"
            if args[0] == "push"
            else "inspect local Git configuration/output"
        )
        raise ValueError(f"Git {args[0]} timed out; {guidance}") from None
    if result.returncode not in allowed:
        raise ValueError(
            f"Git {args[0]} failed (exit {result.returncode}); inspect local Git configuration/output"
        )
    return result


def publish_site(
    site: Path, *, push: bool = False, repo: Path = ROOT, state: Path | None = None
) -> Path:
    """Stage/commit approved bytes in a new owned TEMP checkout and optionally push.

    Never clean the caller's repository, rewrite history, replay a push, or export local
    manuscripts. The input is already an explicitly reviewed reader-only snapshot.
    """
    site = pages_verify.temp_directory(site)
    if errors := pages.check_site(site):
        raise ValueError("public-site validation failed: " + "; ".join(errors[:3]))
    pages.write_inventory(site)
    remote = git(repo, "remote", "get-url", "origin").stdout.strip()
    name = git(repo, "config", "user.name", allowed=(0, 1)).stdout.strip()
    email = git(repo, "config", "user.email", allowed=(0, 1)).stdout.strip()
    if not name or not email:
        raise ValueError("configure repository user.name and user.email first")
    state = state or Path(dev.prepare(root=repo)["project_temp"])
    if not state.is_absolute() or not state.resolve().is_relative_to(
        Path(tempfile.gettempdir()).resolve()
    ):
        raise ValueError("publication state must be under system TEMP")
    scratch = state / "scratch"
    checkout = scratch / f"pages-checkout-{uuid.uuid4().hex}"
    if checkout.exists():
        raise ValueError("fresh publication checkout already exists")
    if checkout.resolve().is_relative_to(site) or site.is_relative_to(checkout.resolve()):
        raise ValueError("publication checkout must not overlap the approved site")
    if checkout.resolve().is_relative_to(repo.resolve()):
        raise ValueError("publication checkout must not be inside the caller's repository")
    scratch.mkdir(parents=True, exist_ok=True)
    exists = git(repo, "ls-remote", "--heads", "origin", "pages-content").stdout.strip()
    if exists:
        git(
            repo,
            "clone",
            "--config",
            "core.autocrlf=false",
            "--config",
            "core.eol=lf",
            "--single-branch",
            "--branch",
            "pages-content",
            remote,
            str(checkout),
        )
    else:
        git(repo, "init", "--initial-branch=pages-content", str(checkout))
        git(checkout, "remote", "add", "origin", remote)
    # Only this fresh, dedicated TEMP repository gets local configuration changes.
    git(checkout, "config", "core.autocrlf", "false")
    git(checkout, "config", "core.eol", "lf")
    git(checkout, "config", "user.name", name)
    git(checkout, "config", "user.email", email)
    for path in checkout.iterdir():
        if path.name != ".git":
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
    for path in site.iterdir():
        if path.name == ".git":
            continue
        target = checkout / path.name
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)
    if errors := pages.check_site(checkout):
        raise ValueError("content checkout validation failed: " + "; ".join(errors[:3]))
    pages.write_inventory(checkout)
    git(checkout, "add", "--all")
    if git(checkout, "diff", "--cached", "--quiet", allowed=(0, 1)).returncode == 1:
        git(checkout, "commit", "-m", "docs(pages): update public reading library")
    if push:
        git(checkout, "push", "origin", "HEAD:pages-content")
        try:
            report, _ = pages_verify.verify_snapshot(checkout, site)
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            raise ValueError(
                f"push succeeded but verification failed; inspect {checkout}; do not repush automatically: {error}"
            ) from error
        print(
            f"Remote verified: {report['pages_content_commit'][:12]}; {report['files_verified']} files; "
            f"{len(report['git_normalized_text_files'])} newline exceptions; binaries exact."
        )
    return checkout


def main(argv: list[str] | None = None) -> int:
    """Publish through Python on Windows, Linux or macOS; PS is optional compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args(argv)
    try:
        info = dev.prepare()
        os.environ.update(info["env"])
        checkout = publish_site(args.site, push=args.push)
        print(f"Content checkout: {checkout}")
        print("Main and canonical work trees were not changed by this command.")
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Publication failed: {error}\n")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
