from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    AUTHOR = "author"
    COMMITTER = "committer"
    COAUTHOR = "coauthor"


@dataclass(frozen=True)
class DenyEntry:
    name: str | None
    email: str | None

    def matches(self, name: str, email: str) -> bool:
        if self.name is not None and self.name != name:
            return False
        if self.email is not None and not _email_matches(self.email, email):
            return False
        return self.name is not None or self.email is not None


def _email_matches(pattern: str, email: str) -> bool:
    if "*" not in pattern:
        return pattern == email
    prefix, _, suffix = pattern.partition("*")
    return email.startswith(prefix) and email.endswith(suffix) and len(email) >= len(prefix) + len(suffix)


@dataclass
class Violation:
    commit_sha: str
    role: Role
    name: str
    email: str

    def fix_command_hint(self, branch: str) -> str:
        return f"git-reattribute --branch {branch} --from-email {self.email} --to-current-user"
