"""Helpers for assembling contribution stats across ranges."""

from datetime import date
from pathlib import Path
import logging

import httpx

from .artifacts import save_html_dump
from .http_client import fetch_contributions_html, fetch_last365_html
from .parsing import (
    ContributionDay,
    ContributionStats,
    calculate_current_streak,
    calculate_longest_streak,
    parse_contributions_html,
)
from .selectors import RangeSelection, split_into_year_windows, year_bounds

logger = logging.getLogger(__name__)


def filter_days_within_range(days: list[ContributionDay], start_date: date, end_date: date) -> list[ContributionDay]:
    """Filter contribution days so they fall within the provided window."""
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    result: list[ContributionDay] = []
    for day in days:
        day_date = day.get("date")
        if isinstance(day_date, str) and start_iso <= day_date <= end_iso:
            result.append(day)
    return result


def collect_days_for_range(
    username: str,
    start_date: date,
    end_date: date,
    session: httpx.Client | None,
    html_base: Path | None,
) -> list[ContributionDay]:
    """Fetch and stitch contribution days spanning multiple years."""
    windows = split_into_year_windows(start_date, end_date)
    logger.info(
        "Fetching %d year block(s) for %s covering %s → %s",
        len(windows),
        username,
        start_date.isoformat(),
        end_date.isoformat(),
    )

    year_cache: dict[int, list[ContributionDay]] = {}
    collected: list[ContributionDay] = []

    for window_index, (window_start, window_end) in enumerate(windows, start=1):
        year = window_start.year
        if year not in year_cache:
            req_start, req_end = year_bounds(year)
            html = fetch_contributions_html(
                username,
                req_start.isoformat(),
                req_end.isoformat(),
                session=session,
            )
            suffix = None if len(windows) == 1 or window_index == 1 else f"year{year}"
            save_html_dump(html_base, suffix, html)
            stats = parse_contributions_html(html, username, req_start.isoformat(), req_end.isoformat())
            year_cache[year] = stats["days"]

        filtered_days = filter_days_within_range(year_cache[year], window_start, window_end)
        logger.debug(
            "Window %d/%d (%s → %s) yielded %d day(s)",
            window_index,
            len(windows),
            window_start.isoformat(),
            window_end.isoformat(),
            len(filtered_days),
        )
        collected.extend(filtered_days)

    collected.sort(key=lambda d: d["date"])
    return collected


def assemble_stats(username: str, start_date: date, end_date: date, days: list[ContributionDay]) -> ContributionStats:
    """Build the final ContributionStats payload from aggregated days."""
    total_contributions = sum(day["count"] for day in days)
    current_streak = calculate_current_streak(days)
    longest_streak = calculate_longest_streak(days)

    return {
        "username": username,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_contributions": total_contributions,
        "days": days,
        "streak_current": current_streak,
        "streak_longest": longest_streak,
    }


def build_stats_for_range(
    username: str,
    start_date: date,
    end_date: date,
    session: httpx.Client | None,
    html_base: Path | None,
    description: str,
) -> ContributionStats:
    """Fetch, merge, and summarize contributions for the requested range."""
    stats_days = collect_days_for_range(username, start_date, end_date, session, html_base)
    stats = assemble_stats(username, start_date, end_date, stats_days)
    logger.info(
        "Range '%s' for %s: %d days, total %d contributions (current streak %d, longest %d)",
        description,
        username,
        len(stats_days),
        stats["total_contributions"],
        stats["streak_current"],
        stats["streak_longest"],
    )
    return stats


def build_stats_from_single_html(
    username: str,
    selection: RangeSelection,
    session: httpx.Client | None,
    html_base: Path | None,
) -> ContributionStats:
    """Fetch a single rolling HTML payload and assemble stats."""
    html = fetch_last365_html(username, session=session)
    save_html_dump(html_base, None, html)
    parsed = parse_contributions_html(
        html,
        username,
        selection.start_date.isoformat(),
        selection.end_date.isoformat(),
    )
    filtered_days = filter_days_within_range(parsed["days"], selection.start_date, selection.end_date)
    stats = assemble_stats(username, selection.start_date, selection.end_date, filtered_days)
    logger.info(
        "Range '%s' for %s: %d days, total %d contributions (current streak %d, longest %d)",
        selection.description,
        username,
        len(filtered_days),
        stats["total_contributions"],
        stats["streak_current"],
        stats["streak_longest"],
    )
    return stats
