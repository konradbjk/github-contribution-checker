# GitHub Contribution Stats Fetcher

A tiny CLI + Python helper that mirrors the contribution heat map for any public GitHub profile by talking to the same internal endpoint the UI uses.

## Features

- Fetches daily contribution counts for the last 365 days or the current year
- Summarizes streaks, totals, and the most productive day
- Works as both a standalone CLI (`github-stats`) and an importable helper (`fetch_github_stats`)
- Zero auth required; it only needs a public profile

## Installation

```bash
uv init
source .venv/bin/activate        # .venv\Scripts\activate on Windows
```

The project targets Python 3.13+

## CLI Usage

```bash
# Username or full profile URL both work
python fetch_contributions.py konradbjk
# or, after installing the package:
github-stats https://github.com/konradbjk --range current_year --output json

# list every day with 8, 9, or 10 commits (supports ranges like 10-20 and 30+; always pass --counts)
python find_commit_days.py konradbjk --counts 8 9 10-20 20-30 30+
```

Default output is a human-friendly summary; pass `--output json` to receive the raw structure.

## Library Usage

```python
from fetch_contributions import fetch_github_stats

stats = fetch_github_stats("octocat", range_type="current_year")
print(stats["total_contributions"])
print(stats["streak_current"])
```

## Returned Data

```python
{
    "username": "octocat",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "total_contributions": 123,
    "streak_current": 5,
    "streak_longest": 15,
    "days": [
        {"date": "2024-03-14", "count": 4, "level": 1},
        # ...
    ],
}
```

## Development

- Works with public profiles only
- Network calls rely on GitHub’s contribution endpoint, so treat the tool respectfully
- Run `python fetch_contributions.py <username>` to sanity-check local changes

## Contributing

1. Fork / branch off `main`.
2. Create a local virtualenv (`uv venv && source .venv/bin/activate`) and install dependencies with `uv pip install -e .`.
3. Make your changes, keeping Ruff (`ruff check .`) and formatting in mind.
4. Test manually via the CLIs (`python fetch_contributions.py <profile>`, `python find_commit_days.py <profile> --counts ...`).
5. Update docs if behavior or options change.
6. Open a PR describing the motivation, steps to reproduce, and screenshots/output if relevant.
