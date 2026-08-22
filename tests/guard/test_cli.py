from typer.testing import CliRunner

from git_reattribute.cli import app

runner = CliRunner()


def _write_config(repo, deny_yaml):
    (repo / ".git-reattribute-guard.yml").write_text(deny_yaml)


def test_guard_check_passes_clean_range(repo_with_root, monkeypatch):
    _write_config(repo_with_root, "deny:\n  - email: ghost@example.com\n")
    monkeypatch.chdir(repo_with_root)
    result = runner.invoke(app, ["guard", "check", "--base", "HEAD~4", "--head", "HEAD"])
    assert result.exit_code == 0
    assert "no denied identities" in result.stdout


def test_guard_check_fails_on_violation(repo_with_root, monkeypatch):
    _write_config(repo_with_root, "deny:\n  - name: Claude\n    email: claude@example.com\n")
    monkeypatch.chdir(repo_with_root)
    result = runner.invoke(
        app, ["guard", "check", "--base", "HEAD~4", "--head", "HEAD", "--branch", "main"]
    )
    assert result.exit_code == 1
    assert "violation" in result.stdout
    assert (
        "git-reattribute --branch main --from-email claude@example.com --to-current-user"
        in result.stdout
    )


def test_guard_check_missing_config(repo_with_root, monkeypatch):
    monkeypatch.chdir(repo_with_root)
    result = runner.invoke(app, ["guard", "check", "--base", "HEAD~4", "--head", "HEAD"])
    assert result.exit_code == 1
    assert "config file not found" in result.stdout


def test_guard_check_local_blocks_denied_author(repo_with_root, monkeypatch, tmp_path):
    _write_config(repo_with_root, "deny:\n  - name: Claude\n    email: claude@example.com\n")
    monkeypatch.chdir(repo_with_root)
    from git_reattribute.gitwrapper import run_git

    run_git(["config", "user.name", "Claude"], cwd=repo_with_root)
    run_git(["config", "user.email", "claude@example.com"], cwd=repo_with_root)

    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("feat: something\n")
    result = runner.invoke(app, ["guard", "check-local", str(msg_file)])
    assert result.exit_code == 1
    assert "blocked commit" in result.stdout


def test_guard_check_local_blocks_denied_coauthor_trailer(repo_with_root, monkeypatch, tmp_path):
    _write_config(repo_with_root, "deny:\n  - name: Claude\n    email: claude@example.com\n")
    monkeypatch.chdir(repo_with_root)
    from git_reattribute.gitwrapper import run_git

    run_git(["config", "user.name", "Alice"], cwd=repo_with_root)
    run_git(["config", "user.email", "alice@example.com"], cwd=repo_with_root)

    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("feat: something\n\nCo-authored-by: Claude <claude@example.com>\n")
    result = runner.invoke(app, ["guard", "check-local", str(msg_file)])
    assert result.exit_code == 1
    assert "Co-authored-by trailer" in result.stdout


def test_guard_check_local_passes_clean(repo_with_root, monkeypatch, tmp_path):
    _write_config(repo_with_root, "deny:\n  - name: Claude\n    email: claude@example.com\n")
    monkeypatch.chdir(repo_with_root)
    from git_reattribute.gitwrapper import run_git

    run_git(["config", "user.name", "Alice"], cwd=repo_with_root)
    run_git(["config", "user.email", "alice@example.com"], cwd=repo_with_root)

    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("feat: something clean\n")
    result = runner.invoke(app, ["guard", "check-local", str(msg_file)])
    assert result.exit_code == 0
