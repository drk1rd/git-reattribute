from git_reattribute.contributors import discover_contributors


def test_discover_contributors_counts(basic_repo):
    contributors = discover_contributors(basic_repo, "main")
    by_email = {c.email: c for c in contributors}

    assert by_email["claude@example.com"].author_commits == 2  # A and D
    assert by_email["claude@example.com"].committer_commits == 1  # A only
    assert by_email["alice@example.com"].author_commits == 1  # B
    assert by_email["alice@example.com"].committer_commits == 2  # B, D
    assert by_email["bob@example.com"].author_commits == 1
    assert by_email["bob@example.com"].committer_commits == 1


def test_discover_contributors_coauthor_trailer(basic_repo):
    contributors = discover_contributors(basic_repo, "main")
    by_email = {c.email: c for c in contributors}
    assert by_email["claude@example.com"].coauthor_commits == 1
    assert by_email["alice@example.com"].coauthor_commits == 0


def test_discover_contributors_sorted_by_commit_count(basic_repo):
    contributors = discover_contributors(basic_repo, "main")
    counts = [c.total_commits for c in contributors]
    assert counts == sorted(counts, reverse=True)


def test_discover_contributors_ignores_mailmap(mailmap_repo):
    contributors = discover_contributors(mailmap_repo, "main")
    emails = {c.email for c in contributors}
    # Raw fields must show the Claude identity as committed, unresolved by
    # .mailmap (which would otherwise remap it to Alice).
    assert "claude@example.com" in emails
    assert emails == {"claude@example.com"}


def test_discover_contributors_unknown_branch(basic_repo):
    import pytest

    from git_reattribute.errors import BranchNotFoundError

    with pytest.raises(BranchNotFoundError):
        discover_contributors(basic_repo, "does-not-exist")
