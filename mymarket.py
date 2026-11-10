import html
import json
import re

import catalog
import net

SECTIONS = [
    "frouta-lachanika",
    "fresko-kreas-psari",
    "galaktokomika-eidi-psygeiou",
    "tyria-allantika-deli",
    "katepsygmena-trofima",
    "mpyres-anapsyktika-krasia-pota",
    "proino-rofimata-kafes",
    "artozacharoplasteio-snacks",
    "trofima",
    "frontida-gia-to-moro-sas",
    "prosopiki-frontida",
    "oikiaki-frontida-chartika",
    "kouzina-mikrosyskeves-spiti",
    "frontida-gia-to-katoikidio-sas",
    "epochiaka",
]


ARTICLE = re.compile(r"<article\b([^>]*)>(.*?)</article>", re.DOTALL)
ITEM_VALUE = re.compile(r'data-google-analytics-item-value="([^"]*)"')
# <span class="font-semibold">1,05€</span> <span>Τιμή λίτρου</span>
UNIT_PRICE = re.compile(
    r'class="measure-label-wrapper">\s*<span[^>]*>([^<]*)</span>\s*<span>([^<]*)</span>'
)


def details(data, body):
    unit_price = UNIT_PRICE.search(body)
    categories = [data.get(k) for k in ("category", "category2", "category3")]

    return {
        "brand": data.get("brand"),
        "category": next((c for c in reversed(categories) if c), None),
        "unit_price": catalog.price(unit_price.group(1)) if unit_price else None,
        "unit": catalog.unit(unit_price.group(2)) if unit_price else None,
    }


def parse(html_content):
    rows = []

    for attrs, body in ARTICLE.findall(html_content):
        if 'data-controller="google-analytics"' not in attrs:
            continue

        value = ITEM_VALUE.search(attrs)

        if not value:
            continue

        data = json.loads(html.unescape(value.group(1)))
        price = round(float(data.get("price", "N/A")), 2)
        rows.append(
            [
                data.get("id", "N/A"),
                html.unescape(data.get("name", "N/A")),
                f"{price:.2f}",
                details(data, body),
            ]
        )

    return rows


def fetch_page(section, page):
    url = f"https://www.mymarket.gr/{section}"

    if page > 1:
        url += f"?page={page}"

    return parse(net.get_text(url))


def mymarket(sections=None, max_pages=None):
    return net.crawl("mymarket", sections or SECTIONS, fetch_page, max_pages)
