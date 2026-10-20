import time

import net

# the site's bot protection (incapsula) sets a cookie on the first
# response and challenges every later request that sends it back; without
# cookies every request goes through
session = net.make_session(cookies=False)

# it also rate limits: ~90 requests back to back get blocked
DELAY = 2

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


def parse(text):
    rows = []
    price_in_next_line = False

    for line in text.split("\n"):
        if "img src=" in line:
            try:
                uid = str(line.split("products/")[1].split("_")[0])
            except:
                uid = None

        if 'class="product-title"' in line:
            name = line.split('title="')[1].split('">')[0]

        if price_in_next_line:
            price = float(line.split("&euro")[0].replace(",", "."))
            price_in_next_line = False

            if uid is None:
                raise Exception(f"name: {name}, price: {price}, uid is None")

            rows.append([uid, name, price])

        if 'class="price"' in line:
            price_in_next_line = True

    return rows


def fetch_page(section, page):
    url = f"https://xalkiadakis.gr/category/{section}"

    if page > 1:
        url += f"?page={page}"

    time.sleep(DELAY)
    text = net.get_text(url, session)

    if "_Incapsula_Resource" in text:
        raise Exception(f"blocked by bot protection: {url}")

    return parse(text)


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

    for uid, name, price in rows:
        if prices.setdefault(uid, price) != price:
            raise Exception(
                f"uid: {uid}, name: {name}, price: {price}, old price: {prices[uid]}"
            )

    return rows
