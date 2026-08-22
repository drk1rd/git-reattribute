# Contributing to Git Reattribute

## Development setup

```bash
git clone https://github.com/drk1rd/git-reattribute.git
cd git-reattribute
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

Tests build temporary Git repositories per test case (see `tests/conftest.py`)
— nothing is ever run against a real or shared repository. If you're adding
a test that exercises `RewriteEngine`, prefer extending the existing
`basic_repo` fixture's history over hand-rolling a new one, unless your test
needs a distinct topology (e.g. `mailmap_repo`, `bare_remote`).

## Making changes

- Keep runtime dependencies minimal — this is meant to stay a small, focused
  CLI. If you're adding a dependency, explain why an existing one (or the
  standard library) doesn't cover it.
- History-rewrite logic lives in `rewrite.py` and goes through
  `git-filter-repo`; don't hand-roll Git object rewriting.
- Any change to `rewrite.py`, `push.py`, or `cli.py`'s confirmation/warning
  flow should be manually verified against a scratch repository in addition
  to the test suite, since these paths are destructive by design.
- Update `README.md` and `CHANGELOG.md` alongside behavior changes — the
  README is expected to match what's actually implemented.

## Submitting a pull request

1. Fork the repo and create a branch from `main`.
2. Make your change, with tests.
3. Run `pytest` locally.
4. Open a PR describing what changed and why (the PR template will prompt
   you for this).

## Reporting bugs / requesting features

Use the GitHub issue templates. For anything security-related, see
`SECURITY.md` instead of opening a public issue.
