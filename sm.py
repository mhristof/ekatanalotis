#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

"""

import requests
import re
import json
import datetime
import html
from bs4 import BeautifulSoup

from click import clickhouse

from mymarket import mymarket
from efresh import efresh
from sklavenitis import sklavenitis


def save_to_file(sms, today):
    for sm, data in sms.items():
        with open(f"smdata/{sm}-{today}.csv", "w") as f:
            for item in data:
                f.write(f"{today},{item[0]},{item[1].replace(',', '-')},{item[2]}\n")
            print(f"saved {len(data)} items to {sm}.csv")


def insert_all():
    soupermarket = {
        "marketin": marketin,
        "kritikos": kritikos,
        "xalkiadakis": xalkiadakis,
        "mymarket": mymarket,
        "efresh": efresh,
        "sklavenitis": sklavenitis,
        # synka
        # masoyti
        # galaxias
        # av_vasilopoylos
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

            continue

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        ch = clickhouse()
    except:
        save_to_file(sms, today)

        return

    for sm, data in sms.items():
        print(f"retrieved data from {sm}: ", len(data))

        ch.query(
            f"CREATE table IF NOT EXISTS {sm} (date Date, barcode String, name String, price Float64) ENGINE = MergeTree() ORDER BY (date, barcode)"
        )

        data = [[today, *item] for item in data]

        existing = [
            x[0]
            for x in ch.query(
                f"SELECT barcode FROM {sm} WHERE date = today()",
            ).result_rows
        ]

        print(f"existing data in {sm}: ", len(existing))

        new_data = []

        for item in data:
            if item[1] in existing:
                continue
            new_data.append(item)

        print(f"new data in {sm}: ", len(new_data))

        if len(new_data) == 0:
            continue

        ch.insert(sm, new_data, column_names=["date", "barcode", "name", "price"])


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


def xalkiadakis():
    ret = []

    uids = {}

    for section in [
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
    ]:
        url = f"https://xalkiadakis.gr/category/{section}"

        for page in range(1, 999):
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


def kritikos():
    sections = [
        "fresko-kreas",
        "allantika",
        "turokomika",
        "galaktokomika",
        "eidh-psugeiou",
        "katapsuxh",
        "pantopwleio",
        "kaba",
        "proswpikh-frontida",
        "brefika",
        "kathariothta",
        "oikiakh-xrhsh",
        "pet-shop",
        "biologikaleitourgika",
    ]

    ret = []

    for section in sections:
        url = f"https://kritikos-sm.gr/categories/{section}"

        response = requests.get(url).text

        # find json blob starting with 'type="application/json">' and ending with '</script>'
        application_text = re.findall(
            r'type="application/json">.*?</script>', response, re.DOTALL
        )

        application = json.loads(application_text[0].split(">")[1].split("</script")[0])

        for iid, product in application["props"]["pageProps"]["staticProducts"].items():
            for item in product:
                ret.append([item["sku"], item["name"], item["finalPrice"] / 100])

    return ret


def marketin():
    ret = []

    for section in [
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
    ]:
        for i in range(1, 999):
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
    insert_all()


if __name__ == "__main__":
    main()
