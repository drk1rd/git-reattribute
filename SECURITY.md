# Security Policy

## Supported versions

Only the latest published release on PyPI receives fixes. This project is
pre-1.0; there is no long-term-support branch yet.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, use [GitHub's private vulnerability reporting](https://github.com/drk1rd/git-reattribute/security/advisories/new)
for this repository. Include:

- A description of the issue and its potential impact.
- Steps to reproduce, ideally against a throwaway/scratch repository.
- The git-reattribute version, Git version, and OS you tested on.

You should get an initial response within a few days. If the report is
confirmed, a fix will be released and the advisory published once a patched
version is available.

## Scope notes specific to this tool

Git Reattribute rewrites Git history and can force-push to remotes. Relevant
things to flag as a security issue (rather than a regular bug) include:

- Any way the tool could be induced to rewrite or push to a branch/remote
  the user did not select or confirm.
- Any way `--force-with-lease` could behave like `git push --force` and
  silently overwrite remote history the user didn't intend to overwrite.
- Any way commit metadata (author/committer/trailers) could be altered
  beyond what was shown in the pre-rewrite summary and confirmed by the
  user.
- Credential or token exposure in `--verbose` output or error messages.

General correctness bugs that don't involve unintended data loss, unintended
history rewriting, or credential exposure should go through the normal
issue tracker instead.
