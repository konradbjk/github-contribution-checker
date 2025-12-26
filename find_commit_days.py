"""List contribution days that match specific commit counts."""

import argparse
from collections.abc import Sequence
from typing import Literal, TypedDict

from fetch_contributions import ContributionStats, DateRangeType, fetch_github_stats

class CountFilter(TypedDict):
    label: str
    kind: Literal["exact", "range", "plus"]
    start: int
    end: int | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show all contribution days that match given commit counts (defaults: 8, 9, 10)"
    )
    parser.add_argument("profile", help="GitHub username or profile URL")
    parser.add_argument(
        "--range",
        choices=["last_365", "current_year"],
        default="last_365",
        dest="range_type",
        help="Date range to analyze (default: last_365)",
    )
    parser.add_argument(
        "--counts",
        type=str,
        nargs="+",
        metavar="FILTER",
        default=None,
        help="Counts or ranges to search for (e.g. 8 9 10-20 20-30 30+)",
    )
    return parser


def parse_filters(values: Sequence[str] | None) -> list[CountFilter]:
    if not values:
        raise ValueError(
            "No commit counts provided. Use --counts with values like '8', '10-20', or '30+' "
            "to filter matching contribution days."
        )

    filters: list[CountFilter] = []
    for raw in values:
        token = raw.strip()
        if not token:
            continue

        if token.endswith("+"):
            start = _parse_positive_int(token[:-1])
            filters.append({"label": f"{start}+", "kind": "plus", "start": start, "end": None})
        elif "-" in token:
            start_str, end_str = token.split("-", 1)
            start = _parse_positive_int(start_str)
            end = _parse_positive_int(end_str)
            low, high = sorted((start, end))
            filters.append({"label": f"{low}-{high}", "kind": "range", "start": low, "end": high})
        else:
            exact = _parse_positive_int(token)
            filters.append({"label": str(exact), "kind": "exact", "start": exact, "end": exact})

    if not filters:
        raise ValueError(
            "Only empty filters were supplied. Provide counts like '8', ranges like '10-20', or thresholds like '30+'."
        )

    return filters


def _parse_positive_int(value: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError("Empty numeric filter")
    number = int(value)
    if number < 0:
        raise ValueError("Counts must be non-negative")
    return number


def find_matching_days(
    profile: str, counts: Sequence[str] | None, range_type: DateRangeType = "last_365"
) -> tuple[ContributionStats, dict[str, list[str]]]:
    stats = fetch_github_stats(profile, range_type=range_type)
    filters = parse_filters(counts)
    matches: dict[str, list[str]] = {flt["label"]: [] for flt in filters}

    for day in stats["days"]:
        count = day["count"]
        for flt in filters:
            if flt["kind"] == "exact" and count == flt["start"]:
                matches[flt["label"]].append(day["date"])
            elif flt["kind"] == "range" and flt["start"] <= count <= (flt["end"] or flt["start"]):
                matches[flt["label"]].append(day["date"])
            elif flt["kind"] == "plus" and count >= flt["start"]:
                matches[flt["label"]].append(day["date"])

    return stats, matches


def format_matches(stats: ContributionStats, matches: dict[str, list[str]]) -> str:
    lines = [
        f"Username: {stats['username']}",
        f"Range: {stats['start_date']} → {stats['end_date']}",
        "",
    ]

    if not matches:
        lines.append("No commit counts requested.")
        return "\n".join(lines)

    for label in sorted(matches, key=_sort_key):
        dates = matches[label]
        lines.append(f"{label} commits: {len(dates)} day(s)")
        for date in dates:
            lines.append(f"  - {date}")
        lines.append("")

    return "\n".join(lines).strip()


def _sort_key(label: str) -> tuple[int, int]:
    if label.endswith("+"):
        base = int(label[:-1])
        return (base, 1)
    if "-" in label:
        start, end = label.split("-", 1)
        return (int(start), int(end))
    return (int(label), 0)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        stats, matches = find_matching_days(args.profile, counts=args.counts, range_type=args.range_type)
    except ValueError as exc:
        parser.error(str(exc))

    print(format_matches(stats, matches))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
