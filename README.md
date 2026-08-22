# Git Reattribute

A small, cross-platform CLI for replacing one Git identity with another
across a repository's history, safely — without requiring you to hand-write
a `git-filter-repo` invocation.

> **⚠️ This tool rewrites Git history.** Rewriting history changes commit
> SHAs, invalidates existing signatures on rewritten commits, and requires a
> force push to update any already-published branch. A force push can
> disrupt collaborators and invalidate their existing clones. Only use this
> on repositories and history you are authorized to modify. This tool does
> not modify GitHub (or any other host's) account data or contributor
> database directly — hosts may independently recompute contributor
> attribution from the resulting commit metadata.

## Why?

A Git "identity" isn't always a person — it can be a placeholder, a bot
account, a shared machine account, or an AI agent that paired on the work.
Correcting a mis-attributed one usually means hand-writing a
`git-filter-repo` invocation. Git Reattribute turns that into one guided
command.

## Features

- Interactive branch, contributor, and replacement-identity selection.
- Non-interactive / scriptable usage via flags.
- Replaces author, committer, or both (default: both).
- Removes matching `Co-authored-by:` trailers for the replaced identity.
- Dry-run mode — preview the impact with no changes made.
- Creates a backup ref before every rewrite.
- Mandatory post-rewrite verification.
- `--force-with-lease` push only, never `--force`, never silent.
- Warns about signed commits and shallow repositories before rewriting.

## Requirements

- Python 3.10+
- Git 2.x
- `git-filter-repo` — installed automatically as a dependency when you
  `pip install git-reattribute`; you don't need to install it separately.

## Installation

```bash
python -m pip install git-reattribute
```

## Quick Start

```bash
cd your-repo
git-reattribute --version
git-reattribute --help
git-reattribute
```

## Example

```text
$ git-reattribute

Git Reattribute

Repository: /home/alice/projects/example
Remote:    origin
Branch:    main

Contributors on main:

  1. Claude <claude@example.com>    47 commits
  2. Alice <alice@example.com>      18 commits
  3. Bob <bob@example.com>           6 commits

Select contributor to replace: Claude <claude@example.com>    47 commits

Replace with:
  Current Git identity
  Alice <alice@example.com>
  Bob <bob@example.com>
  Enter a custom identity

Select replacement: Alice <alice@example.com>

Summary
-------
Branch:       main
From:         Claude <claude@example.com>
To:           Alice <alice@example.com>
Author commits affected:    47
Committer commits affected: 47
Co-authored-by trailers to remove: 3

WARNING: This operation rewrites Git history.

Type REWRITE to continue: REWRITE

History rewrite completed.

Recovery reference:
  refs/backup/git-reattribute/2026-08-22T10-30-00

To restore the original branch:
  git reset --hard refs/backup/git-reattribute/2026-08-22T10-30-00

Keep this reference until you have verified the rewritten history.

Verification

  Old identity commits before: 94
  Remaining old identity commits: 0
  New identity commits: 94
  Remaining Co-authored-by trailers: 0

Verification: PASS

Push rewritten branch to origin with --force-with-lease? [y/N]
```

## Interactive Usage

Running `git-reattribute` with no flags walks you through: select a branch,
see its contributors, pick who to replace, pick the replacement, preview the
change, then type `REWRITE` to confirm.

## Non-Interactive Usage

```bash
git-reattribute \
  --branch main \
  --from-email claude@example.com \
  --to-name Alice \
  --to-email alice@example.com \
  --identity-type both \
  --yes --push
```

`--yes` does not imply `--push` — pass both explicitly when you want a
scripted rewrite-and-push.

## Dry Run

```bash
git-reattribute --branch main --from-email claude@example.com --to-current-user --dry-run
```

Shows affected author/committer commit counts and any `Co-authored-by:`
trailers that would be removed. No history or remote is touched.

## Branches

Local branches are listed and selectable. Remote-tracking branches are not
rewritten directly — check out a local branch first. The rewrite scope is
the **entire reachable history of the selected branch** — every commit an
ancestor of that branch's tip, not just commits made while that branch was
checked out.

## Authors vs Committers

Every commit has an author and a committer, and they can differ. Use
`--identity-type author`, `--identity-type committer`, or the default
`--identity-type both` to control which field(s) get rewritten. The
interactive UI shows both roles whenever they differ for a given contributor.

## Co-authored-by Trailers

When an identity (for example an AI agent that paired with the human author)
appears as a `Co-authored-by:` trailer in a commit message, that trailer is
**removed** (not replaced) for the identity being replaced, by default. This
matters because rewriting only the author field of a commit like:

```text
Author: Claude <claude@example.com>

Co-authored-by: Claude <claude@example.com>
```

would otherwise leave the old identity behind in the message body even
after the commit object's author is fixed.

This runs alongside the author/committer rewrite for the same source
identity — there is no separate replacement target for trailers, and the
trailer is deleted, not rewritten to a new co-author. Disable it with
`--no-strip-coauthor-trailers`.

**Matching rule:** a trailer line matches when it starts with
`Co-authored-by:` (case-insensitive) followed by the source identity's name
and `<email>`, with any amount of whitespace tolerated around the colon,
name, and angle brackets — but the name and email themselves must match the
source identity's recorded name/email (case-insensitively), not a partial or
fuzzy match. Only matching trailer lines are removed; other trailers (e.g.
`Signed-off-by:`) and body text that merely mentions the same name are left
untouched.

## History Rewriting Warning

This tool rewrites Git history using [`git-filter-repo`](https://github.com/newren/git-filter-repo).
Two different `--force` flags matter here, and they are not the same thing:

- **`git-filter-repo --force`** (used internally, always) only permits the
  *local* rewrite to run on a non-fresh-clone repository. `git-filter-repo`
  normally refuses to touch anything but a fresh clone as a generic safety
  net; this tool creates its own backup ref (see **Recovery** below) *before*
  that rewrite ever runs, so that backup is the safety net instead, and the
  `--force` flag just lets the local rewrite proceed.
- **`git push --force`** is never used by this tool, anywhere. Publishing a
  rewritten branch always uses `git push --force-with-lease` (see
  **Push Behavior**), and only after you explicitly confirm it.

Contributor discovery uses Git's raw `%an`/`%ae`/`%cn`/`%ce` fields, not
mailmap-resolved fields — a repository's `.mailmap` is intentionally ignored
so what you see and rewrite always matches the actual commit-object bytes.

Signed commits lose their signatures when rewritten — a warning is shown
before you confirm. Merge commits are rewritten natively by `git-filter-repo`
as part of a full-branch rewrite; this requires no special handling in v1
since there is no commit-range filtering yet.

## Push Behavior

Pushing always uses `git push --force-with-lease`, never `git push --force`.
Nothing is pushed unless you pass `--push` (scripted) or confirm the
interactive prompt. If the remote branch changed since the rewrite began,
the push is rejected and nothing is retried automatically.

## Recovery

Before every rewrite — and before `git-filter-repo` is ever invoked — a
backup ref is created pointing at the original branch tip:

```
refs/backup/git-reattribute/<timestamp>
```

The rewrite is scoped (via `--refs <branch>`) to only the selected branch,
so the backup ref itself is never touched or rewritten by the same
operation. It is never deleted automatically. After a rewrite, the tool
prints the exact recovery command:

```text
Recovery reference:
  refs/backup/git-reattribute/2026-08-22T10-30-00

To restore the original branch:
  git reset --hard refs/backup/git-reattribute/2026-08-22T10-30-00
```

Keep the backup ref until you've verified the rewritten history (and pushed,
if applicable) — then it's safe to delete with
`git update-ref -d refs/backup/git-reattribute/<timestamp>`.

## Limitations

- Shallow clones may show an incomplete contributor list and rewrite scope;
  run `git fetch --unshallow` first.
- Submodules, Git LFS objects, and annotated tag signatures are not
  specially handled in v1.
- Branch-protection or remote-policy push rejections are surfaced as-is;
  this tool never attempts to bypass them.
- One source identity → one target identity per run.

## Development

```bash
python -m pip install -e ".[dev]"
```

## Testing

```bash
pytest
```

Tests build temporary Git repositories per-test; nothing is ever run against
a real/shared repository.

## Release Process

See `CHANGELOG.md`. Versioning follows SemVer (`MAJOR.MINOR.PATCH`).

## License

MIT — see `LICENSE`.
