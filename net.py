"""Shared HTTP session for all fetchers: retries with backoff, a timeout on
every request and a browser user agent."""

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import DefaultCookiePolicy
from itertools import islice

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"



def make_session(cookies=True):
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT

    if not cookies:
        s.cookies.set_policy(DefaultCookiePolicy(allowed_domains=[]))

    adapter = HTTPAdapter(
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
    s.mount("http://", adapter)
    s.mount("https://", adapter)

    return s


session = make_session()


def get(url, session=session, **kwargs):
    response = session.get(url, timeout=TIMEOUT, **kwargs)
    response.raise_for_status()

    return response


def get_text(url, session=session, **kwargs):
    """Page body, or "" for a 404 (paging past the last page)."""
    try:
        return get(url, session, **kwargs).text
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return ""
        raise


# hard stop for paging, in case a site keeps returning products
MAX_PAGES = 998


# pages fetched ahead per section, and sections fetched at once per store,
# so at most PAGE_WORKERS * SECTION_WORKERS requests in flight per store
PAGE_WORKERS = 4
SECTION_WORKERS = 4


def paginate(fetch_page, max_pages=None, workers=PAGE_WORKERS):
    """Call fetch_page(page) for page 1, 2, ... until it returns no rows.

    Keeps `workers` pages in flight; rows are returned in page order."""
    pages = iter(range(1, (max_pages or MAX_PAGES) + 1))
    rows = []

    with ThreadPoolExecutor(workers) as executor:
        pending = deque(executor.submit(fetch_page, p) for p in islice(pages, workers))

        try:
            while pending:
                this = pending.popleft().result()

                if not this:
                    break

                rows += this
                pending.extend(executor.submit(fetch_page, p) for p in islice(pages, 1))
        finally:
            for future in pending:
                future.cancel()

    return rows


def crawl(
    name,
    sections,
    fetch_page,
    max_pages=None,
    page_workers=PAGE_WORKERS,
    section_workers=SECTION_WORKERS,
):
    """Paginate every section; fetch_page(section, page) returns rows."""

    def one(section):
        try:
            this = paginate(
                lambda page: fetch_page(section, page), max_pages, page_workers
            )
        except Exception as e:
            # keep the other sections; a big drop fails sm.validate()
            print(f"[{name}] {section}: error {e!r}")

            return []

        print(f"[{name}] {section}: {len(this)} items")

        return this

    with ThreadPoolExecutor(section_workers) as executor:
        return [row for rows in executor.map(one, sections) for row in rows]
