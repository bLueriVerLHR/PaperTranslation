"""Portable external environments and safe, non-replaying Python publication."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from tools import dev, pages_verify, publish_pages


def test_environment_identity_paths_and_cache_option_are_portable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "项目 with spaces"
    monkeypatch.setattr(dev.tempfile, "gettempdir", lambda: str(tmp_path))
    info = dev.environment(root)
    digest = hashlib.sha256(os.path.normcase(str(root.resolve())).encode()).hexdigest()[:12]
    state = tmp_path / f"paper-translation-{digest}"
    assert Path(info["project_temp"]) == state
    assert Path(info["python"]).is_relative_to(state)
    assert all(
        str(state) in info["env"][key]
        for key in ("PYTHONPYCACHEPREFIX", "RUFF_CACHE_DIR", "PIP_CACHE_DIR")
    )
    monkeypatch.setenv("PYTEST_ADDOPTS", info["env"]["PYTEST_ADDOPTS"])
    assert dev.environment(root)["env"]["PYTEST_ADDOPTS"] == info["env"]["PYTEST_ADDOPTS"]


def test_prepare_uses_stdlib_venv_without_creating_workspace_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr(dev.tempfile, "gettempdir", lambda: str(tmp_path))
    created = []

    class FakeBuilder:
        def __init__(self, *, with_pip: bool) -> None:
            assert with_pip

        def create(self, path: Path) -> None:
            created.append(path)

    monkeypatch.setattr(dev.venv, "EnvBuilder", FakeBuilder)
    info = dev.prepare(create_venv=True, root=root)
    assert created == [Path(info["project_temp"]) / "venv"]
    assert not list(root.iterdir())
    assert (Path(info["project_temp"]) / "scratch").is_dir()


def test_run_uses_literal_argv_and_does_not_mutate_parent_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python = tmp_path / "python with spaces"
    python.write_bytes(b"synthetic interpreter")
    info = {"python": str(python), "env": {"PORTABLE_TEST": "child-only"}}
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 7)

    monkeypatch.delenv("PORTABLE_TEST", raising=False)
    monkeypatch.setattr(dev.subprocess, "run", execute)
    arguments = ["-c", "print('literal & not shell')", "中文 with spaces"]
    assert dev.run_python(arguments, info, root=tmp_path) == 7
    assert calls[0][0] == [str(python), *arguments]
    assert calls[0][1]["env"]["PORTABLE_TEST"] == "child-only"
    assert not calls[0][1].get("shell", False)
    assert "PORTABLE_TEST" not in os.environ


def test_run_rejects_a_missing_venv(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="setup"):
        dev.run_python([], {"python": str(tmp_path / "missing"), "env": {}})


@pytest.mark.parametrize("timeout", [False, True])
def test_git_errors_do_not_echo_credentials_or_replay_unknown_pushes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, timeout: bool
) -> None:
    fake_url = "https://private-token@example.invalid/repo"

    def execute(argv, **kwargs):
        if timeout:
            raise subprocess.TimeoutExpired(argv, 180)
        return subprocess.CompletedProcess(argv, 128, stdout="", stderr=fake_url)

    monkeypatch.setattr(publish_pages.shutil, "which", lambda name: "git")
    monkeypatch.setattr(publish_pages.subprocess, "run", execute)
    with pytest.raises(ValueError) as caught:
        publish_pages.git(tmp_path, "push", fake_url)
    assert "private-token" not in str(caught.value)
    if timeout:
        assert "do not repush automatically" in str(caught.value)
        assert caught.value.__suppress_context__


@pytest.fixture
def publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    if not publish_pages.shutil.which("git"):
        pytest.skip("Git is not installed")
    global_config = tmp_path / "synthetic-global.config"
    global_config.write_text(
        "[core]\n\thooksPath =\n[commit]\n\tgpgSign = false\n", encoding="utf-8", newline="\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    site, repo, remote = [tmp_path / name for name in ("site", "repo", "remote.git")]
    site.mkdir()
    (site / "index.html").write_bytes(b"<title>Approved</title>\r\n")
    (site / "site-manifest.json").write_bytes(b'{"pages": []}\r\n')
    publish_pages.git(tmp_path, "init", str(repo))
    publish_pages.git(tmp_path, "init", "--bare", str(remote))
    publish_pages.git(repo, "config", "user.name", "Synthetic Test")
    publish_pages.git(repo, "config", "user.email", "test@example.invalid")
    publish_pages.git(repo, "remote", "add", "origin", str(remote))
    (repo / "keep.md").write_bytes(b"canonical\r\n")
    return site, repo, tmp_path / "state"


def test_successful_push_is_never_replayed_after_verification_failure(
    publication: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    site, repo, state = publication
    real_git, pushes = publish_pages.git, []

    def trace(root, *args, **kwargs):
        if args[0] == "push":
            pushes.append(args)
        return real_git(root, *args, **kwargs)

    def fail(*args, **kwargs):
        raise ValueError("synthetic verification failure")

    monkeypatch.setattr(publish_pages, "git", trace)
    monkeypatch.setattr(pages_verify, "verify_snapshot", fail)
    with pytest.raises(ValueError, match=r"push succeeded.*do not repush"):
        publish_pages.publish_site(site, push=True, repo=repo, state=state)
    assert len(pushes) == 1
    assert (repo / "keep.md").read_bytes() == b"canonical\r\n"


def test_publisher_rejects_checkout_overlap_without_creating_it(
    publication: tuple[Path, Path, Path],
) -> None:
    site, repo, _ = publication
    with pytest.raises(ValueError, match="overlap"):
        publish_pages.publish_site(site, repo=repo, state=site / "cache")
    assert not (site / "cache").exists()
    assert (repo / "keep.md").read_bytes() == b"canonical\r\n"
