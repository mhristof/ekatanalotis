"""Smoke tests: run every fetcher against the live site for a single
section and a single page, and check the rows look sane."""

import pytest

from ab import ab
from efresh import efresh
from kritikos import kritikos
from mymarket import mymarket
from sklavenitis import sklavenitis
from marketin import marketin
from xalkiadakis import xalkiadakis

# store -> (fetcher, one section)
STORES = {
    "ab": (ab, ["001"]),
    "efresh": (efresh, ["groceries"]),
    "kritikos": (kritikos, ["900"]),
    "marketin": (marketin, ["kava"]),
    "mymarket": (mymarket, ["trofima"]),
    "sklavenitis": (sklavenitis, ["kava"]),
    "xalkiadakis": (xalkiadakis, ["moro"]),
}

# stores whose bot protection blocks some IPs (GitHub runners, or any IP
# after too many requests); reported as XPASS when they do work
BLOCKED = {"sklavenitis", "xalkiadakis"}


@pytest.mark.network
@pytest.mark.parametrize("store", STORES)
def test_fetcher(store, request):
    if store in BLOCKED:
        request.applymarker(pytest.mark.xfail(reason="may be blocked by bot protection"))

    fetcher, sections = STORES[store]
    rows = fetcher(sections=sections, max_pages=1)

    assert rows, f"{store} returned no rows"

    for row in rows:
        assert len(row) == 3, row
        code, name, price = row
        assert str(code).strip(), row
        assert str(name).strip(), row
        assert float(price) > 0, row
