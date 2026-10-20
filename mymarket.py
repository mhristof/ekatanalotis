import html
import json

from bs4 import BeautifulSoup

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


def parse(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    rows = []

    for article in soup.find_all("article", {"data-controller": "google-analytics"}):
        data_values = article.get("data-google-analytics-item-value")

        if data_values:
            data = json.loads(data_values.replace("&quot;", '"'))
            price = round(float(data.get("price", "N/A")), 2)
            rows.append(
                [data.get("id", "N/A"), html.unescape(data.get("name", "N/A")), f"{price:.2f}"]
            )

    return rows


def fetch_page(section, page):
    url = f"https://www.mymarket.gr/{section}"

    if page > 1:
        url += f"?page={page}"

    return parse(net.get_text(url))


def mymarket(sections=None, max_pages=None):
    return net.crawl("mymarket", sections or SECTIONS, fetch_page, max_pages)
