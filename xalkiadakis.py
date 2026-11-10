import html
import time

import catalog
import net

# the site's bot protection (incapsula) sets a cookie on the first
# response and challenges every later request that sends it back; without
# cookies every request goes through
session = net.make_session(cookies=False)

# it also rate limits: ~90 requests back to back get blocked
DELAY = 2

# wait before retrying a page that got the challenge
RETRY_DELAY = 30

SECTIONS = [
    "kritika-prionta",
    "frouta-lachanika",
    "fresko-kreas-poulerika",
    "fresko-psari-thalassina",
    "etima-geumata",
    "proino-rofimata-snaks",
    "artozacharoplastio",
    "allantika-delicatessen",
    "galaktokomika-idi-psigiou",
    "tirokomika-fitika-anapliromata",
    "katepsigmena",
    "siskeuasmena-trofima",
    "pota-chimi-anapsiktika",
    "katikidia",
    "moro",
    "igia-omorfia",
    "ikiaki-frontida",
    "spiti-kouzina",
    "epochiaka",
    "proionta-prostasias",
    "vegan-corner",
    "vradies-mpalas",
]


def parse(text, category=None):
    rows = []
    price_in_next_line = False
    brand_in_next_line = False
    in_unit_price = False
    brand, unit_price = None, None

    for line in text.split("\n"):
        if "img src=" in line:
            try:
                uid = str(line.split("products/")[1].split("_")[0])
            except:
                uid = None

            brand, unit_price = None, None

        # <a class="product-brand-title ..."\n href="...">ORIENTAL EXPRESS</a>
        if 'class="product-brand-title' in line:
            brand_in_next_line = True
        elif brand_in_next_line:
            brand = html.unescape(line.split(">")[1].split("<")[0]).strip()
            brand_in_next_line = False

        if 'class="product-title"' in line:
            name = line.split('title="')[1].split('">')[0]

        # the old unit price is in a <del>, the current one in a <span>:
        # <span>0.18&euro;/τεμ.</span>
        if 'class="selling-unit-price"' in line:
            in_unit_price = True
        elif in_unit_price and "<span>" in line:
            value, _, unit = line.split("<span>")[1].split("</span>")[0].partition("&euro;")
            unit_price = (catalog.price(value), catalog.unit(unit))
            in_unit_price = False

        if price_in_next_line:
            price = float(line.split("&euro")[0].replace(",", "."))
            price_in_next_line = False

            if uid is None:
                raise Exception(f"name: {name}, price: {price}, uid is None")

            details = {"name": html.unescape(name), "brand": brand, "category": category}

            if unit_price:
                details["unit_price"], details["unit"] = unit_price

            rows.append([uid, name, price, details])

        if 'class="price"' in line:
            price_in_next_line = True
            in_unit_price = False

    return rows


def fetch_page(section, page):
    url = f"https://xalkiadakis.gr/category/{section}"

    if page > 1:
        url += f"?page={page}"

    # every page loads an _Incapsula_Resource script; the challenge page is a
    # stub without the site's own markup. it is sometimes served to a single
    # request, so try once more after a while
    for delay in [DELAY, RETRY_DELAY]:
        time.sleep(delay)
        text = net.get_text(url, session)

        if "_Incapsula_Resource" not in text or '<html lang="el">' in text:
            return parse(text, section)

    raise Exception(f"blocked by bot protection: {url}: {text[:300]!r}")


def xalkiadakis(sections=None, max_pages=None):
    # one request at a time, see DELAY
    rows = net.crawl(
        "xalkiadakis",
        sections or SECTIONS,
        fetch_page,
        max_pages,
        page_workers=1,
        section_workers=1,
    )

    prices = {}

    for uid, name, price, _ in rows:
        if prices.setdefault(uid, price) != price:
            raise Exception(
                f"uid: {uid}, name: {name}, price: {price}, old price: {prices[uid]}"
            )

    return rows
