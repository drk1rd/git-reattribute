from typer.testing import CliRunner

from git_reattribute.cli import app

runner = CliRunner()


def test_init_writes_empty_template_when_no_deny_given(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["guard", "init"])
    assert result.exit_code == 0

    config = (tmp_path / ".git-reattribute-guard.yml").read_text()
    assert "deny: []" in config
    assert "check_coauthors: true" in config

    workflow = (tmp_path / ".github/workflows/guard.yml").read_text()
    assert "drk1rd/git-reattribute/.github/actions/guard@v1" in workflow
    assert "pull_request" in workflow

    assert "pre-commit-config.yaml" in result.stdout
    assert "repo: local" in result.stdout


def test_init_writes_real_deny_entry_when_given(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app, ["guard", "init", "--deny-name", "Claude", "--deny-email", "claude@example.com"]
    )
    assert result.exit_code == 0

    config = (tmp_path / ".git-reattribute-guard.yml").read_text()
    assert "name: Claude" in config
    assert "email: claude@example.com" in config
    # should not fall back to the commented-out empty template
    assert "deny: []" not in config

    # the generated config should actually be valid and loadable
    from git_reattribute.guard.config import load_config

    loaded = load_config(tmp_path / ".git-reattribute-guard.yml")
    assert len(loaded.deny) == 1
    assert loaded.deny[0].name == "Claude"
    assert loaded.deny[0].email == "claude@example.com"


def test_init_no_workflow_flag_skips_workflow_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["guard", "init", "--no-workflow"])
    assert result.exit_code == 0
    assert not (tmp_path / ".github/workflows/guard.yml").exists()


def test_init_skips_existing_files_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / ".git-reattribute-guard.yml"
    config_path.write_text("deny:\n  - email: existing@example.com\n")

    result = runner.invoke(app, ["guard", "init"])
    assert result.exit_code == 0
    assert "skipped" in result.stdout
    # original content untouched
    assert "existing@example.com" in config_path.read_text()


def test_init_force_overwrites_existing_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / ".git-reattribute-guard.yml"
    config_path.write_text("deny:\n  - email: existing@example.com\n")

    result = runner.invoke(app, ["guard", "init", "--force"])
    assert result.exit_code == 0
    assert "existing@example.com" not in config_path.read_text()
    assert "deny: []" in config_path.read_text()


def test_init_generated_config_is_valid_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["guard", "init"])

    import yaml

    with open(tmp_path / ".git-reattribute-guard.yml") as f:
        parsed = yaml.safe_load(f)
    assert parsed["deny"] == []
    assert parsed["check_coauthors"] is True


def test_init_custom_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "guard",
            "init",
            "--config",
            "custom-guard.yml",
            "--workflow-path",
            ".github/workflows/custom.yml",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "custom-guard.yml").exists()
    assert (tmp_path / ".github/workflows/custom.yml").exists()
