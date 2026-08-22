from git_reattribute.contributors import discover_contributors
from git_reattribute.models import Identity, IdentityType, RewriteOptions
from git_reattribute.rewrite import RewriteEngine
from git_reattribute.verify import verify_rewrite

CLAUDE = Identity("Claude", "claude@example.com")
ALICE = Identity("Alice", "alice@example.com")


def test_verify_rewrite_passes(basic_repo):
    before = discover_contributors(basic_repo, "main")
    engine = RewriteEngine(basic_repo)
    engine.replace_identity(
        RewriteOptions(branch="main", source=CLAUDE, target=ALICE, identity_type=IdentityType.BOTH)
    )
    result = verify_rewrite(basic_repo, "main", CLAUDE, ALICE, IdentityType.BOTH, before)
    assert result.passed
    assert result.source_author_after == 0
    assert result.source_committer_after == 0
    assert result.coauthor_trailers_after == 0
    assert result.target_author_after == 3
    assert result.target_committer_after == 3


def test_verify_rewrite_author_only_leaves_committer(basic_repo):
    before = discover_contributors(basic_repo, "main")
    engine = RewriteEngine(basic_repo)
    engine.replace_identity(
        RewriteOptions(
            branch="main", source=CLAUDE, target=ALICE, identity_type=IdentityType.AUTHOR
        )
    )
    result = verify_rewrite(basic_repo, "main", CLAUDE, ALICE, IdentityType.AUTHOR, before)
    assert result.passed
    assert result.source_author_after == 0
