# GitHub Contribution Checker – Agent Guide

This document summarizes everything an agent needs to know to work effectively in this repository.

## Project Overview

- Purpose: fetch and inspect GitHub contribution calendars using GitHub’s public contribution endpoint.
- Key entry points:
  - `fetch_contributions.py`: core logic + CLI (`python fetch_contributions.py <username|url>` / installed as `github-stats`).
  - `find_commit_days.py`: helper CLI that lists days matching specific commit counts (defaults: 8, 9, 10).
  - `usage.py`: demonstrates library usage (handy for sanity checks).

## Runtime & Tooling

- Python 3.13 is the target/runtime. Avoid legacy compatibility shims (`__future__`, typing backports, etc).
- Dependencies (see `pyproject.toml` / `uv.lock`): `httpx`, `beautifulsoup4`, `lxml`.
- Linting: Ruff configured via `ruff.toml` (120-char lines, rule set `E W F I N UP`).
- No tests yet; lightweight validation is usually done by executing the CLIs against a public profile.

## CLI Usage Cheatsheet

```bash
# summary output
python fetch_contributions.py octocat
# JSON output
python fetch_contributions.py https://github.com/konradbjk --output json
# alternate range
python fetch_contributions.py konradbjk --range current_year
# find specific commit counts
python find_commit_days.py konradbjk --counts 8 9 10
```

Both CLIs accept plain usernames or profile URLs; `fetch_github_stats` auto-detects and normalizes inputs.

## Code Structure Highlights

- `ContributionDay` / `ContributionStats` are `TypedDict` models used across modules.
- Network fetch (`fetch_contributions_html`) accepts an optional `httpx.Client` to allow session reuse in future enhancements.
- HTML parsing uses BeautifulSoup; data attributes must be validated (some cells lack `data-date`).
- Streak calculations operate on the sorted `days` list; keep that ordering if refactoring.
- `find_commit_days.py` reuses `fetch_github_stats` and supports arbitrary counts via `--counts`.

## VS Code / Dev UX

- `.vscode/extensions.json` recommends only Python-centric extensions (Python, Ruff, indentation helper, autodocstring, markdownlint).
- Ruff is not integrated via pre-commit; run manually if needed (`ruff check .`).

## Common Tasks

- **Fetch stats programmatically:** import `fetch_contributions.fetch_github_stats`.
- **Regenerate CLI summary:** `python fetch_contributions.py <profile>`.
- **Search for specific contribution counts:** `python find_commit_days.py <profile> --counts ...`.
- **Keep docs in sync:** update `README.md` when new flags/scripts are introduced.

## Contribution Tips

- Stick to plain ASCII unless a file already uses Unicode.
- Prefer `rg` for search, respect existing formatting, and keep code comments minimal but helpful.
- Avoid adding global state; functions currently return plain dicts for straightforward JSON serialization.

With this reference, agents should be able to audit, refactor, or extend the project confidently without digging through the entire codebase first.*** End Patch} to=functions.apply_patch зимой
