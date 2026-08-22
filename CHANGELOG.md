# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - Unreleased

### Added

- Initial MVP: interactive and non-interactive contributor-identity
  replacement using `git-filter-repo`.
- Branch discovery and selection.
- Contributor discovery (author/committer, raw identity fields, no mailmap).
- Backup ref creation before every rewrite.
- Author/committer/both replacement scope via `--identity-type`.
- Co-authored-by trailer stripping for the replaced identity.
- Post-rewrite verification.
- `--force-with-lease` push support.
- Dry-run mode.
- Signed-commit and shallow-repository warnings.
