import net

PAGE_SIZE = 30
URL = "https://www.ab.gr/api/v1/?operationName=GetCategoryProductSearch&variables=%7B%22lang%22%3A%22gr%22%2C%22searchQuery%22%3A%22%3Arelevance%22%2C%22sort%22%3A%22relevance%22%2C%22category%22%3A%22{category}%22%2C%22pageNumber%22%3A{page}%2C%22pageSize%22%3A{page_size}%2C%22filterFlag%22%3Atrue%2C%22plainChildCategories%22%3Afalse%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22dd8d3de806d7e82af7e29b491a30df5a93d2c27c04190ef25ab973cbfe913079%22%7D%7D"


def fetch_page(category, page):
    # the api pages from 0
    url = URL.format(category=category, page=page - 1, page_size=PAGE_SIZE)
    products = net.get(url).json()["data"]["categoryProductSearch"]["products"]

    return [
        [p["code"], p["url"] if p["name"] == "." else p["name"], p["price"]["value"]]
        for p in products
    ]


def all_categories(max_pages=None):
    """Walk category codes 001, 002, ... until 10 in a row are empty."""
    rows = []
    empty = 0

    for category in (f"{i:03}" for i in range(1, 1000)):
        try:
            this = net.paginate(lambda page: fetch_page(category, page), max_pages)
        except Exception as e:
            print(f"[ab] {category}: error {e!r}")
            this = []

        empty = 0 if this else empty + 1

        if empty > 10:
            break

        rows += this

    return rows


def ab(sections=None, max_pages=None):
    if sections:
        rows = net.crawl("ab", sections, fetch_page, max_pages)
    else:
        rows = all_categories(max_pages)

    # products are listed under several categories; keep the first
    seen = {}

    for row in rows:
        seen.setdefault(row[0], row)

    return list(seen.values())
