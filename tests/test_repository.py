from pathlib import Path

import pytest

from git_reattribute.errors import NotAGitRepositoryError
from git_reattribute.repository import (
    current_branch,
    find_repo_root,
    is_clean_working_tree,
    is_shallow_repository,
    list_remotes,
)


def test_find_repo_root(basic_repo):
    root = find_repo_root(basic_repo)
    assert root == basic_repo.resolve()


def test_find_repo_root_not_a_repo(tmp_path):
    not_repo = tmp_path / "plain"
    not_repo.mkdir()
    with pytest.raises(NotAGitRepositoryError):
        find_repo_root(not_repo)


def test_current_branch(basic_repo):
    assert current_branch(basic_repo) == "main"


def test_clean_working_tree(basic_repo):
    clean, modified = is_clean_working_tree(basic_repo)
    assert clean
    assert modified == []


def test_dirty_working_tree(basic_repo):
    (basic_repo / "new_file.txt").write_text("hello")
    clean, modified = is_clean_working_tree(basic_repo)
    assert not clean
    assert "new_file.txt" in modified[0]


def test_list_remotes_empty(basic_repo):
    assert list_remotes(basic_repo) == []


def test_is_shallow_repository_false(basic_repo):
    assert is_shallow_repository(basic_repo) is False
