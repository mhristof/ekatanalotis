#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

"""

import requests
import json


def ab():
    ret = []
    pageSize = 30

    codes = {}
    duplicates = 0
    subsequent_emtpy_categories = 0

    for category in [f"{i:03}" for i in range(1, 1000)]:
        page = 0
        total = 0
        new_category_products = 0

        while True:
            try:
                products = requests.get(
                    f"https://www.ab.gr/api/v1/?operationName=GetCategoryProductSearch&variables=%7B%22lang%22%3A%22gr%22%2C%22searchQuery%22%3A%22%3Arelevance%22%2C%22sort%22%3A%22relevance%22%2C%22category%22%3A%22{category}%22%2C%22pageNumber%22%3A{page}%2C%22pageSize%22%3A{pageSize}%2C%22filterFlag%22%3Atrue%2C%22plainChildCategories%22%3Afalse%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22dd8d3de806d7e82af7e29b491a30df5a93d2c27c04190ef25ab973cbfe913079%22%7D%7D"
                ).json()["data"]["categoryProductSearch"]["products"]
            except Exception as e:
                print("exception", e, "for", category, page)

                break

            print(
                f"Category: {category} Page: {page}, total: {total}, new category products: {new_category_products}, duplicates: {duplicates}"
            )

            if not products:
                break

            for product in products:
                name = product["name"]

                if name == ".":
                    name = product["url"]

                code = product["code"]

                if code in codes:
                    print(
                        f"Duplicate code: {code}, name: {name}, price: {product['price']['value']} for category {category}"
                    )
                    duplicates += 1

                    continue

                codes[code] = True

                print(product["code"], name, product["price"]["value"])
                total += 1
                new_category_products += 1
                ret.append([product["code"], name, product["price"]["value"]])

            page += 1

        if new_category_products == 0:
            subsequent_emtpy_categories += 1

        if subsequent_emtpy_categories > 10:
            break

    return ret


if __name__ == "__main__":
    ab()
