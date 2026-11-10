import html
import json
import re

import catalog
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


# the product tiles, in the same order as the impressions; they have the
# name with spaces (the impressions replace them with dashes) and the unit
# price: <span ...>0,33€/τεμ</span>
TILE_TITLE = re.compile(r'class="product-ttl">([^<]*)</a>')
TILE_UNIT_PRICE = re.compile(r'class="kg-price-weight">\s*<span>\s*<span[^>]*>([^<]*)</span>')
# weighed products have no unit price, the price is for a default weight:
# <span class="new-price ...">0,59 €<span ...> / 600 γρ.</span></span>
TILE_SIZE = re.compile(r'class="new-price[^"]*">[^<]*<span[^>]*>\s*/\s*([^<]+?)\s*</span>')
GRAMS = re.compile(r"(\d+)\s*γρ")
# or the tile shows the price per kilo: <span class="new-price ...">1,69€ / κιλό</span>
TILE_PRICE_PER = re.compile(r'class="new-price[^"]*">\s*([\d.,]+)\s*€\s*/\s*([^<]+?)\s*</span>')


def tiles(text):
    out = []

    for tile in text.split('class="product-item"')[1:]:
        title = TILE_TITLE.search(tile)
        unit_price = TILE_UNIT_PRICE.search(tile)
        size = TILE_SIZE.search(tile)
        value, _, unit = unit_price.group(1).partition("/") if unit_price else ("", "", "")

        if not value and (price_per := TILE_PRICE_PER.search(tile)):
            value, unit = price_per.groups()
        out.append(
            {
                "name": html.unescape(title.group(1)).strip() if title else None,
                "unit_price": catalog.price(value),
                "unit": catalog.unit(unit) if unit else None,
                "size": size.group(1) if size else None,
            }
        )

    return out


def squash(name):
    # the impressions also replace punctuation: "M&M'S" -> "M_M-S"
    return re.sub(r"[\W_]", "", name or "")


def details(data):
    return {
        "brand": data.get("brand", "").replace("-", " "),
        # "ΤΡΟΦΙΜΑ-|-ΑΥΓΑ-|-Αυγά"
        "category": data.get("category", "").split("-|-")[-1].replace("-", " "),
    }


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

        rows.append([data["id"], data["name"], float(data["price"]), details(data)])

    page_tiles = tiles(text)

    # without a common key, only trust the order when the counts and the
    # names agree
    if len(page_tiles) == len(rows):
        for row, tile in zip(rows, page_tiles):
            if squash(row[1]) == squash(tile["name"]):
                row[3].update({k: v for k, v in tile.items() if v})

    for row in rows:
        grams = GRAMS.match(row[3].get("size") or "")

        if grams and not row[3].get("unit_price"):
            row[3].update(unit_price=round(row[2] * 1000 / int(grams.group(1)), 2), unit="kg")

    return rows


def fetch_page(section, page):
    return parse(net.get_text(f"https://www.market-in.gr/el-gr/{section}?pageno={page}"))


def marketin(sections=None, max_pages=None):
    return net.crawl("marketin", sections or SECTIONS, fetch_page, max_pages)
