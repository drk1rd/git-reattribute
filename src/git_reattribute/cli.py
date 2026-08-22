from __future__ import annotations

from pathlib import Path
from typing import Optional

import questionary
import typer

from git_reattribute import __version__
from git_reattribute.branches import list_local_branches
from git_reattribute.contributors import discover_contributors
from git_reattribute.errors import GitReattributeError
from git_reattribute.gitwrapper import check_git_version
from git_reattribute.guard.cli import guard_app
from git_reattribute.identities import current_git_identity, resolve_target_identity
from git_reattribute.models import Identity, IdentityType, RewriteOptions
from git_reattribute.push import push_with_lease
from git_reattribute.repository import (
    current_branch,
    find_repo_root,
    is_clean_working_tree,
    is_shallow_repository,
    list_remotes,
)
from git_reattribute.rewrite import RewriteEngine, has_signed_commits
from git_reattribute.verify import verify_rewrite

app = typer.Typer(add_completion=False, no_args_is_help=False)
app.add_typer(guard_app, name="guard")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"git-reattribute {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    branch: Optional[str] = typer.Option(None, "--branch", help="Branch to operate on."),
    from_name: Optional[str] = typer.Option(None, "--from-name"),
    from_email: Optional[str] = typer.Option(None, "--from-email"),
    to_name: Optional[str] = typer.Option(None, "--to-name"),
    to_email: Optional[str] = typer.Option(None, "--to-email"),
    to_current_user: bool = typer.Option(False, "--to-current-user"),
    identity_type: IdentityType = typer.Option(IdentityType.BOTH, "--identity-type"),
    push: bool = typer.Option(False, "--push"),
    no_push: bool = typer.Option(False, "--no-push"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes"),
    allow_dirty: bool = typer.Option(False, "--allow-dirty"),
    strip_coauthor_trailers: bool = typer.Option(
        True, "--strip-coauthor-trailers/--no-strip-coauthor-trailers"
    ),
    verbose: bool = typer.Option(False, "--verbose"),
    quiet: bool = typer.Option(False, "--quiet"),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True
    ),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    run(
        branch=branch,
        from_name=from_name,
        from_email=from_email,
        to_name=to_name,
        to_email=to_email,
        to_current_user=to_current_user,
        identity_type=identity_type,
        push=push,
        no_push=no_push,
        dry_run=dry_run,
        yes=yes,
        allow_dirty=allow_dirty,
        strip_coauthor_trailers=strip_coauthor_trailers,
        verbose=verbose,
        quiet=quiet,
    )


def _echo(quiet: bool, message: str = "") -> None:
    if not quiet:
        typer.echo(message)


def run(
    branch: Optional[str],
    from_name: Optional[str],
    from_email: Optional[str],
    to_name: Optional[str],
    to_email: Optional[str],
    to_current_user: bool,
    identity_type: IdentityType,
    push: bool,
    no_push: bool,
    dry_run: bool,
    yes: bool,
    allow_dirty: bool,
    strip_coauthor_trailers: bool,
    verbose: bool,
    quiet: bool,
) -> None:
    try:
        check_git_version()
        repo_root = find_repo_root()

        _echo(quiet, "Git Reattribute\n")
        _echo(quiet, f"Repository: {repo_root}")
        remotes = list_remotes(repo_root)
        _echo(quiet, f"Remote:    {remotes[0] if remotes else '(none)'}")
        active_branch = current_branch(repo_root)
        _echo(quiet, f"Branch:    {active_branch or '(detached HEAD)'}\n")

        if is_shallow_repository(repo_root):
            _echo(
                quiet,
                "This repository is shallow.\n\n"
                "For a complete history rewrite, fetch the full history first.\n\n"
                "Suggested command:\n\n  git fetch --unshallow\n",
            )

        selected_branch = branch or _select_branch(repo_root, active_branch, quiet)

        contributors = discover_contributors(repo_root, selected_branch)
        if not quiet:
            _echo(quiet, f"Contributors on {selected_branch}:\n")
            for i, c in enumerate(contributors, start=1):
                _echo(quiet, f"  {i}. {c.name} <{c.email}>    {c.total_commits} commits")
            _echo(quiet)

        source = _resolve_source(contributors, from_name, from_email, selected_branch, quiet)
        target = _resolve_target(repo_root, contributors, to_current_user, to_name, to_email, quiet)

        if source == target:
            typer.echo("Error: source and target identities are identical; nothing to do.")
            raise typer.Exit(code=1)

        source_contributor = next(
            (c for c in contributors if c.name == source.name and c.email == source.email), None
        )
        author_count = source_contributor.author_commits if source_contributor else 0
        committer_count = source_contributor.committer_commits if source_contributor else 0
        coauthor_count = source_contributor.coauthor_commits if source_contributor else 0

        _echo(quiet, "Summary")
        _echo(quiet, "-------")
        _echo(quiet, f"Branch:       {selected_branch}")
        _echo(quiet, f"From:         {source}")
        _echo(quiet, f"To:           {target}")
        _echo(quiet, f"Author commits affected:    {author_count}")
        _echo(quiet, f"Committer commits affected: {committer_count}")
        if strip_coauthor_trailers:
            _echo(quiet, f"Co-authored-by trailers to remove: {coauthor_count}")
        _echo(quiet)

        if has_signed_commits(repo_root, selected_branch):
            _echo(
                quiet,
                "Warning:\nThis history contains signed commits.\n\n"
                "Rewriting commits creates new commit objects and invalidates\n"
                "existing signatures on rewritten commits.\n",
            )

        if dry_run:
            _echo(quiet, "DRY RUN\n")
            _echo(quiet, "No history was changed.")
            _echo(quiet, "No remote was modified.")
            return

        _echo(quiet, "WARNING: This operation rewrites Git history.\n")
        _echo(
            quiet,
            "The branch will need to be force-pushed if it has already\nbeen published.\n",
        )

        if not yes:
            answer = typer.prompt("Type REWRITE to continue")
            if answer.strip() != "REWRITE":
                typer.echo("Aborted: confirmation not given.")
                raise typer.Exit(code=1)

        engine = RewriteEngine(repo_root)
        options = RewriteOptions(
            branch=selected_branch,
            source=source,
            target=target,
            identity_type=identity_type,
            allow_dirty=allow_dirty,
            strip_coauthor_trailers=strip_coauthor_trailers,
        )
        result = engine.replace_identity(options)

        _echo(quiet, "\nHistory rewrite completed.\n")
        _echo(quiet, f"Recovery reference:\n  {result.backup_ref}\n")
        _echo(quiet, f"To restore the original branch:\n  git reset --hard {result.backup_ref}\n")
        _echo(quiet, "Keep this reference until you have verified the rewritten history.\n")

        verification = verify_rewrite(
            repo_root, selected_branch, source, target, identity_type, contributors
        )
        _echo(quiet, "Verification\n")
        _echo(quiet, f"  Old identity commits before: {author_count + committer_count}")
        _echo(
            quiet,
            f"  Remaining old identity commits: "
            f"{verification.source_author_after + verification.source_committer_after}",
        )
        _echo(quiet, f"  New identity commits: {verification.target_author_after}")
        if strip_coauthor_trailers:
            _echo(
                quiet,
                f"  Remaining Co-authored-by trailers: {verification.coauthor_trailers_after}",
            )
        _echo(quiet, f"\nVerification: {'PASS' if verification.passed else 'FAIL'}")

        if no_push:
            return

        if not remotes:
            return

        remote = remotes[0]
        should_push = push
        if not push and not yes:
            should_push = typer.confirm(
                f"\nPush rewritten branch to {remote} with --force-with-lease?", default=False
            )
        elif not push and yes:
            should_push = False

        if should_push:
            push_result = push_with_lease(repo_root, remote, selected_branch)
            if push_result.success:
                _echo(quiet, "\nPush succeeded.")
            else:
                _echo(quiet, f"\n{push_result.message}")
                raise typer.Exit(code=1)

    except GitReattributeError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)


def _select_branch(repo_root: Path, active_branch: Optional[str], quiet: bool) -> str:
    branches = list_local_branches(repo_root)
    names = [b.name for b in branches]
    if not names:
        typer.echo("Error: no local branches found in this repository.")
        raise typer.Exit(code=1)
    default = active_branch if active_branch in names else names[0]
    choice = questionary.select("Select branch:", choices=names, default=default).ask()
    if choice is None:
        raise typer.Exit(code=1)
    return choice


def _resolve_source(
    contributors, from_name: Optional[str], from_email: Optional[str], branch: str, quiet: bool
) -> Identity:
    if from_email:
        if from_name:
            return Identity(name=from_name, email=from_email)
        match = next((c for c in contributors if c.email == from_email), None)
        if match:
            return match.identity
        # Not among discovered contributors; rewrite() will raise
        # IdentityNotFoundError once it re-checks against actual history.
        return Identity(name=from_email, email=from_email)
    labels = [f"{c.name} <{c.email}>    {c.total_commits} commits" for c in contributors]
    if not labels:
        typer.echo(f"Error: no contributors found on branch {branch}.")
        raise typer.Exit(code=1)
    choice = questionary.select("Select contributor to replace:", choices=labels).ask()
    if choice is None:
        raise typer.Exit(code=1)
    index = labels.index(choice)
    return contributors[index].identity


def _resolve_target(
    repo_root: Path,
    contributors,
    to_current_user: bool,
    to_name: Optional[str],
    to_email: Optional[str],
    quiet: bool,
) -> Identity:
    if to_current_user or (to_name and to_email):
        return resolve_target_identity(
            repo_root, to_current_user=to_current_user, to_name=to_name, to_email=to_email
        )

    options = ["Current Git identity"]
    options += [f"{c.name} <{c.email}>" for c in contributors]
    options += ["Enter a custom identity"]
    choice = questionary.select("Replace with:", choices=options).ask()
    if choice is None:
        raise typer.Exit(code=1)

    if choice == "Current Git identity":
        return current_git_identity(repo_root)
    if choice == "Enter a custom identity":
        name = questionary.text("Name:").ask()
        email = questionary.text("Email:").ask()
        if not name or not email:
            raise typer.Exit(code=1)
        return Identity(name=name, email=email)

    index = options.index(choice) - 1
    return contributors[index].identity


if __name__ == "__main__":
    app()
