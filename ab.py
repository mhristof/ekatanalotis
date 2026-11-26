import json
import re

import catalog
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
    " filterFlag:true plainChildCategories:false){products{code name url manufacturerName"
    " categories{name} price{value supplementaryPriceLabel1 supplementaryPriceLabel2}}}}"
)
HEADERS = {"apollo-require-preflight": "true"}
# the site search finds a product by its EAN
SEARCH_QUERY = (
    "query GetProductSearch($lang:String$searchQuery:String$pageSize:Int$pageNumber:Int)"
    "{productSearch:productSearchV2(lang:$lang searchQuery:$searchQuery pageSize:$pageSize"
    " pageNumber:$pageNumber sort:\"relevance\"){products{code name url manufacturerName"
    " categories{name} price{value supplementaryPriceLabel1 supplementaryPriceLabel2}}}}"
)


# ab lists some products as a fraction of a piece ("0,09 τεμ", "17,11 €/
# τεμ") when it means kg or l: the name has the real size ("... 90g")
FRACTION_OF_A_PIECE = re.compile(r"^0[.,]\d+\s*τεμ")
NAME_SIZE = re.compile(r"\d+(?:[.,]\d+)?\s*(kg|κιλ|g|gr|γρ|ml|lt|l|λιτ)\b", re.IGNORECASE)


def fix_unit(name, details):
    """kg or l for a unit price ab gives per piece of a fractional piece,
    from the size in the name; keeps ab's unit in unit_fixed."""
    m = NAME_SIZE.search(name or "")

    if details.get("unit") != "piece" or not FRACTION_OF_A_PIECE.match(details.get("size") or "") or not m:
        return details

    unit = "kg" if m.group(1).lower() in ("kg", "κιλ", "g", "gr", "γρ") else "l"
    amount = (details["size"] or "").split()[0]

    return {
        **details,
        "unit": unit,
        "size": f"{amount} {'κιλ' if unit == 'kg' else 'λιτ'}",
        "unit_fixed": "piece",
    }


def details(p):
    # "1,46 €/ κιλ" and the pack size "500 γρ", or "~1 κιλ" for weighed ones
    unit_price = p["price"].get("supplementaryPriceLabel1") or ""
    categories = p.get("categories") or [{}]

    return fix_unit(
        p.get("name"),
        {
            # the name has no brand, "-" when there is none
            "brand": (p.get("manufacturerName") or "").strip("- "),
            "category": categories[-1].get("name"),
            "size": p["price"].get("supplementaryPriceLabel2"),
            "unit": catalog.unit(unit_price.rpartition("/")[2]) if unit_price else None,
            "unit_price": catalog.price(unit_price),
        },
    )


def parse(data, field="categoryProductSearch"):
    return [
        [
            p["code"],
            p["url"] if p["name"] == "." else p["name"],
            p["price"]["value"],
            details(p),
        ]
        for p in data["data"][field]["products"]
    ]


def query(params):
    # since 2026-11-19 the api also wants the operation name as a header
    headers = {**HEADERS, "x-apollo-operation-name": params["operationName"]}

    return net.get(URL, params=params, headers=headers).json()


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

    return parse(query(params))


def ab(sections=None, max_pages=None):
    rows = net.crawl("ab", sections or SECTIONS, fetch_page, max_pages)

    # products are listed under several categories; keep the first
    seen = {}

    for row in rows:
        seen.setdefault(row[0], row)

    return list(seen.values())


def search(text):
    """Rows for the products the site search finds for text, e.g. an EAN."""
    variables = {"lang": "gr", "searchQuery": text, "pageNumber": 0, "pageSize": 5}
    params = {
        "operationName": "GetProductSearch",
        "query": SEARCH_QUERY,
        "variables": json.dumps(variables),
    }

    return parse(query(params), "productSearch")
