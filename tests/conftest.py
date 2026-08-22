from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

CLAUDE = ("Claude", "claude@example.com")
ALICE = ("Alice", "alice@example.com")
BOB = ("Bob", "bob@example.com")


@pytest.fixture(autouse=True)
def _isolated_git_env(tmp_path, monkeypatch):
    # Prevent the host machine's real ~/.gitconfig (which typically has
    # user.name/user.email set) from leaking into tests that rely on no
    # identity being configured.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for var in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)


def _run(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, env=env, check=True
    )
    return result


def _commit(repo: Path, message: str, author=CLAUDE, committer=None, body: str = "") -> None:
    committer = committer or author
    env = {
        "GIT_AUTHOR_NAME": author[0],
        "GIT_AUTHOR_EMAIL": author[1],
        "GIT_COMMITTER_NAME": committer[0],
        "GIT_COMMITTER_EMAIL": committer[1],
        "PATH": _os_path(),
        "HOME": str(repo),
    }
    full_message = message if not body else f"{message}\n\n{body}"
    _run(["commit", "--allow-empty", "-m", full_message], cwd=repo, env=env)


def _os_path() -> str:
    import os

    return os.environ.get("PATH", "")


@pytest.fixture
def repo_factory(tmp_path):
    def _make(name: str = "repo") -> Path:
        repo = tmp_path / name
        repo.mkdir()
        _run(["init", "-b", "main"], cwd=repo)
        _run(["config", "user.name", "Alice"], cwd=repo)
        _run(["config", "user.email", "alice@example.com"], cwd=repo)
        _run(["config", "commit.gpgsign", "false"], cwd=repo)
        return repo

    return _make


@pytest.fixture
def basic_repo(repo_factory) -> Path:
    """Builds A-B-C-D history with Claude, Alice, and Bob identities.

    A: Claude author+committer
    B: Alice author+committer
    C: Bob author+committer
    D: Claude author, Alice committer, with a Co-authored-by: Claude trailer
       and an unrelated Signed-off-by trailer.
    """
    repo = repo_factory()
    _commit(repo, "A: initial", author=CLAUDE)
    _commit(repo, "B: alice work", author=ALICE)
    _commit(repo, "C: bob work", author=BOB)
    _commit(
        repo,
        "D: mixed roles",
        author=CLAUDE,
        committer=ALICE,
        body=f"Co-authored-by: {CLAUDE[0]} <{CLAUDE[1]}>\nSigned-off-by: {ALICE[0]} <{ALICE[1]}>",
    )
    return repo


@pytest.fixture
def repo_with_root(repo_factory) -> Path:
    """root -- A -- B -- C -- D, same commits as basic_repo but with a
    leading root commit so HEAD~N ranges resolve cleanly (A has no parent
    otherwise). Used by guard tests; kept separate from basic_repo so
    existing tests' commit-index assumptions are untouched.
    """
    repo = repo_factory()
    _commit(repo, "root", author=ALICE)
    _commit(repo, "A: initial", author=CLAUDE)
    _commit(repo, "B: alice work", author=ALICE)
    _commit(repo, "C: bob work", author=BOB)
    _commit(
        repo,
        "D: mixed roles",
        author=CLAUDE,
        committer=ALICE,
        body=f"Co-authored-by: {CLAUDE[0]} <{CLAUDE[1]}>\nSigned-off-by: {ALICE[0]} <{ALICE[1]}>",
    )
    return repo


@pytest.fixture
def mailmap_repo(repo_factory) -> Path:
    repo = repo_factory()
    (repo / ".mailmap").write_text(f"{ALICE[0]} <{ALICE[1]}> <{CLAUDE[1]}>\n")
    _run(["add", ".mailmap"], cwd=repo)
    _commit(repo, "A: claude commit under mailmap", author=CLAUDE)
    return repo


@pytest.fixture
def bare_remote(tmp_path) -> Path:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _run(["init", "--bare", "-b", "main"], cwd=remote)
    return remote
