"""Formatting helpers for optional CLI reports."""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal, TypedDict

from .parsing import ContributionStats

DEFAULT_COUNT_FILTERS: tuple[str, ...] = ("8", "9", "10")
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class CountFilter(TypedDict):
    label: str
    kind: Literal["exact", "range", "plus"]
    start: int
    end: int | None


def parse_count_filters(values: Sequence[str]) -> list[CountFilter]:
    """Parse raw filter expressions like '8', '10-20', or '30+'."""
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


def find_commit_count_matches(stats: ContributionStats, filters: Sequence[CountFilter]) -> dict[str, list[str]]:
    """Return all dates matching the requested commit filters."""
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

    return matches


def format_commit_count_report(stats: ContributionStats, matches: dict[str, list[str]]) -> str:
    """Pretty-print commit count matches."""
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


def calculate_weekday_distribution(stats: ContributionStats) -> dict[str, int]:
    """Total contribution counts per weekday."""
    totals: dict[str, int] = {name: 0 for name in WEEKDAY_NAMES}

    for day in stats["days"]:
        try:
            weekday_index = datetime.fromisoformat(day["date"]).weekday()
        except ValueError:
            continue
        totals[WEEKDAY_NAMES[weekday_index]] += day["count"]

    return totals


def format_weekday_report(stats: ContributionStats, weekday_totals: dict[str, int]) -> str:
    """Pretty-print weekday totals."""
    total_contributions = sum(weekday_totals.values())
    if total_contributions == 0:
        return (
            f"Username: {stats['username']}\n"
            f"Range: {stats['start_date']} → {stats['end_date']}\n"
            "No contributions recorded in this period."
        )

    lines = [
        f"Username: {stats['username']}",
        f"Range: {stats['start_date']} → {stats['end_date']}",
        "",
        "Weekday distribution:",
    ]

    for name in WEEKDAY_NAMES:
        count = weekday_totals[name]
        percent = (count / total_contributions) * 100 if total_contributions else 0.0
        lines.append(f"- {name:<9} {count:5d} contributions ({percent:5.1f}%)")

    max_count = max(weekday_totals.values())
    busiest_days = [name for name, count in weekday_totals.items() if count == max_count]

    if max_count == 0:
        lines.append("\nAll weekdays recorded zero contributions.")
    else:
        plural = "s" if len(busiest_days) > 1 else ""
        days_sentence = ", ".join(busiest_days)
        lines.append(f"\nMost active day{plural}: {days_sentence} ({max_count} contributions)")

    return "\n".join(lines)


def _parse_positive_int(value: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError("Empty numeric filter")
    number = int(value)
    if number < 0:
        raise ValueError("Counts must be non-negative")
    return number


def _sort_key(label: str) -> tuple[int, int]:
    if label.endswith("+"):
        base = int(label[:-1])
        return (base, 1)
    if "-" in label:
        start, end = label.split("-", 1)
        return (int(start), int(end))
    return (int(label), 0)
