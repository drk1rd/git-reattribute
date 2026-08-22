from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IdentityType(str, Enum):
    AUTHOR = "author"
    COMMITTER = "committer"
    BOTH = "both"


@dataclass(frozen=True)
class Identity:
    name: str
    email: str

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


@dataclass
class Contributor:
    name: str
    email: str
    author_commits: int = 0
    committer_commits: int = 0
    coauthor_commits: int = 0

    @property
    def identity(self) -> Identity:
        return Identity(self.name, self.email)

    @property
    def total_commits(self) -> int:
        return max(self.author_commits, self.committer_commits)


@dataclass
class RewriteOptions:
    branch: str
    source: Identity
    target: Identity
    identity_type: IdentityType = IdentityType.BOTH
    allow_dirty: bool = False
    strip_coauthor_trailers: bool = True


@dataclass
class RewriteResult:
    backup_ref: str
    commits_rewritten: int
    coauthor_trailers_removed: int
    success: bool


@dataclass
class VerificationResult:
    source_author_before: int
    source_author_after: int
    source_committer_before: int
    source_committer_after: int
    target_author_after: int
    target_committer_after: int
    coauthor_trailers_after: int
    passed: bool


@dataclass
class PushResult:
    success: bool
    rejected: bool
    message: str
