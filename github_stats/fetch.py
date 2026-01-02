"""High-level API for fetching GitHub contribution statistics."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
import logging

import httpx

from .artifacts import save_html_dump as _save_html_dump
from .logging_utils import setup_logging as _setup_logging
from .parsing import ContributionDay, ContributionStats
from .selectors import resolve_selection
from .stats_builder import (
    build_stats_for_range,
    build_stats_from_single_html,
    collect_days_for_range as _collect_days_for_range,
)

DateRangeType = Literal["last_365", "current_year"]

logger = logging.getLogger(__name__)

setup_logging = _setup_logging
save_html_dump = _save_html_dump
collect_days_for_range = _collect_days_for_range

__all__ = [
    "ContributionDay",
    "ContributionStats",
    "DateRangeType",
    "build_stats_for_range",
    "build_stats_from_single_html",
    "collect_days_for_range",
    "fetch_github_stats",
    "resolve_username",
    "save_html_dump",
    "setup_logging",
]


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

    if "github.com" in text:
        return extract_username(f"https://{text.lstrip('/')}")

    normalized = text.strip("/")
    if not normalized:
        raise ValueError("Invalid username input")

    return normalized


def fetch_github_stats(
    profile: str,
    range_type: DateRangeType = "last_365",
    session: httpx.Client | None = None,
    save_html_path: Path | str | None = None,
    year: int | None = None,
    from_date_override: str | None = None,
    to_date_override: str | None = None,
) -> ContributionStats:
    """Fetch and parse GitHub contribution statistics for a given profile."""
    username = resolve_username(profile)
    html_base = Path(save_html_path) if save_html_path else None
    logger.info("Resolved profile %s → %s", profile, username)

    selection = resolve_selection(range_type, year, from_date_override, to_date_override)

    if selection.use_rolling_endpoint:
        return build_stats_from_single_html(
            username,
            selection,
            session=session,
            html_base=html_base,
        )

    return build_stats_for_range(
        username,
        selection.start_date,
        selection.end_date,
        session,
        html_base,
        description=selection.description,
    )
