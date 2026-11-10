import catalog
import net

URL = "https://kritikos-cxm-production.herokuapp.com/api/v2/products"
HEADERS = {
    "appId": "kritikos-web",
    "sec-ch-ua-platform": '"macOS"',
    "Referer": "https://kritikos-sm.gr/",
    "Accept": "application/json, text/plain, */*",
    "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
}

# the api returns a whole collection in one response
SECTIONS = ["900"]


def details(item):
    category = item.get("category") or {}

    return {
        # displayName is often just the brand, name has the product and size
        "name": item.get("name"),
        "brand": item.get("brand"),
        "category": item.get("categoryKind") or category.get("name"),
        "size": item.get("quantity"),
        "unit": catalog.unit(item.get("unitOfMeasurement")),
        "unit_price": (item.get("unitOfMeasurementFinalPrice") or 0) / 100 or None,
        # old and multipack barcodes are listed too
        "ean": catalog.eans(item.get("barcodes") or []),
    }


def parse(data):
    # prices are in cents
    return [
        [item["sku"], item["displayName"], item["finalPrice"] / 100, details(item)]
        for item in data["payload"]["products"]
    ]


def fetch_page(collection, page):
    if page > 1:
        return []

    params = {"collection_eq": collection, "eligible": "true"}

    return parse(net.get(URL, headers=HEADERS, params=params).json())


def kritikos(sections=None, max_pages=None):
    return net.crawl("kritikos", sections or SECTIONS, fetch_page, max_pages)
