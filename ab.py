import json

import net

# top level categories from the site navigation
SECTIONS = [f"{i:03}" for i in [*range(1, 15), 23, 25, 30, 31]]

PAGE_SIZE = 50
URL = "https://www.ab.gr/api/v1/"
# the site's own persisted query hash changes with every deploy, so send a
# minimal query instead; the CSRF protection needs the preflight header
QUERY = (
    "query GetCategoryProductSearch($lang:String$pageSize:Int$pageNumber:Int$category:String)"
    "{categoryProductSearch:categoryProductSearchV2(lang:$lang searchQuery:\":relevance\""
    " sort:\"relevance\" pageSize:$pageSize pageNumber:$pageNumber category:$category"
    " filterFlag:true plainChildCategories:false){products{code name url price{value}}}}"
)
HEADERS = {"apollo-require-preflight": "true"}


def parse(data):
    return [
        [p["code"], p["url"] if p["name"] == "." else p["name"], p["price"]["value"]]
        for p in data["data"]["categoryProductSearch"]["products"]
    ]


def fetch_page(category, page):
    variables = {
        "lang": "gr",
        "category": category,
        # the api pages from 0
        "pageNumber": page - 1,
        "pageSize": PAGE_SIZE,
    }
    params = {
        "operationName": "GetCategoryProductSearch",
        "query": QUERY,
        "variables": json.dumps(variables),
    }

    return parse(net.get(URL, params=params, headers=HEADERS).json())


def ab(sections=None, max_pages=None):
    rows = net.crawl("ab", sections or SECTIONS, fetch_page, max_pages)

    # products are listed under several categories; keep the first
    seen = {}

    for row in rows:
        seen.setdefault(row[0], row)

    return list(seen.values())
