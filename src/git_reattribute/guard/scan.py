from __future__ import annotations

import re
import subprocess
from pathlib import Path

from git_reattribute.guard.config import Config
from git_reattribute.guard.errors import GuardNotAGitRepositoryError, InvalidRangeError
from git_reattribute.guard.models import Role, Violation

_COAUTHOR_RE = re.compile(r"^Co-authored-by:\s*(.+?)\s*<([^>]+)>\s*$", re.IGNORECASE)

# Placeholder text for `git log --format`; git substitutes these with the
# corresponding raw byte in the *output*. Actual argv strings can't embed a
# literal NUL, so we pass git's own %x00/%x01 escapes and split on the real
# bytes once we have the decoded output. (Same approach as
# git_reattribute.contributors, adapted to a commit range.)
_FIELD_SEP_PLACEHOLDER = "%x00"
_RECORD_SEP_PLACEHOLDER = "%x01"
_FIELD_SEP = "\x00"
_RECORD_SEP = "\x01"


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)


def coauthors_in_body(body: str) -> list[tuple[str, str]]:
    found = []
    for line in body.splitlines():
        match = _COAUTHOR_RE.match(line.strip())
        if match:
            found.append((match.group(1), match.group(2)))
    return found


def _log_records(repo_root: Path, commit_range: str) -> list[tuple[str, str, str, str, str, str]]:
    fmt = (
        f"%H{_FIELD_SEP_PLACEHOLDER}%an{_FIELD_SEP_PLACEHOLDER}%ae{_FIELD_SEP_PLACEHOLDER}"
        f"%cn{_FIELD_SEP_PLACEHOLDER}%ce{_FIELD_SEP_PLACEHOLDER}%B{_RECORD_SEP_PLACEHOLDER}"
    )
    result = _run_git(["log", commit_range, f"--format={fmt}", "--no-color"], cwd=repo_root)
    if result.returncode != 0:
        stderr = result.stderr.lower()
        if "not a git repository" in stderr:
            raise GuardNotAGitRepositoryError()
        raise InvalidRangeError(commit_range)

    records = []
    for raw in result.stdout.split(_RECORD_SEP):
        raw = raw.lstrip("\n")
        if not raw.strip("\n"):
            continue
        parts = raw.split(_FIELD_SEP)
        if len(parts) < 6:
            continue
        sha, an, ae, cn, ce = parts[0], parts[1], parts[2], parts[3], parts[4]
        body = _FIELD_SEP.join(parts[5:]).strip("\n")
        records.append((sha, an, ae, cn, ce, body))
    return records


def scan_range(repo_root: Path, commit_range: str, config: Config) -> list[Violation]:
    violations: list[Violation] = []
    for sha, an, ae, cn, ce, body in _log_records(repo_root, commit_range):
        for entry in config.deny:
            if entry.matches(an, ae):
                violations.append(Violation(commit_sha=sha, role=Role.AUTHOR, name=an, email=ae))
            if entry.matches(cn, ce):
                violations.append(Violation(commit_sha=sha, role=Role.COMMITTER, name=cn, email=ce))
        if config.check_coauthors:
            for coauthor_name, coauthor_email in coauthors_in_body(body):
                for entry in config.deny:
                    if entry.matches(coauthor_name, coauthor_email):
                        violations.append(
                            Violation(
                                commit_sha=sha,
                                role=Role.COAUTHOR,
                                name=coauthor_name,
                                email=coauthor_email,
                            )
                        )
    return violations
