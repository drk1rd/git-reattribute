import pytest

from git_reattribute.guard.config import Config
from git_reattribute.guard.errors import InvalidRangeError
from git_reattribute.guard.models import DenyEntry, Role
from git_reattribute.guard.scan import scan_range


def test_scan_range_no_violations(repo_with_root):
    config = Config(deny=[DenyEntry(name="Ghost", email="ghost@example.com")])
    violations = scan_range(repo_with_root, "HEAD~4..HEAD", config)
    assert violations == []


def test_scan_range_author_violation(repo_with_root):
    config = Config(deny=[DenyEntry(name="Claude", email="claude@example.com")])
    violations = scan_range(repo_with_root, "HEAD~4..HEAD", config)
    roles = {v.role for v in violations}
    assert Role.AUTHOR in roles
    assert Role.COMMITTER in roles  # commit A: Claude is both author and committer


def test_scan_range_coauthor_violation(repo_with_root):
    config = Config(deny=[DenyEntry(name="Claude", email="claude@example.com")], check_coauthors=True)
    violations = scan_range(repo_with_root, "HEAD~1..HEAD", config)
    assert any(v.role == Role.COAUTHOR for v in violations)


def test_scan_range_coauthor_disabled(repo_with_root):
    config = Config(deny=[DenyEntry(name="Claude", email="claude@example.com")], check_coauthors=False)
    violations = scan_range(repo_with_root, "HEAD~1..HEAD", config)
    assert not any(v.role == Role.COAUTHOR for v in violations)


def test_scan_range_email_glob(repo_with_root):
    config = Config(deny=[DenyEntry(name=None, email="*@example.com")])
    violations = scan_range(repo_with_root, "HEAD~4..HEAD", config)
    assert len(violations) > 0


def test_scan_range_invalid_range(repo_with_root):
    config = Config(deny=[])
    with pytest.raises(InvalidRangeError):
        scan_range(repo_with_root, "not-a-ref..HEAD", config)
