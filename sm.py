#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

"""

import os
import subprocess
import sys
import requests
import re
import json
import datetime
import html
from bs4 import BeautifulSoup

from mymarket import mymarket
from efresh import efresh
from sklavenitis import sklavenitis
from ab import ab
from kritikos import kritikos


def save_to_file(sms, today):
    # smdata/ is not checked out in CI (sparse checkout)
    os.makedirs("smdata", exist_ok=True)

    for sm, data in sms.items():
        # sorted and without exact duplicates (stores list products in
        # more than one section) so that day-to-day diffs stay small
        lines = sorted(
            {f"{today},{item[0]},{item[1].replace(',', '-')},{item[2]}\n" for item in data},
            key=lambda line: line.split(",", 2)[1],
        )

        with open(f"smdata/{sm}-{today}.csv", "w") as f:
            f.writelines(lines)
            print(f"saved {len(lines)} items to {sm}.csv")


# a store returning less than this fraction of its previous row count is
# treated as a failed scrape
MIN_ROWS_RATIO = 0.5


def previous_count(sm, today):
    """Row count of the most recent non-empty csv for sm before today.

    Read through git so it works on the sparse CI checkout, where smdata/
    is not in the working tree; only the blobs read are fetched."""
    try:
        names = subprocess.run(
            ["git", "ls-tree", "--name-only", "HEAD", "smdata/"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return None

    names = sorted(
        n for n in names if n.startswith(f"smdata/{sm}-2") and n < f"smdata/{sm}-{today}"
    )

    for name in reversed(names[-30:]):
        data = subprocess.run(
            ["git", "show", f"HEAD:{name}"], capture_output=True, text=True
        ).stdout

        if data:
            return data.count("\n")

    return None


def validate(sms, today):
    """Drop stores that returned no or suspiciously few rows; return the
    names of the stores that failed."""
    failed = []

    for sm, data in list(sms.items()):
        prev = previous_count(sm, today)
        print(f"{sm}: {len(data)} rows, previous: {prev}")

        if not data or (prev and len(data) < prev * MIN_ROWS_RATIO):
            print(f"error in {sm}: got {len(data)} rows, previous run had {prev}")
            failed.append(sm)
            del sms[sm]

    return failed


def insert_all():
    soupermarket = {
        "marketin": marketin,
        "kritikos": kritikos,
        "xalkiadakis": xalkiadakis,
        "mymarket": mymarket,
        "efresh": efresh,
        "sklavenitis": sklavenitis,
        "ab": ab,
        # masoyti
        # galaxias
        # egnatia
        # bazaar
        # lidl
        # discount_markt
    }

    sms = {}

    for sm, func in soupermarket.items():
        try:
            sms[sm] = func()
        except Exception as e:
            print(f"error in {sm}: {e}")
            sms[sm] = []

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    failed = validate(sms, today)
    save_to_file(sms, today)

    return failed


def mymarket_products(html_content):
    # Function to decode unicode sequences using HTML unescape
    def decode_unicode_escapes(text):
        return html.unescape(text)

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Initialize lists to store the extracted data
    product_data = []

    # Enhanced logic to find product details using identified patterns

    for article in soup.find_all("article", {"data-controller": "google-analytics"}):
        # Extract product code, name, and price from data attributes
        data_values = article.get("data-google-analytics-item-value")

        if data_values:
            # Replace HTML entities and load as JSON
            data_dict = json.loads(data_values.replace("&quot;", '"'))
            product_code = data_dict.get("id", "N/A")
            product_name = decode_unicode_escapes(data_dict.get("name", "N/A"))
            product_price = float(data_dict.get("price", "N/A"))

            # Round the product price to two decimal places
            rounded_price = round(product_price, 2)

            # Append the product details as a list
            product_data.append([product_code, product_name, f"{rounded_price:.2f}"])

    return product_data


XALKIADAKIS_SECTIONS = [
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


def xalkiadakis(sections=None, max_pages=None):
    ret = []

    uids = {}

    for section in sections or XALKIADAKIS_SECTIONS:
        url = f"https://xalkiadakis.gr/category/{section}"

        for page in range(1, (max_pages or 998) + 1):
            thisURL = url

            if page > 1:
                thisURL = f"{url}?page={page}"

            text = requests.get(thisURL).text

            price_in_next_line = False

            count = 0

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
                    count += 1

                    if uid is None:
                        raise Exception(f"name: {name}, price: {price}, uid is None")

                    if uid in uids and uids[uid] != price:
                        raise Exception(
                            f"uid: {uid}, name: {name}, price: {price}, old price: {uids[uid]}"
                        )

                    # print(f"uid: {uid}, name: {name}, price: {price}")
                    ret.append([uid, name, price])
                    uids[uid] = price

                if 'class="price"' in line:
                    price_in_next_line = True

            if count == 0:
                break

            print(f"[{section}] found {count} items on page {page}")

    return ret


MARKETIN_SECTIONS = [
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


def marketin(sections=None, max_pages=None):
    ret = []

    for section in sections or MARKETIN_SECTIONS:
        for i in range(1, (max_pages or 998) + 1):
            url = f"https://www.market-in.gr/el-gr/{section}?pageno={i}"
            response = requests.get(url).text

            # regex match blocks starting with { and ending with } and can be multiline
            parts = re.findall(r"\{.*?\}", response, re.DOTALL)

            count = 0

            for part in parts:
                part = part.replace("'", '"').replace("\n", "").replace(",}", "}")

                try:
                    data = json.loads(part.replace("'", '"'))
                except:
                    continue

                if "price" not in data:
                    continue

                count += 1
                ret += [[data["id"], data["name"], float(data["price"])]]

            if count == 0:
                break

            print(f"[{section}] found {count} items on page {i}")

    return ret


def main():
    failed = insert_all()

    if failed:
        print(f"failed stores: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
