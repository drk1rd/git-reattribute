from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from git_reattribute.errors import MissingToolError


def run_git(
    args: list[str],
    cwd: Path | str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
    )


def check_git_version() -> str:
    if shutil.which("git") is None:
        raise MissingToolError(
            "git",
            "Install Git from https://git-scm.com/downloads and ensure it is on your PATH.",
        )
    result = run_git(["--version"])
    return result.stdout.strip()


def check_filter_repo_available() -> None:
    if shutil.which("git-filter-repo") is not None:
        return
    result = subprocess.run(
        ["git", "filter-repo", "--version"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise MissingToolError(
            "git-filter-repo",
            "Install it with:\n\n  python -m pip install git-filter-repo\n\n"
            "See https://github.com/newren/git-filter-repo for details.",
        )
