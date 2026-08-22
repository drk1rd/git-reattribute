from __future__ import annotations

from pathlib import Path

import yaml

from git_reattribute.guard.errors import ConfigInvalidError, ConfigNotFoundError
from git_reattribute.guard.models import DenyEntry

DEFAULT_CONFIG_NAME = ".git-reattribute-guard.yml"


class Config:
    def __init__(self, deny: list[DenyEntry], check_coauthors: bool = True) -> None:
        self.deny = deny
        self.check_coauthors = check_coauthors


def load_config(path: Path) -> Config:
    if not path.exists():
        raise ConfigNotFoundError(str(path))

    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ConfigInvalidError(str(exc)) from exc

    if not isinstance(raw, dict):
        raise ConfigInvalidError("top-level config must be a mapping")

    deny_raw = raw.get("deny", [])
    if not isinstance(deny_raw, list):
        raise ConfigInvalidError("`deny` must be a list")

    deny: list[DenyEntry] = []
    for i, entry in enumerate(deny_raw):
        if not isinstance(entry, dict):
            raise ConfigInvalidError(f"`deny[{i}]` must be a mapping with `name` and/or `email`")
        name = entry.get("name")
        email = entry.get("email")
        if name is None and email is None:
            raise ConfigInvalidError(f"`deny[{i}]` must specify `name` and/or `email`")
        deny.append(DenyEntry(name=name, email=email))

    check_coauthors = raw.get("check_coauthors", True)
    if not isinstance(check_coauthors, bool):
        raise ConfigInvalidError("`check_coauthors` must be a boolean")

    return Config(deny=deny, check_coauthors=check_coauthors)
