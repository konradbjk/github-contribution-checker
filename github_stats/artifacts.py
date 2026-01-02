"""Helpers for persisting raw GitHub contribution artifacts."""

from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def build_html_dump_path(base: Path | None, suffix: str) -> Path | None:
    """Return a derived path for saving HTML."""
    if base is None:
        return None
    suffix = suffix.replace("/", "_")
    stem = base.stem
    new_suffix = base.suffix or ".html"
    new_name = f"{stem}-{suffix}{new_suffix}"
    return base.with_name(new_name)


def save_html_dump(base: Path | None, suffix: str | None, html: str) -> None:
    """Persist HTML content using a derived path."""
    if base is None:
        return
    target = base if not suffix else build_html_dump_path(base, suffix)
    if target is None:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(html, encoding="utf-8")
        logger.info("Saved raw HTML to %s (%d bytes)", target, len(html))
    except OSError as exc:
        logger.error("Failed to save raw HTML to %s: %s", target, exc)
