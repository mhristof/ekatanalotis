#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

"""

import requests


def kritikos():
    url = "https://kritikos-cxm-production.herokuapp.com/api/v2/products"
    headers = {
        "appId": "kritikos-web",
        "sec-ch-ua-platform": '"macOS"',
        "Referer": "https://kritikos-sm.gr/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
    }

    params = {"collection_eq": "900", "eligible": "true"}

    response = requests.get(url, headers=headers, params=params)

    data = response.json()

    ret = []

    for item in data["payload"]["products"]:
        uid = item["sku"]
        name = item["displayName"]
        price = item["finalPrice"] / 10

        ret.append([uid, name, price])

        print(f"uid: {uid}, name: {name}, price: {price}")

    print("found", len(ret), "items")

    return ret


if __name__ == "__main__":
    kritikos()
