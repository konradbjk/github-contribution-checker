"""HTTP helpers for fetching GitHub contribution calendars."""

import logging

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0"


def _build_client(session: httpx.Client | None, headers: dict[str, str]) -> tuple[httpx.Client, bool]:
    should_close = session is None
    if session:
        return session, False
    return httpx.Client(headers=headers, follow_redirects=True), True


def fetch_contributions_html(username: str, from_date: str, to_date: str, session: httpx.Client | None = None) -> str:
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
        "User-Agent": USER_AGENT,
        "Accept": "text/html",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{url}?tab=contributions",
    }

    client, should_close = _build_client(session, headers)
    logger.info(
        "Requesting contributions for %s: url=%s params=%s headers=%s",
        username,
        url,
        params,
        {"User-Agent": headers["User-Agent"], "Referer": headers["Referer"]},
    )

    try:
        response = client.get(url, params=params)
        response.raise_for_status()
        logger.info(
            "Response for %s: status=%s length=%d final_url=%s",
            username,
            response.status_code,
            len(response.text),
            str(response.url),
        )
        return response.text
    finally:
        if should_close:
            client.close()


def fetch_last365_html(username: str, session: httpx.Client | None = None) -> str:
    """Fetch the rolling last-365-days contribution HTML."""
    url = f"https://github.com/{username}"
    params = {
        "action": "show",
        "controller": "profiles",
        "tab": "contributions",
        "user_id": username,
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://github.com/{username}?tab=overview",
    }

    client, should_close = _build_client(session, headers)
    logger.info("Requesting rolling last_365 data for %s", username)
    try:
        response = client.get(url, params=params)
        response.raise_for_status()
        logger.info(
            "Rolling response for %s: status=%s length=%d final_url=%s",
            username,
            response.status_code,
            len(response.text),
            str(response.url),
        )
        return response.text
    finally:
        if should_close:
            client.close()
