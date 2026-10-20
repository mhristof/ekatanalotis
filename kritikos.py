#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

"""

import net


def kritikos(sections=None, max_pages=None):
    url = "https://kritikos-cxm-production.herokuapp.com/api/v2/products"
    headers = {
        "appId": "kritikos-web",
        "sec-ch-ua-platform": '"macOS"',
        "Referer": "https://kritikos-sm.gr/",
        "Accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
    }

    ret = []

    for collection in sections or ["900"]:
        params = {"collection_eq": collection, "eligible": "true"}
        data = net.get(url, headers=headers, params=params).json()
        ret += parse(data)

    print("found", len(ret), "items")

    return ret


def parse(data):
    ret = []

    for item in data["payload"]["products"]:
        uid = item["sku"]
        name = item["displayName"]
        price = item["finalPrice"] / 10

        ret.append([uid, name, price])

        print(f"uid: {uid}, name: {name}, price: {price}")

    return ret


if __name__ == "__main__":
    kritikos()
