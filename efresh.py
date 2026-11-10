import html
import json

import catalog
import net

SECTIONS = [
    "groceries",
    "drinks",
    "personal-care",
    "baby",
    "household",
    "clothing",
    "home",
    "biologika-proionta-bio-corner",
    "vegan-shop",
]

# products are json objects in the page's script, starting with
#   {"kodikos":"4200001851","title":"Beer Can, Fix (6x330ml) 5+1 Free",...
START = '{"kodikos":'


def products(text):
    decoder = json.JSONDecoder()
    i = text.find(START)

    while i >= 0:
        product, end = decoder.raw_decode(text, i)
        yield product
        i = text.find(START, end)


def details(p):
    attrs = p.get("attrs") or {}
    pkg_unit = (attrs.get("pkg_unit") or {}).get("title")
    categories = p.get("categories_data") or [{}]

    return {
        # the price csv keeps the escaped title
        "name": html.unescape(p["title"]),
        "brand": (attrs.get("developer_id") or {}).get("title"),
        "category": categories[0].get("title_el"),
        "size": f"{p['pkg_value']:g} {pkg_unit}" if p.get("pkg_value") and pkg_unit else None,
        "unit": catalog.unit(pkg_unit) if pkg_unit else None,
        "unit_price": round(p["price_per_unit"], 3) if p.get("price_per_unit") else None,
    }


def parse(text):
    return [
        [p["kodikos"], p["title"], float(p["price"]), details(p)]
        for p in products(text)
        if p.get("price")
    ]


def fetch_page(section, page):
    return parse(net.get_text(f"https://www.e-fresh.gr/en/{section}?page={page}"))


def efresh(sections=None, max_pages=None):
    return net.crawl("efresh", sections or SECTIONS, fetch_page, max_pages)
