# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - Unreleased

### Added

- New `git-reattribute guard` subcommand — prevention companion to the
  existing remediation flow. Never touches history; only scans and reports.
  - `guard check --base --head`: scans a commit range for denylisted
    identities (author/committer/Co-authored-by trailers). Intended for CI.
  - `guard check-local <message-file>`: checks the identity about to be
    used for the current commit. Intended for a `pre-commit` `repo: local`
    hook (`stages: [commit-msg]`).
  - Denylist config via `.git-reattribute-guard.yml` (`deny:` list of
    name/email pairs, glob supported on email; `check_coauthors` toggle).
  - Violation output names the exact `git-reattribute` command to fix it.
  - Composite GitHub Action at `.github/actions/guard` for PR-level
    enforcement (`uses: drk1rd/git-reattribute/.github/actions/guard@v1`).
- New `pyyaml` runtime dependency (for guard's config file).

## [0.1.1] - 2026-08-22

### Fixed

- Corrected package metadata (`Homepage`/`Issues` URLs, description wording).

## [0.1.0] - 2026-08-22

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
