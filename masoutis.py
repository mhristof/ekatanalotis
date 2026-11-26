import functools
import math
import threading
import time

import catalog
import net

URL = "https://www.masoutis.gr/api/eshop/"
# the fixed key the site's own javascript sends with every request
PASS_KEY = "Sc@NnSh0p"
PAGE_SIZE = 50

# the api's reads are POSTs
session = net.make_session(methods=("GET", "POST"))
session.headers["Referer"] = "https://www.masoutis.gr/"

# the departments of the site menu; the other menu entries (offers, new,
# organic, vegan, ...) list products of these again
SECTIONS = {
    "566": "Μανάβικο",
    "565": "Κρεοπωλείο",
    "568": "Είδη Ψυγείου",
    "573": "Είδη Κατάψυξης",
    "564": "Υγιεινή Διατροφή",
    "574": "Κάβα",
    "579": "Snack-Ξηροί Καρποί",
    "544": "Πρωινά",
    "575": "Αρτοζαχαροπλαστείο",
    "571": "Ζαχαρώδη-Μπισκότα",
    "562": "Είδη Παντοπωλείου",
    "577": "Ζυμαρικά-Όσπρια",
    "563": "Dressing",
    "578": "Κονσερβοειδή",
    "545": "Βρεφική Φροντίδα",
    "570": "Προσωπική Περιποίηση",
    "576": "Υγιεινή-Χαρτικά",
    "572": "Είδη Καθαρισμού",
    "727": "Είδη Οικιακής",
    "567": "Κατοικίδια",
}

# the site gets new credentials after 30 minutes
CREDENTIALS_AGE = 20 * 60

_credentials = {}
_lock = threading.Lock()


def headers():
    """An anonymous visitor's Uid, Usl and Key, which every call needs."""
    with _lock:
        if time.monotonic() - _credentials.get("at", -math.inf) > CREDENTIALS_AGE:
            c = net.get(URL + "GetCred", session).json()
            _credentials.update(
                at=time.monotonic(), Uid=c["Uid"], Usl=c["Usl"], Key=c["Key"]
            )

        return {k: _credentials[k] for k in ("Uid", "Usl", "Key")}


def call(name, body):
    return net.post(URL + name, session, json=body, headers=headers()).json()


@functools.cache
def categories():
    """{subcategory code: name} from the site menu; a product's TeamId
    starts with its subcategory's code."""
    try:
        menu = call("GetScanNShopMenuAllLevelsAutoScheduler", {"PassKey": PASS_KEY})
    except Exception as e:
        print(f"[masoutis] menu: error {e!r}")

        return {}

    return {m["MenuItemcode"]: m["MenuItemDescr"].strip() for m in menu}


def details(item):
    # "1.05€/λιτ", "12.99€/κιλ"
    unit_price = item.get("ItemVolume") or ""
    brand = (item.get("BrandNameDesciption") or "").strip()

    return {
        "brand": None if brand == "NO BRAND" else brand,
        "category": categories().get((item.get("TeamId") or "")[:6])
        or item.get("breadcrumbLinkL2"),
        "unit": catalog.unit(unit_price.rpartition("/")[2]) if "/" in unit_price else None,
        "unit_price": catalog.price(unit_price),
    }


def parse(items):
    # PosPrice is the price now, StartPrice the one before an offer;
    # weighed products are priced per kg
    return [
        [item["Itemcode"], item["ItemDescr"].strip(), item["PosPrice"], details(item)]
        for item in items
        if item.get("PosPrice")
    ]


# {section: product count}, so pages past the last are not requested
_totals = {}


def fetch_page(section, page):
    if section in _totals and page > math.ceil(_totals[section] / PAGE_SIZE):
        return []

    body = {
        "PassKey": PASS_KEY,
        # "<department>" or "<department>,<subcategory>"
        "Itemcode": section,
        # the sort order
        "ItemDescr": "0",
        # the page number, from 1
        "IfWeight": str(page),
        "ServiceResponse": "",
        "Token": "",
        "Zip": "",
        "BrandName": "",
        "TeamId": "",
        "ExtraFilter": "",
    }
    items = call("GetPromoItemWithListCouponsSubCategoriesAutoPromosv2", body) or []

    if items:
        # every item carries the section's product count
        _totals[section] = items[0].get("PassKey") or 0

    if page > math.ceil(_totals.get(section, 0) / PAGE_SIZE):
        return []

    return parse(items)


def masoutis(sections=None, max_pages=None):
    rows = net.crawl(
        "masoutis",
        sections or list(SECTIONS),
        fetch_page,
        max_pages,
        page_workers=2,
        label=lambda section: f"{section} {SECTIONS.get(section, '')}".strip(),
    )

    # a product can be in more than one department; keep the first
    seen = {}

    for row in rows:
        seen.setdefault(row[0], row)

    return list(seen.values())
