import re

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

PRODUCT = re.compile(
    r'{"kodikos":"(?P<code>\d{10})","title":"(?P<name>[^"]+)".*?"price":(?P<price>\d+\.\d{2})',
    re.DOTALL,
)


def parse(text):
    return [
        [m.group("code"), m.group("name"), float(m.group("price"))]
        for m in PRODUCT.finditer(text)
    ]


def fetch_page(section, page):
    return parse(net.get_text(f"https://www.e-fresh.gr/en/{section}?page={page}"))


def efresh(sections=None, max_pages=None):
    return net.crawl("efresh", sections or SECTIONS, fetch_page, max_pages)
