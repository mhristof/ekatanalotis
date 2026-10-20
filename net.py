"""Shared HTTP session for all fetchers: retries with backoff, a timeout on
every request and a browser user agent."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT
_adapter = HTTPAdapter(
    # enough connections for the per-section and per-page thread pools
    pool_connections=32,
    pool_maxsize=32,
    max_retries=Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    ),
)
session.mount("http://", _adapter)
session.mount("https://", _adapter)


def get(url, **kwargs):
    response = session.get(url, timeout=TIMEOUT, **kwargs)
    response.raise_for_status()

    return response


def get_text(url, **kwargs):
    """Page body, or "" for a 404 (paging past the last page)."""
    try:
        return get(url, **kwargs).text
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return ""
        raise
