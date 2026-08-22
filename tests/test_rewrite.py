import pytest

from git_reattribute.contributors import discover_contributors
from git_reattribute.errors import DirtyWorkingTreeError, IdentityNotFoundError
from git_reattribute.gitwrapper import run_git
from git_reattribute.models import Identity, IdentityType, RewriteOptions
from git_reattribute.rewrite import RewriteEngine, has_signed_commits

CLAUDE = Identity("Claude", "claude@example.com")
ALICE = Identity("Alice", "alice@example.com")


def _log_messages(repo, branch="main"):
    result = run_git(["log", branch, "--format=%B---END---"], cwd=repo)
    return result.stdout


def test_replace_identity_both(basic_repo):
    engine = RewriteEngine(basic_repo)
    result = engine.replace_identity(
        RewriteOptions(branch="main", source=CLAUDE, target=ALICE, identity_type=IdentityType.BOTH)
    )
    assert result.success
    assert result.backup_ref.startswith("refs/backup/git-reattribute/")

    contributors = discover_contributors(basic_repo, "main")
    by_email = {c.email: c for c in contributors}
    assert "claude@example.com" not in by_email
    assert by_email["alice@example.com"].author_commits == 3  # A, D, plus original B
    assert by_email["alice@example.com"].committer_commits == 3  # A, plus original B, D


def test_replace_identity_author_only(basic_repo):
    engine = RewriteEngine(basic_repo)
    engine.replace_identity(
        RewriteOptions(
            branch="main", source=CLAUDE, target=ALICE, identity_type=IdentityType.AUTHOR
        )
    )
    contributors = discover_contributors(basic_repo, "main")
    by_email = {c.email: c for c in contributors}
    # Claude was committer on commit A; that role is untouched.
    assert by_email["claude@example.com"].author_commits == 0
    assert by_email["claude@example.com"].committer_commits == 1


def test_replace_identity_committer_only(basic_repo):
    engine = RewriteEngine(basic_repo)
    engine.replace_identity(
        RewriteOptions(
            branch="main", source=CLAUDE, target=ALICE, identity_type=IdentityType.COMMITTER
        )
    )
    contributors = discover_contributors(basic_repo, "main")
    by_email = {c.email: c for c in contributors}
    # Claude was author on commits A and D; that role is untouched.
    assert by_email["claude@example.com"].author_commits == 2
    assert by_email["claude@example.com"].committer_commits == 0


def test_replace_identity_source_not_present(basic_repo):
    ghost = Identity("Ghost", "ghost@example.com")
    engine = RewriteEngine(basic_repo)
    with pytest.raises(IdentityNotFoundError):
        engine.replace_identity(
            RewriteOptions(branch="main", source=ghost, target=ALICE)
        )


def test_replace_identity_refuses_dirty_tree(basic_repo):
    (basic_repo / "dirty.txt").write_text("uncommitted")
    engine = RewriteEngine(basic_repo)
    with pytest.raises(DirtyWorkingTreeError):
        engine.replace_identity(
            RewriteOptions(branch="main", source=CLAUDE, target=ALICE)
        )


def test_replace_identity_allow_dirty_proceeds(basic_repo):
    (basic_repo / "dirty.txt").write_text("uncommitted")
    engine = RewriteEngine(basic_repo)
    result = engine.replace_identity(
        RewriteOptions(branch="main", source=CLAUDE, target=ALICE, allow_dirty=True)
    )
    assert result.success


def test_coauthor_trailer_stripped(basic_repo):
    before = _log_messages(basic_repo)
    assert "Co-authored-by: Claude <claude@example.com>" in before

    engine = RewriteEngine(basic_repo)
    result = engine.replace_identity(
        RewriteOptions(
            branch="main", source=CLAUDE, target=ALICE, strip_coauthor_trailers=True
        )
    )
    assert result.coauthor_trailers_removed == 1

    after = _log_messages(basic_repo)
    assert "Co-authored-by: Claude" not in after
    # Unrelated trailer must be preserved untouched.
    assert "Signed-off-by: Alice <alice@example.com>" in after


def test_coauthor_trailer_kept_when_disabled(basic_repo):
    engine = RewriteEngine(basic_repo)
    result = engine.replace_identity(
        RewriteOptions(
            branch="main", source=CLAUDE, target=ALICE, strip_coauthor_trailers=False
        )
    )
    assert result.coauthor_trailers_removed == 0
    after = _log_messages(basic_repo)
    assert "Co-authored-by: Claude <claude@example.com>" in after


def test_has_signed_commits_false(basic_repo):
    assert has_signed_commits(basic_repo, "main") is False


def test_backup_ref_points_to_original_tip(basic_repo):
    original_tip = run_git(["rev-parse", "main"], cwd=basic_repo).stdout.strip()
    engine = RewriteEngine(basic_repo)
    result = engine.replace_identity(
        RewriteOptions(branch="main", source=CLAUDE, target=ALICE)
    )
    backup_tip = run_git(["rev-parse", result.backup_ref], cwd=basic_repo).stdout.strip()
    assert backup_tip == original_tip
