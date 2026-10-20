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


def parse(text):
    rows = []

    # every {...} block on the page; the product ones are js objects
    for part in re.findall(r"\{.*?\}", text, re.DOTALL):
        part = part.replace("'", '"').replace("\n", "").replace(",}", "}")

        try:
            data = json.loads(part)
        except:
            continue

        if "price" not in data:
            continue

        rows.append([data["id"], data["name"], float(data["price"])])

    return rows


def fetch_page(section, page):
    return parse(net.get_text(f"https://www.market-in.gr/el-gr/{section}?pageno={page}"))


def marketin(sections=None, max_pages=None):
    return net.crawl("marketin", sections or SECTIONS, fetch_page, max_pages)
