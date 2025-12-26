"""GitHub contribution statistics fetcher and CLI."""

import argparse
import json
import re
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Literal, TypedDict
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

DateRangeType = Literal["last_365", "current_year"]


class ContributionDay(TypedDict):
    """Single day contribution data."""

    date: str
    count: int
    level: int


class ContributionStats(TypedDict):
    """Aggregated contribution statistics."""

    username: str
    start_date: str
    end_date: str
    total_contributions: int
    days: list[ContributionDay]
    streak_current: int
    streak_longest: int


def extract_username(profile_url: str) -> str:
    """Extract GitHub username from profile URL."""
    parsed = urlparse(profile_url)
    if parsed.netloc not in ("github.com", "www.github.com"):
        raise ValueError(f"Invalid GitHub URL: {profile_url}")

    path_parts = [p for p in parsed.path.split("/") if p]
    if not path_parts:
        raise ValueError(f"No username found in URL: {profile_url}")

    return path_parts[0]


def resolve_username(profile_or_username: str) -> str:
    """Resolve either a raw username or a profile URL to a username."""
    text = profile_or_username.strip()

    if not text:
        raise ValueError("Profile input cannot be empty")

    if text.startswith(("http://", "https://")) or "github.com" in text:
        return extract_username(text)

    # In case someone passes "github.com/user" without scheme.
    if "github.com" in text:
        return extract_username(f"https://{text.lstrip('/')}")

    normalized = text.strip("/")
    if not normalized:
        raise ValueError("Invalid username input")

    return normalized


def build_date_range(range_type: DateRangeType = "last_365") -> tuple[str, str]:
    """Build date range for fetching contributions."""
    today = datetime.now().date()

    if range_type == "last_365":
        from_date = today - timedelta(days=365)
        to_date = today
    elif range_type == "current_year":
        from_date = datetime(today.year, 1, 1).date()
        to_date = today
    else:
        raise ValueError(f"Invalid range_type: {range_type}")

    return from_date.isoformat(), to_date.isoformat()


def fetch_contributions_html(
    username: str, from_date: str, to_date: str, session: httpx.Client | None = None
) -> str:
    """Fetch raw HTML contribution data from GitHub."""
    url = f"https://github.com/{username}"
    params = {
        "action": "show",
        "controller": "profiles",
        "from": from_date,
        "tab": "contributions",
        "to": to_date,
        "user_id": username,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept": "text/html",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{url}?tab=contributions",
    }

    should_close = session is None
    client = session or httpx.Client(headers=headers, follow_redirects=True)

    try:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.text
    finally:
        if should_close:
            client.close()


def parse_contribution_count(tooltip_text: str) -> int:
    """Extract contribution count from tooltip text."""
    if "No contribution" in tooltip_text:
        return 0

    match = re.search(r"(\d+)\s+contribution", tooltip_text)
    if match:
        return int(match.group(1))

    return 0


def parse_contributions_html(html: str, username: str, from_date: str, to_date: str) -> ContributionStats:
    """Parse HTML contribution calendar into structured data."""
    soup = BeautifulSoup(html, "html.parser")
    days: list[ContributionDay] = []

    for cell in soup.find_all("td", class_="ContributionCalendar-day"):
        date_attr = cell.get("data-date")
        if not isinstance(date_attr, str):
            continue

        level_attr = cell.get("data-level")
        if isinstance(level_attr, str):
            try:
                level = int(level_attr)
            except ValueError:
                level = 0
        else:
            level = 0

        cell_id = cell.get("id")
        tooltip = soup.find("tool-tip", attrs={"for": cell_id}) if isinstance(cell_id, str) else None

        count = 0
        if tooltip:
            tooltip_text = tooltip.get_text(strip=True)
            count = parse_contribution_count(tooltip_text)

        days.append({"date": date_attr, "count": count, "level": level})

    days.sort(key=lambda d: d["date"])

    total_contributions = sum(day["count"] for day in days)
    current_streak = calculate_current_streak(days)
    longest_streak = calculate_longest_streak(days)

    return {
        "username": username,
        "start_date": from_date,
        "end_date": to_date,
        "total_contributions": total_contributions,
        "days": days,
        "streak_current": current_streak,
        "streak_longest": longest_streak,
    }


def calculate_current_streak(days: list[ContributionDay]) -> int:
    """Calculate current contribution streak."""
    if not days:
        return 0

    streak = 0
    for day in reversed(days):
        if day["count"] > 0:
            streak += 1
        else:
            break

    return streak


def calculate_longest_streak(days: list[ContributionDay]) -> int:
    """Calculate longest contribution streak in the period."""
    if not days:
        return 0

    max_streak = 0
    current = 0

    for day in days:
        if day["count"] > 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0

    return max_streak


def fetch_github_stats(
    profile: str, range_type: DateRangeType = "last_365", session: httpx.Client | None = None
) -> ContributionStats:
    """
    Main function to fetch and parse GitHub contribution statistics.

    Args:
        profile: GitHub profile URL or username
        range_type: Either 'last_365' or 'current_year'

    Returns:
        Parsed contribution statistics
    """
    username = resolve_username(profile)
    from_date, to_date = build_date_range(range_type)

    html = fetch_contributions_html(username, from_date, to_date, session=session)
    stats = parse_contributions_html(html, username, from_date, to_date)

    return stats


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch GitHub contribution statistics")
    parser.add_argument(
        "profile",
        help="GitHub username or profile URL (e.g. octocat or https://github.com/octocat)",
    )
    parser.add_argument(
        "--range",
        choices=["last_365", "current_year"],
        default="last_365",
        dest="range_type",
        help="Date range to analyze (default: last_365)",
    )
    parser.add_argument(
        "--output",
        choices=["summary", "json"],
        default="summary",
        help="Choose summary text or JSON output",
    )
    return parser


def summarize_stats(stats: ContributionStats) -> str:
    days = stats["days"]
    days_count = len(days)
    active_days = sum(1 for day in days if day["count"] > 0)
    most_productive = max(days, key=lambda day: day["count"], default=None)

    lines = [
        f"Username: {stats['username']}",
        f"Range: {stats['start_date']} → {stats['end_date']}",
        f"Total contributions: {stats['total_contributions']}",
        f"Current streak: {stats['streak_current']} days",
        f"Longest streak: {stats['streak_longest']} days",
        f"Active days: {active_days} / {days_count}",
    ]

    if most_productive:
        lines.append(
            f"Most productive: {most_productive['date']} ({most_productive['count']} contributions, level {most_productive['level']})"
        )

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    stats = fetch_github_stats(args.profile, range_type=args.range_type)

    if args.output == "json":
        print(json.dumps(stats, indent=2))
    else:
        print(summarize_stats(stats))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
