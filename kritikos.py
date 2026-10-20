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


def parse(data):
    return [
        [item["sku"], item["displayName"], item["finalPrice"] / 10]
        for item in data["payload"]["products"]
    ]


def fetch_page(collection, page):
    if page > 1:
        return []

    params = {"collection_eq": collection, "eligible": "true"}

    return parse(net.get(URL, headers=HEADERS, params=params).json())


def kritikos(sections=None, max_pages=None):
    return net.crawl("kritikos", sections or SECTIONS, fetch_page, max_pages)
