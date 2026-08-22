from __future__ import annotations

from pathlib import Path

from git_reattribute.gitwrapper import run_git
from git_reattribute.models import PushResult


def push_with_lease(repo_root: Path, remote: str, branch: str) -> PushResult:
    result = run_git(
        ["push", "--force-with-lease", remote, branch],
        cwd=repo_root,
        check=False,
    )
    if result.returncode == 0:
        return PushResult(success=True, rejected=False, message=result.stdout.strip())

    stderr = result.stderr.strip()
    rejected = "stale info" in stderr or "rejected" in stderr
    if rejected:
        return PushResult(
            success=False,
            rejected=True,
            message=(
                "The remote branch changed after the rewrite began.\n\n"
                "No remote history was overwritten.\n\n"
                "Review the remote changes before attempting another push."
            ),
        )
    return PushResult(success=False, rejected=False, message=stderr)
