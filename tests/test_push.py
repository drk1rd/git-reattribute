from git_reattribute.gitwrapper import run_git
from git_reattribute.push import push_with_lease


def test_push_with_lease_success(basic_repo, bare_remote):
    run_git(["remote", "add", "origin", str(bare_remote)], cwd=basic_repo)
    run_git(["push", "origin", "main"], cwd=basic_repo)

    run_git(["commit", "--allow-empty", "-m", "another commit"], cwd=basic_repo)

    result = push_with_lease(basic_repo, "origin", "main")
    assert result.success
    assert not result.rejected


def test_push_with_lease_rejected_when_remote_moved(basic_repo, bare_remote, tmp_path):
    run_git(["remote", "add", "origin", str(bare_remote)], cwd=basic_repo)
    run_git(["push", "origin", "main"], cwd=basic_repo)

    other_clone = tmp_path / "other_clone"
    run_git(["clone", str(bare_remote), str(other_clone)])
    run_git(["config", "user.name", "Bob"], cwd=other_clone)
    run_git(["config", "user.email", "bob@example.com"], cwd=other_clone)
    run_git(["commit", "--allow-empty", "-m", "concurrent commit"], cwd=other_clone)
    run_git(["push", "origin", "main"], cwd=other_clone)

    run_git(["commit", "--allow-empty", "-m", "local diverging commit"], cwd=basic_repo)

    result = push_with_lease(basic_repo, "origin", "main")
    assert not result.success
    assert result.rejected
