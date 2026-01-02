"""Helpers for resolving contribution date ranges."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum


class RangeMode(str, Enum):
    """Supported built-in range presets."""

    LAST_365 = "last_365"
    CURRENT_YEAR = "current_year"


@dataclass(frozen=True)
class RangeSelection:
    """Resolved contribution range metadata."""

    start_date: date
    end_date: date
    description: str
    use_rolling_endpoint: bool = False


def parse_date_input(value: str) -> date:
    """Parse ISO date or Unix timestamp (seconds or milliseconds)."""
    raw = value.strip()
    if not raw:
        raise ValueError("Date input cannot be empty")

    try:
        return date.fromisoformat(raw)
    except ValueError:
        try:
            timestamp = float(raw)
        except ValueError as exc:
            raise ValueError(f"Invalid date input: {value}") from exc

        # Assume milliseconds if the timestamp is too large.
        if timestamp > 2_000_000_000:
            timestamp /= 1000.0

        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()


def year_bounds(year: int) -> tuple[date, date]:
    """Return start/end dates for a calendar year."""
    return date(year, 1, 1), date(year, 12, 31)


def build_default_range(mode: RangeMode) -> RangeSelection:
    """Build default selections for built-in presets."""
    today = date.today()

    if mode is RangeMode.CURRENT_YEAR:
        start, end = date(today.year, 1, 1), today
        return RangeSelection(start, end, description="current_year")

    if mode is RangeMode.LAST_365:
        start, end = today - timedelta(days=365), today
        return RangeSelection(start, end, description="last_365", use_rolling_endpoint=True)

    raise ValueError(f"Unsupported range mode: {mode}")


def resolve_selection(
    range_type: str,
    year: int | None,
    from_input: str | None,
    to_input: str | None,
) -> RangeSelection:
    """Resolve CLI inputs into a concrete range selection."""

    if (from_input is not None) ^ (to_input is not None):
        raise ValueError("Both --from-date and --to-date must be provided together.")

    if from_input and to_input and year is not None:
        raise ValueError("Use either --year or --from-date/--to-date, not both.")

    if from_input and to_input:
        start = parse_date_input(from_input)
        end = parse_date_input(to_input)
        if start > end:
            start, end = end, start
        return RangeSelection(start, end, description="custom range")

    if year is not None:
        start, end = year_bounds(year)
        return RangeSelection(start, end, description=f"year {year}")

    try:
        mode = RangeMode(range_type)
    except ValueError as exc:
        raise ValueError(f"Unsupported range type: {range_type}") from exc

    return build_default_range(mode)


def split_into_year_windows(start: date, end: date) -> list[tuple[date, date]]:
    """Split a date range into calendar-year windows (inclusive)."""
    if start > end:
        start, end = end, start

    windows: list[tuple[date, date]] = []
    current_start = start
    while current_start <= end:
        year_end = date(current_start.year, 12, 31)
        current_end = min(year_end, end)
        windows.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)
    return windows
