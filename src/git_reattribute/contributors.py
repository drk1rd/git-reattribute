from __future__ import annotations

import re
from pathlib import Path

from git_reattribute.errors import BranchNotFoundError
from git_reattribute.gitwrapper import run_git
from git_reattribute.models import Contributor

# Matches trailer lines of the form "Co-authored-by: Name <email>".
# Deliberately anchored to the start of the line (trailers are one per line)
# and case-insensitive on the key, per Git's trailer convention.
_COAUTHOR_RE = re.compile(r"^Co-authored-by:\s*(.+?)\s*<([^>]+)>\s*$", re.IGNORECASE)

# Placeholder text passed to `git log --format`; git itself substitutes these
# with the corresponding raw byte in the *output*. They must not be actual
# NUL/unit-separator characters here, since argv strings can't embed NUL.
_FIELD_SEP_PLACEHOLDER = "%x00"
_RECORD_SEP_PLACEHOLDER = "%x01"

# The actual bytes git substitutes those placeholders with, used to split
# the decoded output back into fields/records.
_FIELD_SEP = "\x00"
_RECORD_SEP = "\x01"


def _log_records(repo_root: Path, branch: str) -> list[tuple[str, str, str, str]]:
    """Return (author_name, author_email, committer_name, committer_email, body) tuples.

    Uses raw %an/%ae/%cn/%ce fields rather than mailmap-resolved %aN/%aE/%cN/%cE
    so displayed identities always match the actual commit-object bytes, not
    mailmap-remapped display names.
    """
    fmt = (
        f"%an{_FIELD_SEP_PLACEHOLDER}%ae{_FIELD_SEP_PLACEHOLDER}"
        f"%cn{_FIELD_SEP_PLACEHOLDER}%ce{_FIELD_SEP_PLACEHOLDER}%B{_RECORD_SEP_PLACEHOLDER}"
    )
    result = run_git(["log", branch, f"--format={fmt}", "--no-color"], cwd=repo_root, check=False)
    if result.returncode != 0:
        raise BranchNotFoundError(branch)
    records = []
    for raw in result.stdout.split(_RECORD_SEP):
        # git's --format behaves like tformat and appends a trailing newline
        # after each record, which lands at the start of the *next* chunk
        # once split on our record separator.
        raw = raw.lstrip("\n")
        if not raw.strip("\n"):
            continue
        parts = raw.split(_FIELD_SEP)
        if len(parts) < 5:
            continue
        an, ae, cn, ce, body = parts[0], parts[1], parts[2], parts[3], _FIELD_SEP.join(parts[4:])
        records.append((an, ae, cn, ce, body.strip("\n")))
    return records


def _coauthors_in_body(body: str) -> list[tuple[str, str]]:
    found = []
    for line in body.splitlines():
        match = _COAUTHOR_RE.match(line.strip())
        if match:
            found.append((match.group(1), match.group(2)))
    return found


def discover_contributors(repo_root: Path, branch: str) -> list[Contributor]:
    records = _log_records(repo_root, branch)
    by_identity: dict[tuple[str, str], Contributor] = {}

    def bump(name: str, email: str, field: str) -> None:
        key = (name, email)
        contributor = by_identity.setdefault(key, Contributor(name=name, email=email))
        setattr(contributor, field, getattr(contributor, field) + 1)

    for an, ae, cn, ce, body in records:
        bump(an, ae, "author_commits")
        bump(cn, ce, "committer_commits")
        for coauthor_name, coauthor_email in _coauthors_in_body(body):
            bump(coauthor_name, coauthor_email, "coauthor_commits")

    return sorted(by_identity.values(), key=lambda c: c.total_commits, reverse=True)
