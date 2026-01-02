"""HTML parsing helpers for contribution calendars."""

import logging
import re

from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import TypedDict

logger = logging.getLogger(__name__)


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


def parse_contribution_count(tooltip_text: str) -> int:
    """Extract contribution count from tooltip text."""
    if "No contribution" in tooltip_text:
        return 0

    match = re.search(r"(\d+)\s+contribution", tooltip_text)
    if match:
        return int(match.group(1))

    return 0


def build_day_from_cell(cell: Tag, tooltip_lookup: dict[str, str] | None = None) -> tuple[ContributionDay | None, str]:
    """Convert a calendar cell element into a ContributionDay entry."""
    date_attr = cell.get("data-date")
    if not isinstance(date_attr, str):
        return None, "missing data-date"

    level_attr = cell.get("data-level")
    if isinstance(level_attr, str):
        try:
            level = int(level_attr)
        except ValueError:
            level = 0
    else:
        level = 0

    count = 0
    count_source = "unset"
    count_attr = cell.get("data-count")
    if isinstance(count_attr, str):
        try:
            count = int(count_attr)
            count_source = "data-count"
        except ValueError:
            count = 0

    if count == 0:
        aria_text = cell.get("data-aria-label") or cell.get("aria-label")
        if isinstance(aria_text, str):
            parsed = parse_contribution_count(aria_text)
            if parsed or "No contribution" in aria_text:
                count = parsed
                count_source = "aria-label"

    if count == 0:
        sr_only = cell.find("span", class_="sr-only")
        if sr_only:
            text = sr_only.get_text(strip=True)
            parsed = parse_contribution_count(text)
            if parsed or "No contribution" in text:
                count = parsed
                count_source = "sr-only"

    if count == 0:
        tooltip = cell.find("tool-tip")
        if tooltip:
            text = tooltip.get_text(strip=True)
            parsed = parse_contribution_count(text)
            if parsed or "No contribution" in text:
                count = parsed
                count_source = "inline tool-tip"

    if count == 0 and tooltip_lookup:
        cell_id = cell.get("id")
        if isinstance(cell_id, str) and cell_id in tooltip_lookup:
            text = tooltip_lookup[cell_id]
            parsed = parse_contribution_count(text)
            if parsed or "No contribution" in text:
                count = parsed
                count_source = "external tool-tip"

    details = f"count_source={count_source}, raw_level={cell.get('data-level')}"
    return {"date": date_attr, "count": count, "level": level}, details


def parse_contributions_html(html: str, username: str, from_date: str, to_date: str) -> ContributionStats:
    """Parse HTML contribution calendar into structured data."""
    soup = BeautifulSoup(html, "html.parser")

    alert_selectors = [
        ".flash",
        ".flash-error",
        ".flash-warn",
        ".flash-notice",
        ".js-flash-alert",
    ]
    alert_messages: set[str] = set()
    for selector in alert_selectors:
        for element in soup.select(selector):
            text = element.get_text(" ", strip=True)
            if text:
                alert_messages.add(text)

    for message in sorted(alert_messages):
        logger.warning("GitHub page notice for %s: %s", username, message)

    calendar_table = soup.select_one(".js-calendar-graph table.ContributionCalendar-grid")
    if calendar_table is None:
        logger.warning("Calendar table not found for %s; falling back to global search", username)

    tooltip_map: dict[str, str] = {}
    tooltip_scope = calendar_table or soup
    for tooltip in tooltip_scope.select("tool-tip[for]"):
        target = tooltip.get("for")
        if isinstance(target, str):
            tooltip_map[target] = tooltip.get_text(strip=True)

    cell_scope = calendar_table or soup
    cells = cell_scope.select(".ContributionCalendar-day[data-date]")
    cells_scanned = len(cells)
    invalid_cells = 0
    deduped: dict[str, ContributionDay] = {}

    for index, cell in enumerate(cells, start=1):
        day, details = build_day_from_cell(cell, tooltip_map)
        if not day:
            invalid_cells += 1
            logger.debug("Cell %d skipped: %s", index, details)
            continue
        deduped[day["date"]] = day
        logger.debug(
            "Cell %d captured: date=%s count=%d level=%d (%s)",
            index,
            day["date"],
            day["count"],
            day["level"],
            details,
        )

    days = [deduped[key] for key in sorted(deduped)]
    days.sort(key=lambda d: d["date"])

    total_contributions = sum(day["count"] for day in days)
    current_streak = calculate_current_streak(days)
    longest_streak = calculate_longest_streak(days)

    logger.info(
        "Parsed contributions for %s (%s → %s): cells=%d, unique_days=%d, invalid_cells=%d",
        username,
        from_date,
        to_date,
        cells_scanned,
        len(days),
        invalid_cells,
    )

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
