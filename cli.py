"""CLI entrypoint for GitHub contribution helpers."""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from github_stats.fetch import ContributionStats, fetch_github_stats, resolve_username, setup_logging
from github_stats.reports import (
    DEFAULT_COUNT_FILTERS,
    calculate_weekday_distribution,
    find_commit_count_matches,
    format_commit_count_report,
    format_weekday_report,
    parse_count_filters,
)

DATA_DIR = Path("data")
LOG_DIR = Path("log")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and inspect GitHub contribution data (rolling, yearly, or custom ranges).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cli.py konradbjk --output weekly --year 2025    # Full 2025 calendar view\n"
            "  python cli.py konradbjk --output weekly --range last_365  # Rolling last-year cadence"
        ),
    )
    parser.add_argument(
        "profile",
        help="GitHub username or profile URL (e.g. octocat or https://github.com/octocat)",
    )
    parser.add_argument(
        "--range",
        choices=["last_365", "current_year"],
        default="last_365",
        dest="range_type",
        help=(
            "Range preset when no --year/--from-date is supplied "
            "(default: last_365, which uses GitHub's rolling endpoint)."
        ),
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Fetch an entire calendar year (1 Jan → 31 Dec). Overrides --range.",
    )
    parser.add_argument(
        "--from-date",
        dest="from_date",
        help="Custom range start (ISO date like 2024-12-01 or Unix timestamp). Requires --to-date.",
    )
    parser.add_argument(
        "--to-date",
        dest="to_date",
        help="Custom range end (ISO date or Unix timestamp). Requires --from-date.",
    )
    parser.add_argument(
        "--output",
        choices=["summary", "json", "counts", "weekly"],
        default="summary",
        help=(
            "Console output format. Use 'counts' to list specific commit totals or 'weekly' "
            "for weekday aggregation (default: summary)."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity. DEBUG also forces artifact persistence under data/.",
    )
    parser.add_argument(
        "--save-html",
        action="store_true",
        help=(
            "Always persist raw HTML and JSON artifacts under data/. "
            "Without this flag, artifacts are only saved when --log-level DEBUG is used."
        ),
    )
    parser.add_argument(
        "--counts",
        nargs="+",
        metavar="FILTER",
        help=(
            "Filters for --output counts (e.g. 8 9 10-20 30+). "
            "Defaults to 8, 9, 10 when --output counts is selected."
        ),
    )
    return parser


def format_summary(stats: ContributionStats) -> str:
    return "\n".join(
        [
            f"Username: {stats['username']}",
            f"Range: {stats['start_date']} → {stats['end_date']}",
            f"Total contributions: {stats['total_contributions']}",
            f"Current streak: {stats['streak_current']} days",
            f"Longest streak: {stats['streak_longest']} days",
            f"Active days: {sum(1 for day in stats['days'] if day['count'] > 0)} / {len(stats['days'])}",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"run-{timestamp}.log"
    setup_logging(args.log_level, log_file, console_enabled=False)

    username = resolve_username(args.profile)
    safe_name = username.replace("/", "_")

    persist_artifacts = args.save_html or args.log_level.upper() == "DEBUG"
    html_path = None
    json_path = None
    if persist_artifacts:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        html_path = DATA_DIR / f"{timestamp}-{safe_name}.html"
        json_path = DATA_DIR / f"{timestamp}-{safe_name}.json"

    stats = fetch_github_stats(
        args.profile,
        range_type=args.range_type,
        year=args.year,
        from_date_override=args.from_date,
        to_date_override=args.to_date,
        save_html_path=html_path,
    )

    if json_path:
        json_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    if args.output == "json":
        print(json.dumps(stats, indent=2))
    elif args.output == "counts":
        raw_filters = args.counts or list(DEFAULT_COUNT_FILTERS)
        try:
            filters = parse_count_filters(raw_filters)
        except ValueError as exc:
            parser.error(str(exc))
        matches = find_commit_count_matches(stats, filters)
        print(format_commit_count_report(stats, matches))
    elif args.output == "weekly":
        weekday_totals = calculate_weekday_distribution(stats)
        print(format_weekday_report(stats, weekday_totals))
    else:
        print(format_summary(stats))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
