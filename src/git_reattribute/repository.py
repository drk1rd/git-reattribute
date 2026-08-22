from __future__ import annotations

from pathlib import Path

from git_reattribute.errors import NotAGitRepositoryError
from git_reattribute.gitwrapper import run_git


def find_repo_root(start: Path | str | None = None) -> Path:
    cwd = Path(start) if start else Path.cwd()
    result = run_git(["rev-parse", "--show-toplevel"], cwd=cwd, check=False)
    if result.returncode != 0:
        raise NotAGitRepositoryError()
    return Path(result.stdout.strip())


def current_branch(repo_root: Path) -> str | None:
    result = run_git(["symbolic-ref", "--short", "-q", "HEAD"], cwd=repo_root, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_clean_working_tree(repo_root: Path) -> tuple[bool, list[str]]:
    result = run_git(["status", "--porcelain"], cwd=repo_root)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    modified = [line[3:] for line in lines]
    return (len(lines) == 0, modified)


def list_remotes(repo_root: Path) -> list[str]:
    result = run_git(["remote"], cwd=repo_root)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_shallow_repository(repo_root: Path) -> bool:
    result = run_git(["rev-parse", "--is-shallow-repository"], cwd=repo_root)
    return result.stdout.strip() == "true"
