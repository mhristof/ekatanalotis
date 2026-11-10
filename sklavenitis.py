import html
import re

import catalog
import net

SECTIONS = [
    "eidi-artozacharoplasteioy",
    "freska-froyta-lachanika",
    "fresko-psari-thalassina",
    "fresko-kreas",
    "galata-rofimata-chymoi-psygeioy",
    "giaoyrtia-kremes-galaktos-epidorpia-psygeioy",
    "turokomika-futika-anapliromata",
    "ayga-voytyro-nopes-zymes-zomoi",
    "allantika",
    "orektika-delicatessen",
    "etoima-geymata",
    "katepsygmena",
    "kava",
    "anapsyktika-nera-chymoi",
    "xiroi-karpoi-snak",
    "mpiskota-sokolates-zacharodi",
    "eidi-proinoy-rofimata",
    "vrefikes-paidikes-trofes",
    "trofima-pantopoleioy",
    "trofes-eidi-gia-katoikidia",
    "eidi-mias-chrisis-eidi-parti",
    "chartika-panes-servietes",
    "kallyntika-eidi-prosopikis-ygieinis",
    "aporrypantika-eidi-katharismoy",
    "eidi-oikiakis-chrisis",
]

PRODUCT = re.compile(
    r"data-plugin-analyticsimpressions=.*?{&quot;item_id&quot;:&quot;(\d+)&quot;,&quot;item_name&quot;:&quot;(.*?)&quot;.*?price&quot;:(\d+\.\d+)",
    re.DOTALL,
)
BRAND = re.compile(r"&quot;item_brand&quot;:&quot;(.*?)&quot;")
CATEGORY = re.compile(r"&quot;item_category&quot;:&quot;(.*?)&quot;")
# <div class="priceKil">3,47 €<span>/λίτρο</span>
UNIT_PRICE = re.compile(r'class="priceKil">\s*([\d.,]+)[^<]*<span>([^<]*)</span>')


def field(regex, text):
    m = regex.search(text)

    return html.unescape(m.group(1)) if m else None


def parse(html_content):
    rows = []

    # one block per product tile
    for block in html_content.split("data-plugin-product=")[1:]:
        for code, name, price in PRODUCT.findall(block):
            unit_price = UNIT_PRICE.search(block)
            details = {
                # the price csv keeps the escaped name
                "name": html.unescape(name),
                "brand": field(BRAND, block),
                "category": field(CATEGORY, block),
            }

            if unit_price:
                details["unit_price"] = catalog.price(unit_price.group(1))
                details["unit"] = catalog.unit(unit_price.group(2))

            rows.append([code, name, float(price), details])

    return rows


def fetch_page(section, page):
    return parse(net.get_text(f"https://www.sklavenitis.gr/{section}/?pg={page}"))


def sklavenitis(sections=None, max_pages=None):
    return net.crawl("sklavenitis", sections or SECTIONS, fetch_page, max_pages)
