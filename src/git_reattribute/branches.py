from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from git_reattribute.gitwrapper import run_git


@dataclass
class Branch:
    name: str
    upstream: str | None


def list_local_branches(repo_root: Path) -> list[Branch]:
    result = run_git(
        ["for-each-ref", "--format=%(refname:short)%09%(upstream:short)", "refs/heads/"],
        cwd=repo_root,
    )
    branches: list[Branch] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        name, _, upstream = line.partition("\t")
        branches.append(Branch(name=name, upstream=upstream or None))
    return branches


def branch_exists(repo_root: Path, name: str) -> bool:
    result = run_git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{name}"],
        cwd=repo_root,
        check=False,
    )
    return result.returncode == 0


def upstream_of(repo_root: Path, branch: str) -> str | None:
    result = run_git(
        ["rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_remote_tracking_branch(repo_root: Path, name: str) -> bool:
    result = run_git(
        ["show-ref", "--verify", "--quiet", f"refs/remotes/{name}"],
        cwd=repo_root,
        check=False,
    )
    return result.returncode == 0
