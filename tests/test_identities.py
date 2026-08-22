import pytest

from git_reattribute.errors import MissingGitIdentityError
from git_reattribute.gitwrapper import run_git
from git_reattribute.identities import current_git_identity, resolve_target_identity
from git_reattribute.models import Identity


def test_current_git_identity(basic_repo):
    identity = current_git_identity(basic_repo)
    assert identity == Identity(name="Alice", email="alice@example.com")


def test_current_git_identity_missing(basic_repo):
    run_git(["config", "--unset", "user.name"], cwd=basic_repo)
    with pytest.raises(MissingGitIdentityError):
        current_git_identity(basic_repo)


def test_resolve_target_identity_current_user(basic_repo):
    identity = resolve_target_identity(basic_repo, to_current_user=True)
    assert identity == Identity(name="Alice", email="alice@example.com")


def test_resolve_target_identity_custom(basic_repo):
    identity = resolve_target_identity(basic_repo, to_name="Bob", to_email="bob@example.com")
    assert identity == Identity(name="Bob", email="bob@example.com")


def test_resolve_target_identity_missing_args(basic_repo):
    with pytest.raises(ValueError):
        resolve_target_identity(basic_repo)
