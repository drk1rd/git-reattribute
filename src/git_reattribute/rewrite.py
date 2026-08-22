from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from git_reattribute.branches import branch_exists
from git_reattribute.contributors import discover_contributors
from git_reattribute.errors import (
    BranchNotFoundError,
    DirtyWorkingTreeError,
    IdentityNotFoundError,
    RewriteFailedError,
)
from git_reattribute.gitwrapper import check_filter_repo_available, run_git
from git_reattribute.models import Identity, IdentityType, RewriteOptions, RewriteResult
from git_reattribute.repository import is_clean_working_tree

BACKUP_REF_PREFIX = "refs/backup/git-reattribute"


def has_signed_commits(repo_root: Path, branch: str) -> bool:
    result = run_git(["log", branch, "--pretty=%G?"], cwd=repo_root)
    return any(code.strip() and code.strip() != "N" for code in result.stdout.splitlines())


def create_backup_ref(repo_root: Path, branch: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    ref = f"{BACKUP_REF_PREFIX}/{timestamp}"
    tip = run_git(["rev-parse", branch], cwd=repo_root).stdout.strip()
    run_git(["update-ref", ref, tip], cwd=repo_root)
    return ref


def _build_callback(
    source: Identity,
    target: Identity,
    identity_type: IdentityType,
    strip_coauthor_trailers: bool,
) -> str:
    rewrite_author = identity_type in (IdentityType.AUTHOR, IdentityType.BOTH)
    rewrite_committer = identity_type in (IdentityType.COMMITTER, IdentityType.BOTH)
    return f"""
import re

source_name = {source.name.encode("utf-8")!r}
source_email = {source.email.encode("utf-8")!r}
target_name = {target.name.encode("utf-8")!r}
target_email = {target.email.encode("utf-8")!r}
rewrite_author = {rewrite_author!r}
rewrite_committer = {rewrite_committer!r}
strip_coauthor = {strip_coauthor_trailers!r}

if rewrite_author and commit.author_name == source_name and commit.author_email == source_email:
    commit.author_name = target_name
    commit.author_email = target_email

if rewrite_committer and commit.committer_name == source_name and commit.committer_email == source_email:
    commit.committer_name = target_name
    commit.committer_email = target_email

if strip_coauthor:
    pattern = re.compile(
        rb"^Co-authored-by:\\s*" + re.escape(source_name) + rb"\\s*<\\s*" + re.escape(source_email) + rb"\\s*>\\s*$\\n?",
        re.IGNORECASE | re.MULTILINE,
    )
    commit.message = pattern.sub(b"", commit.message)
    commit.message = re.sub(rb"\\n{{3,}}", b"\\n\\n", commit.message)
""".strip()


class RewriteEngine:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def replace_identity(self, options: RewriteOptions) -> RewriteResult:
        check_filter_repo_available()

        if not branch_exists(self.repo_root, options.branch):
            raise BranchNotFoundError(options.branch)

        if not options.allow_dirty:
            clean, modified = is_clean_working_tree(self.repo_root)
            if not clean:
                raise DirtyWorkingTreeError(modified)

        contributors = discover_contributors(self.repo_root, options.branch)
        source_contributor = next(
            (
                c
                for c in contributors
                if c.name == options.source.name and c.email == options.source.email
            ),
            None,
        )
        has_author_match = source_contributor is not None and source_contributor.author_commits > 0
        has_committer_match = (
            source_contributor is not None and source_contributor.committer_commits > 0
        )
        has_coauthor_match = (
            source_contributor is not None and source_contributor.coauthor_commits > 0
        )
        if not (has_author_match or has_committer_match or has_coauthor_match):
            raise IdentityNotFoundError(str(options.source), options.branch)

        # Merge commits require no special handling: filter-repo rewrites them
        # natively as part of a full-branch rewrite. This only becomes a
        # concern if future --commit-range filtering is introduced.

        backup_ref = create_backup_ref(self.repo_root, options.branch)

        callback = _build_callback(
            options.source, options.target, options.identity_type, options.strip_coauthor_trailers
        )

        filter_repo_exe = shutil.which("git-filter-repo")
        if filter_repo_exe:
            cmd = [filter_repo_exe]
        else:
            cmd = ["git", "filter-repo"]
        cmd += [
            "--force",  # our own backup ref supersedes filter-repo's fresh-clone safety check
            "--refs",
            options.branch,
            "--commit-callback",
            callback,
        ]
        result = subprocess.run(cmd, cwd=self.repo_root, text=True, capture_output=True)
        if result.returncode != 0:
            raise RewriteFailedError(result.stderr.strip() or result.stdout.strip())

        if options.identity_type is IdentityType.AUTHOR:
            commits_rewritten = source_contributor.author_commits if source_contributor else 0
        elif options.identity_type is IdentityType.COMMITTER:
            commits_rewritten = source_contributor.committer_commits if source_contributor else 0
        else:
            commits_rewritten = (
                max(source_contributor.author_commits, source_contributor.committer_commits)
                if source_contributor
                else 0
            )

        coauthor_trailers_removed = (
            source_contributor.coauthor_commits
            if options.strip_coauthor_trailers and source_contributor
            else 0
        )

        return RewriteResult(
            backup_ref=backup_ref,
            commits_rewritten=commits_rewritten,
            coauthor_trailers_removed=coauthor_trailers_removed,
            success=True,
        )
