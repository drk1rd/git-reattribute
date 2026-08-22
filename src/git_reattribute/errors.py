class GitReattributeError(Exception):
    """Base class for all git-reattribute errors with a human-readable message."""


class NotAGitRepositoryError(GitReattributeError):
    def __init__(self) -> None:
        super().__init__(
            "Error: this directory is not a Git repository.\n\n"
            "Run the command from inside a Git repository."
        )


class DirtyWorkingTreeError(GitReattributeError):
    def __init__(self, modified_files: list[str]) -> None:
        files = "\n".join(f"  {f}" for f in modified_files)
        super().__init__(
            "Your working tree is not clean.\n\n"
            f"Modified:\n{files}\n\n"
            "Commit or stash these changes before continuing."
        )


class BranchNotFoundError(GitReattributeError):
    def __init__(self, branch: str) -> None:
        super().__init__(f"Error: branch '{branch}' was not found in this repository.")


class IdentityNotFoundError(GitReattributeError):
    def __init__(self, identity: str, branch: str) -> None:
        super().__init__(
            f"Error: no commits matching:\n\n  {identity}\n\nwere found on branch {branch}."
        )


class MissingGitIdentityError(GitReattributeError):
    def __init__(self) -> None:
        super().__init__(
            "Error: Git does not have a configured user.name/user.email.\n\n"
            "Configure them with:\n\n"
            '  git config --global user.name "Your Name"\n'
            '  git config --global user.email "you@example.com"'
        )


class RewriteFailedError(GitReattributeError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Error: history rewrite failed: {reason}")


class PushRejectedError(GitReattributeError):
    def __init__(self) -> None:
        super().__init__(
            "The remote branch changed after the rewrite began.\n\n"
            "No remote history was overwritten.\n\n"
            "Review the remote changes before attempting another push."
        )


class MissingToolError(GitReattributeError):
    def __init__(self, tool: str, install_hint: str) -> None:
        super().__init__(f"Error: required tool '{tool}' was not found.\n\n{install_hint}")
