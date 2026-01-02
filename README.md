# GitHub Contribution Stats Fetcher

A tiny CLI + Python helper that mirrors the contribution heat map for any public GitHub profile by talking to the same internal endpoint the UI uses.

## Features

- Fetches daily contribution counts for the last 365 days or the current year
- Summarizes streaks, totals, and the most productive day
- Optional viewpoints for commit-count searches and weekday distributions
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
python cli.py konradbjk
# Turn on verbose logging (range selection, exported rows, GitHub notices)
python cli.py konradbjk --log-level info
# Persist artifacts even outside DEBUG mode
python cli.py konradbjk --save-html
# Fetch a specific calendar year
python cli.py konradbjk --year 2023
# Custom ranges (ISO dates or Unix timestamps; spans auto-merge across years)
python cli.py konradbjk --from-date 2024-12-01 --to-date 2025-12-01
# Rolling range accepts timestamps too (example: Dec 1 2024 - Jan 1 2025)
python cli.py konradbjk --from-date 1733011200 --to-date 1735689600
# or, after installing the package:
github-stats https://github.com/konradbjk --range current_year --output json

# list every day with 8, 9, or 10 commits (supports ranges like 10-20 and 30+; --counts optional)
python cli.py konradbjk --output counts --counts 8 9 10-20 20-30 30+

# inspect weekday distribution and the busiest day(s)
python cli.py konradbjk --output weekly --range current_year
# Weekday view for a specific calendar year (auto-caps on today's date if in-progress)
python cli.py konradbjk --output weekly --year 2025
# Rolling last-365 weekday snapshot, handy for spotting recent cadence shifts
python cli.py konradbjk --output weekly --range last_365
```

Default output is a human-friendly summary; pass `--output json` to receive the raw structure. Per-run logs still live in `log/`, but raw HTML + parsed JSON snapshots are now written under `data/` only when you pass `--save-html` or run with `--log-level debug`. Multi-year custom ranges create one HTML file per calendar year with the same timestamped prefix.

## Library Usage

```python
from github_stats.fetch import fetch_github_stats

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
- Run `python cli.py <username>` to sanity-check local changes

## Contributing

1. Fork / branch off `main`.
2. Create a local virtualenv (`uv venv && source .venv/bin/activate`) and install dependencies with `uv pip install -e .`.
3. Make your changes, keeping Ruff (`ruff check .`) and formatting in mind.
4. Test manually via the CLI (`python cli.py <profile>`, `python cli.py <profile> --output counts --counts ...`).
5. Update docs if behavior or options change.
6. Open a PR describing the motivation, steps to reproduce, and screenshots/output if relevant.
