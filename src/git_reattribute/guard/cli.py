from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer

from git_reattribute.guard.config import DEFAULT_CONFIG_NAME, load_config
from git_reattribute.guard.errors import GuardError
from git_reattribute.guard.models import Role
from git_reattribute.guard.scan import coauthors_in_body, scan_range

guard_app = typer.Typer(
    add_completion=False,
    help="Prevent denied Git identities before they're committed or merged.",
)

ROLE_LABEL = {
    Role.AUTHOR: "author",
    Role.COMMITTER: "committer",
    Role.COAUTHOR: "Co-authored-by trailer",
}


@guard_app.command()
def check(
    base: str = typer.Option(..., "--base", help="Base ref/commit (exclusive)."),
    head: str = typer.Option("HEAD", "--head", help="Head ref/commit (inclusive)."),
    config_path: Path = typer.Option(
        Path(DEFAULT_CONFIG_NAME), "--config", help="Path to the guard config file."
    ),
    branch: Optional[str] = typer.Option(
        None, "--branch", help="Branch name to use in suggested fix commands (defaults to --head)."
    ),
) -> None:
    """Check a commit range (e.g. in CI) for denied identities."""
    try:
        config = load_config(config_path)
        commit_range = f"{base}..{head}"
        violations = scan_range(Path.cwd(), commit_range, config)

        if not violations:
            typer.echo(f"git-reattribute guard: no denied identities found in {commit_range}.")
            raise typer.Exit(code=0)

        fix_branch = branch or head
        typer.echo(f"git-reattribute guard: found {len(violations)} violation(s) in {commit_range}:\n")
        for v in violations:
            short_sha = v.commit_sha[:8]
            typer.echo(f"  {short_sha}  {ROLE_LABEL[v.role]}: {v.name} <{v.email}>")
        typer.echo("\nFix with:")
        seen = set()
        for v in violations:
            cmd = v.fix_command_hint(fix_branch)
            if cmd not in seen:
                seen.add(cmd)
                typer.echo(f"  {cmd}")
        raise typer.Exit(code=1)

    except GuardError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)


def _git_config_identity() -> tuple[str, str]:
    name = subprocess.run(["git", "config", "user.name"], text=True, capture_output=True).stdout.strip()
    email = subprocess.run(["git", "config", "user.email"], text=True, capture_output=True).stdout.strip()
    return name, email


@guard_app.command("check-local")
def check_local(
    message_file: Path = typer.Argument(
        ..., help="Path to the commit message file (passed by pre-commit's commit-msg stage)."
    ),
    config_path: Path = typer.Option(
        Path(DEFAULT_CONFIG_NAME), "--config", help="Path to the guard config file."
    ),
) -> None:
    """Check the commit about to be made (for a local pre-commit commit-msg hook).

    Intended for a `repo: local` entry in a consumer's .pre-commit-config.yaml:

        repos:
          - repo: local
            hooks:
              - id: git-reattribute-guard
                name: git-reattribute-guard
                entry: git-reattribute guard check-local
                language: system
                stages: [commit-msg]
    """
    try:
        config = load_config(config_path)
    except GuardError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    name, email = _git_config_identity()
    violations = []
    for entry in config.deny:
        if entry.matches(name, email):
            violations.append((Role.AUTHOR, name, email))
            violations.append((Role.COMMITTER, name, email))

    if config.check_coauthors and message_file.exists():
        body = message_file.read_text()
        for coauthor_name, coauthor_email in coauthors_in_body(body):
            for entry in config.deny:
                if entry.matches(coauthor_name, coauthor_email):
                    violations.append((Role.COAUTHOR, coauthor_name, coauthor_email))

    if not violations:
        raise typer.Exit(code=0)

    typer.echo("git-reattribute guard: blocked commit — denied identity detected:\n")
    for role, vname, vemail in violations:
        typer.echo(f"  {ROLE_LABEL[role]}: {vname} <{vemail}>")
    typer.echo(
        "\nThis identity is on the denylist in .git-reattribute-guard.yml. "
        "Fix your git config or the Co-authored-by trailer before committing."
    )
    raise typer.Exit(code=1)
