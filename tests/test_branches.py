from git_reattribute.branches import branch_exists, list_local_branches, upstream_of
from git_reattribute.gitwrapper import run_git


def test_list_local_branches(basic_repo):
    run_git(["branch", "develop"], cwd=basic_repo)
    branches = {b.name for b in list_local_branches(basic_repo)}
    assert branches == {"main", "develop"}


def test_branch_exists(basic_repo):
    assert branch_exists(basic_repo, "main")
    assert not branch_exists(basic_repo, "nonexistent")


def test_upstream_of_no_upstream(basic_repo):
    assert upstream_of(basic_repo, "main") is None
