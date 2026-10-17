"""Portable external-venv setup and Python command runner; no shell activation required."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def environment(root: Path = ROOT) -> dict:
    """Describe TEMP-only development state, preserving the existing Windows identity."""
    identity = os.path.normcase(str(root.resolve()))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    state = Path(tempfile.gettempdir()) / f"paper-translation-{digest}"
    python = state / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    settings = {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPYCACHEPREFIX": str(state / "pycache"),
        "RUFF_CACHE_DIR": str(state / "ruff-cache"),
        "PIP_CACHE_DIR": str(state / "pip-cache"),
    }
    option = f'-o cache_dir="{(state / "pytest-cache").as_posix()}"'
    existing = os.environ.get("PYTEST_ADDOPTS", "")
    settings["PYTEST_ADDOPTS"] = existing if option in existing else f"{existing} {option}".strip()
    return {"project_temp": str(state), "python": str(python), "env": settings}


def prepare(*, create_venv: bool = False, root: Path = ROOT) -> dict:
    """Create disposable directories and optionally a venv, never manuscript material."""
    if sys.version_info < (3, 12):  # noqa: UP036 (bootstrap may run outside the venv)
        raise ValueError("Python 3.12 or newer is required")
    info = environment(root)
    state = Path(info["project_temp"])
    for name in ("", "tasks", "reports", "scratch"):
        (state / name).mkdir(parents=True, exist_ok=True)
    if create_venv and not Path(info["python"]).is_file():
        venv.EnvBuilder(with_pip=True).create(state / "venv")
    return info


def run_python(arguments: list[str], info: dict, *, root: Path = ROOT) -> int:
    """Invoke the external interpreter with isolated caches and literal argv entries."""
    python = Path(info["python"])
    if not python.is_file():
        raise ValueError("external venv is missing; run: python tools/dev.py setup")
    return subprocess.run(  # noqa: S603
        [str(python), *arguments], cwd=root, env=os.environ | info["env"], check=False
    ).returncode


def main(argv: list[str] | None = None) -> int:
    """Prepare an environment or execute Python without platform-specific activation."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    info_parser = commands.add_parser("env", help="print portable paths/environment as JSON")
    info_parser.add_argument("--create-venv", action="store_true")
    setup = commands.add_parser(
        "setup", help="create the external venv and install pinned packages"
    )
    setup.add_argument("--pages", action="store_true", help="also install publication dependencies")
    setup.add_argument("--browser", action="store_true", help="also install optional Playwright")
    setup.add_argument("--pandoc", action="store_true", help="also install the document renderer")
    run = commands.add_parser("run", help="run external-venv Python; put -- before its arguments")
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        info = prepare(create_venv=args.command == "setup" or getattr(args, "create_venv", False))
        if args.command == "env":
            print(json.dumps(info, ensure_ascii=False))
            return 0
        if args.command == "setup":
            packages = ["-m", "pip", "install", "-r", str(ROOT / "requirements.txt")]
            if args.pages:
                packages += ["-r", str(ROOT / "requirements-pages.txt")]
            if args.browser:
                packages += ["playwright==1.58.0"]
            if args.pandoc:
                packages += [
                    "--only-binary=pypandoc_binary",
                    "-r",
                    str(ROOT / "requirements-pandoc.txt"),
                ]
            return run_python(packages, info)
        arguments = args.arguments
        if arguments[:1] == ["--"]:
            arguments = arguments[1:]
        if not arguments:
            parser.error("run needs Python arguments after --")
        return run_python(arguments, info)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Environment error: {error}\n")


if __name__ == "__main__":
    # A bootstrap started outside the configured environment must not cache local modules.
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
