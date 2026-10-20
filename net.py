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


# hard stop for paging, in case a site keeps returning products
MAX_PAGES = 998


def paginate(fetch_page, max_pages=None):
    """Call fetch_page(page) for page 1, 2, ... until it returns no rows."""
    rows = []

    for page in range(1, (max_pages or MAX_PAGES) + 1):
        this = fetch_page(page)

        if not this:
            break

        rows += this

    return rows


def crawl(name, sections, fetch_page, max_pages=None):
    """Paginate every section; fetch_page(section, page) returns rows."""
    rows = []

    for section in sections:
        try:
            this = paginate(lambda page: fetch_page(section, page), max_pages)
        except Exception as e:
            # keep the other sections; a big drop fails sm.validate()
            print(f"[{name}] {section}: error {e!r}")

            continue

        print(f"[{name}] {section}: {len(this)} items")
        rows += this

    return rows
