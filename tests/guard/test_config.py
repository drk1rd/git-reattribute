import pytest

from git_reattribute.guard.config import load_config
from git_reattribute.guard.errors import ConfigInvalidError, ConfigNotFoundError


def test_load_config_basic(tmp_path):
    cfg_path = tmp_path / ".git-reattribute-guard.yml"
    cfg_path.write_text(
        "deny:\n"
        "  - name: Claude\n"
        "    email: claude@example.com\n"
        "  - email: '*@bots.example.com'\n"
        "check_coauthors: false\n"
    )
    config = load_config(cfg_path)
    assert len(config.deny) == 2
    assert config.check_coauthors is False
    assert config.deny[0].name == "Claude"
    assert config.deny[0].email == "claude@example.com"


def test_load_config_default_check_coauthors(tmp_path):
    cfg_path = tmp_path / ".git-reattribute-guard.yml"
    cfg_path.write_text("deny:\n  - email: bot@example.com\n")
    config = load_config(cfg_path)
    assert config.check_coauthors is True


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigNotFoundError):
        load_config(tmp_path / "nope.yml")


def test_load_config_not_a_mapping(tmp_path):
    cfg_path = tmp_path / ".git-reattribute-guard.yml"
    cfg_path.write_text("- just\n- a\n- list\n")
    with pytest.raises(ConfigInvalidError):
        load_config(cfg_path)


def test_load_config_deny_entry_missing_fields(tmp_path):
    cfg_path = tmp_path / ".git-reattribute-guard.yml"
    cfg_path.write_text("deny:\n  - not_name_or_email: oops\n")
    with pytest.raises(ConfigInvalidError):
        load_config(cfg_path)


def test_load_config_deny_not_a_list(tmp_path):
    cfg_path = tmp_path / ".git-reattribute-guard.yml"
    cfg_path.write_text("deny: nope\n")
    with pytest.raises(ConfigInvalidError):
        load_config(cfg_path)
