"""Public API for the GitHub contribution checker package."""

from .fetch import (
    ContributionDay,
    ContributionStats,
    build_stats_for_range,
    build_stats_from_single_html,
    collect_days_for_range,
    fetch_github_stats,
    resolve_username,
    save_html_dump,
    setup_logging,
)

__all__ = [
    "ContributionDay",
    "ContributionStats",
    "fetch_github_stats",
    "collect_days_for_range",
    "build_stats_for_range",
    "build_stats_from_single_html",
    "save_html_dump",
    "resolve_username",
    "setup_logging",
]
