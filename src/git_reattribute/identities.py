from __future__ import annotations

from pathlib import Path

from git_reattribute.errors import MissingGitIdentityError
from git_reattribute.gitwrapper import run_git
from git_reattribute.models import Identity


def current_git_identity(repo_root: Path) -> Identity:
    name_result = run_git(["config", "user.name"], cwd=repo_root, check=False)
    email_result = run_git(["config", "user.email"], cwd=repo_root, check=False)
    name = name_result.stdout.strip()
    email = email_result.stdout.strip()
    if not name or not email:
        raise MissingGitIdentityError()
    return Identity(name=name, email=email)


def resolve_target_identity(
    repo_root: Path,
    to_current_user: bool = False,
    to_name: str | None = None,
    to_email: str | None = None,
) -> Identity:
    if to_current_user:
        return current_git_identity(repo_root)
    if to_name and to_email:
        return Identity(name=to_name, email=to_email)
    raise ValueError(
        "A target identity requires --to-current-user, or both --to-name and --to-email."
    )
