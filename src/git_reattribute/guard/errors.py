class GuardError(Exception):
    """Base class for guard-subcommand errors with a human-readable message."""


class ConfigNotFoundError(GuardError):
    def __init__(self, path: str) -> None:
        super().__init__(
            f"Error: config file not found: {path}\n\n"
            "Create a .git-reattribute-guard.yml with a `deny` list, e.g.:\n\n"
            "deny:\n"
            "  - name: Claude\n"
            "    email: claude@example.com\n"
        )


class ConfigInvalidError(GuardError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Error: invalid config: {reason}")


class GuardNotAGitRepositoryError(GuardError):
    def __init__(self) -> None:
        super().__init__(
            "Error: this directory is not a Git repository.\n\n"
            "Run the command from inside a Git repository."
        )


class InvalidRangeError(GuardError):
    def __init__(self, commit_range: str) -> None:
        super().__init__(f"Error: could not resolve commit range: {commit_range}")
