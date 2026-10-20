import json
import re

import net

SECTIONS = [
    "kreopoleio-1",
    "manabikh",
    "trofima",
    "kava",
    "vrefika",
    "turokomika-allantika",
    "galaktokomika-proionta-psugeiou",
    "katepsugmena",
    "prosopikh-frontida",
    "kathariothta",
    "ola-gia-to-spiti",
    "katoikidia",
]


# products are listed as google analytics impressions:
#   ga('ec:addImpression', {'id': '1', 'name': '...', 'price': '4.49', ...});
IMPRESSION = re.compile(r"ga\('ec:addImpression',\s*(\{.*?\})\);", re.DOTALL)


def parse(text):
    rows = []

    for part in IMPRESSION.findall(text):
        part = part.replace("'", '"').replace("\n", "").replace(",}", "}")

        try:
            data = json.loads(part)
        except ValueError:
            continue

        if "price" not in data:
            continue

        rows.append([data["id"], data["name"], float(data["price"])])

    return rows


def fetch_page(section, page):
    return parse(net.get_text(f"https://www.market-in.gr/el-gr/{section}?pageno={page}"))


def marketin(sections=None, max_pages=None):
    return net.crawl("marketin", sections or SECTIONS, fetch_page, max_pages)
