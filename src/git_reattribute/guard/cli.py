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


_CONFIG_TEMPLATE_EMPTY = """\
# git-reattribute-guard config
# https://github.com/drk1rd/git-reattribute#guard-prevent-denied-identities-before-they-land
#
# Add identities to deny below, e.g.:
#
# deny:
#   - name: Claude
#     email: claude@example.com
#   - email: "*@bots.example.com"   # glob supported on email only
#
deny: []
check_coauthors: true
"""

_WORKFLOW_TEMPLATE = """\
name: Guard commit identities
on: [pull_request]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: drk1rd/git-reattribute/.github/actions/guard@v1
"""

_PRE_COMMIT_SNIPPET = """\
repos:
  - repo: local
    hooks:
      - id: git-reattribute-guard
        name: git-reattribute-guard
        entry: git-reattribute guard check-local
        language: system
        stages: [commit-msg]"""

_DEFAULT_WORKFLOW_PATH = Path(".github/workflows/guard.yml")


def _config_template(deny_name: Optional[str], deny_email: Optional[str]) -> str:
    if not deny_name and not deny_email:
        return _CONFIG_TEMPLATE_EMPTY

    entry_lines = ["deny:", "  -"]
    if deny_name:
        entry_lines.append(f"    name: {deny_name}")
    if deny_email:
        entry_lines.append(f"    email: {deny_email}")
    entry = "\n".join(entry_lines)
    return (
        "# git-reattribute-guard config\n"
        "# https://github.com/drk1rd/git-reattribute"
        "#guard-prevent-denied-identities-before-they-land\n"
        f"{entry}\n"
        "check_coauthors: true\n"
    )


def _write_if_absent(path: Path, content: str, force: bool) -> tuple[bool, str]:
    """Returns (written, message)."""
    if path.exists() and not force:
        return False, f"skipped (already exists): {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True, f"wrote: {path}"


@guard_app.command()
def init(
    deny_name: Optional[str] = typer.Option(
        None, "--deny-name", help="Name of an identity to deny immediately (with --deny-email)."
    ),
    deny_email: Optional[str] = typer.Option(
        None, "--deny-email", help="Email of an identity to deny immediately."
    ),
    config_path: Path = typer.Option(
        Path(DEFAULT_CONFIG_NAME), "--config", help="Where to write the guard config file."
    ),
    workflow_path: Path = typer.Option(
        _DEFAULT_WORKFLOW_PATH, "--workflow-path", help="Where to write the GitHub Actions workflow."
    ),
    no_workflow: bool = typer.Option(
        False, "--no-workflow", help="Skip writing the GitHub Actions workflow file."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite files that already exist."
    ),
) -> None:
    """Scaffold guard's config, GitHub Action workflow, and pre-commit snippet in one shot."""
    written, message = _write_if_absent(
        config_path, _config_template(deny_name, deny_email), force
    )
    typer.echo(message)

    if not no_workflow:
        written_wf, message_wf = _write_if_absent(workflow_path, _WORKFLOW_TEMPLATE, force)
        typer.echo(message_wf)

    typer.echo(
        "\nTo also block a denied identity locally before it's committed, add this to "
        ".pre-commit-config.yaml and run `pre-commit install --hook-type commit-msg`:\n"
    )
    typer.echo(_PRE_COMMIT_SNIPPET)
    typer.echo(
        "\n(Not written automatically — merging into an existing "
        ".pre-commit-config.yaml safely needs a human, not a blind overwrite.)"
    )
