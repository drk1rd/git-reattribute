from __future__ import annotations

from pathlib import Path

from git_reattribute.contributors import discover_contributors
from git_reattribute.models import Contributor, Identity, IdentityType, VerificationResult


def _find(contributors: list[Contributor], identity: Identity) -> Contributor | None:
    return next(
        (c for c in contributors if c.name == identity.name and c.email == identity.email),
        None,
    )


def verify_rewrite(
    repo_root: Path,
    branch: str,
    source: Identity,
    target: Identity,
    identity_type: IdentityType,
    before: list[Contributor],
) -> VerificationResult:
    after = discover_contributors(repo_root, branch)

    source_before = _find(before, source)
    source_after = _find(after, source)
    target_after = _find(after, target)

    source_author_before = source_before.author_commits if source_before else 0
    source_committer_before = source_before.committer_commits if source_before else 0
    source_author_after = source_after.author_commits if source_after else 0
    source_committer_after = source_after.committer_commits if source_after else 0
    coauthor_trailers_after = source_after.coauthor_commits if source_after else 0

    passed = True
    if identity_type in (IdentityType.AUTHOR, IdentityType.BOTH):
        passed = passed and source_author_after == 0
    if identity_type in (IdentityType.COMMITTER, IdentityType.BOTH):
        passed = passed and source_committer_after == 0
    passed = passed and coauthor_trailers_after == 0

    return VerificationResult(
        source_author_before=source_author_before,
        source_author_after=source_author_after,
        source_committer_before=source_committer_before,
        source_committer_after=source_committer_after,
        target_author_after=target_after.author_commits if target_after else 0,
        target_committer_after=target_after.committer_commits if target_after else 0,
        coauthor_trailers_after=coauthor_trailers_after,
        passed=passed,
    )
