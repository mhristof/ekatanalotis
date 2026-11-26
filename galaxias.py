import catalog
import net

# the site's own proxy of its magento graphql api; reads are GETs
URL = "https://galaxias.shop/api/graphql"
HEADERS = {"Referer": "https://galaxias.shop/"}
PAGE_SIZE = 300

# the top level categories of the menu
SECTIONS = {
    "59": "Τρόφιμα",
    "69": "Είδη Ψυγείου",
    "194": "Τυριά, Αλλαντικά",
    "95": "Κατεψυγμένα",
    "66": "Έτοιμα Γεύματα",
    "104": "Σνακς",
    "68": "Είδη Πρωϊνού",
    "1080515": "Ροφήματα",
    "103": "Αρτοποιείο",
    "89": "Αναψυκτικά, Χυμοί",
    "88": "Κάβα",
    "788": "Βρεφικές Τροφές",
    "342": "Μαναβική",
    "93": "Ψαρικά, Κρέας",
    "75": "Προσωπική Υγιεινή",
    "64": "Απορρυπαντικά",
    "72": "Οικιακής Χρήσης",
    "245": "Είδη Πάρτι",
    "86": "Κατοικίδια",
}

# sorted by name, so pages don't shift between requests
QUERY = (
    '{products(filter:{category_id:{eq:"%s"}} pageSize:%d currentPage:%d sort:{name:ASC})'
    "{page_info{total_pages} items{sku name unit_measurement cost_per_unit"
    " categories{name level} price_range{minimum_price{final_price{value}}}}}}"
)


def details(item):
    # the deepest of the product's categories
    categories = sorted(item.get("categories") or [], key=lambda c: c.get("level") or 0)
    unit_price = item.get("cost_per_unit")

    return {
        "category": categories[-1]["name"] if categories else None,
        # "Κιλό", "Λίτρο", "Τεμάχιο"; null when there is no unit price
        "unit": catalog.unit(item.get("unit_measurement")) if unit_price else None,
        "unit_price": round(float(unit_price), 2) if unit_price else None,
        # the sku is the product's barcode
        "ean": catalog.eans([item["sku"]]),
    }


def parse(data):
    items = ((data.get("data") or {}).get("products") or {}).get("items") or []

    return [
        [
            item["sku"],
            item["name"].strip(),
            item["price_range"]["minimum_price"]["final_price"]["value"],
            details(item),
        ]
        for item in items
        if item["price_range"]["minimum_price"]["final_price"]["value"]
    ]


# {section: pages}, so pages past the last are not requested
_pages = {}


def fetch_page(section, page):
    if page > _pages.get(section, page):
        return []

    data = net.get(URL, params={"query": QUERY % (section, PAGE_SIZE, page)}, headers=HEADERS).json()
    products = (data.get("data") or {}).get("products")

    # past the last page magento answers with an error and no products
    if not products:
        return []

    _pages[section] = products["page_info"]["total_pages"]

    return parse(data)


def galaxias(sections=None, max_pages=None):
    rows = net.crawl(
        "galaxias",
        sections or list(SECTIONS),
        fetch_page,
        max_pages,
        page_workers=2,
        label=lambda section: f"{section} {SECTIONS.get(section, '')}".strip(),
    )

    # a product can be in more than one category; keep the first
    seen = {}

    for row in rows:
        seen.setdefault(row[0], row)

    return list(seen.values())
