"""Build the static files the browser extension reads, from the latest
price files, the catalog and the matches.

`build` writes, under site/:

- `index.json`: when it was built and each store's price date
- `latest/<store>.json`: `{"date": ..., "prices": {code: [price,
  unit_price, unit]}}`, every product in the store's latest price file
- `products.json`: `{product_id: {"name", "brand", "size", "codes":
  {store: code}}}`, the products matched in 2 or more stores

In CI smdata/ isn't checked out (~3GB), so `latest` reads file names on
stdin (`git ls-tree --name-only HEAD smdata/`) and prints the latest file
of each store, to fetch only those."""

import argparse
import csv
import datetime
import json
import os
import re
import sys
from collections import defaultdict

import catalog
import fuzzy
import match

PRICES_DIRECTORY = "smdata"
SITE_DIRECTORY = "site"
PRICE_FILE = re.compile(r"(?:.*/)?([a-z_]+)-(\d{4}-\d{2}-\d{2})\.csv")
# the store whose name is shown for a product: these have the brand in the
# name, ab's names don't and kritikos' are abbreviated capitals
NAME_ORDER = ["mymarket", "sklavenitis", "marketin", "xalkiadakis", "ab", "kritikos", "efresh"]


def latest_files(names):
    """{store: (date, name)} of the newest price file of each store."""
    out = {}

    for name in names:
        m = PRICE_FILE.fullmatch(name.strip())

        if m and m[1] in fuzzy.STORES and (m[1] not in out or m[2] > out[m[1]][0]):
            out[m[1]] = (m[2], name.strip())

    return out


def number(text):
    try:
        return float(text)
    except ValueError:
        return None


def prices(path, products):
    """{code: [price, unit_price, unit]}; the unit price is the catalog's,
    updated by the same run."""
    out = {}

    with open(path, newline="", encoding="utf-8") as f:
        for _, code, _, price in csv.reader(f):
            p = products.get(code, {})
            out[code] = [number(price), number(p.get("unit_price", "")), p.get("unit") or None]

    return out


def matched_products(rows, catalogs):
    """{product_id: {name, brand, size, codes}} from the matches rows."""
    codes = defaultdict(dict)

    for row in rows:
        codes[row["product_id"]][row["store"]] = row["code"]

    out = {}

    for product_id, stores in sorted(codes.items()):
        shown = next(
            catalogs[s][stores[s]] for s in NAME_ORDER if stores.get(s) in catalogs.get(s, {})
        )
        out[product_id] = {
            "name": shown["name"],
            "brand": shown["brand"],
            "size": shown["size"],
            "codes": stores,
        }

    return out


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def build(prices_directory=PRICES_DIRECTORY, catalog_directory="catalog", out=SITE_DIRECTORY):
    catalogs = {s: catalog.read(catalog.path(s, catalog_directory)) for s in fuzzy.STORES}
    latest = latest_files(os.listdir(prices_directory))

    for store, (date, name) in sorted(latest.items()):
        found = prices(os.path.join(prices_directory, name), catalogs[store])
        write_json(f"{out}/latest/{store}.json", {"date": date, "prices": found})
        print(f"{store}: {len(found)} prices of {date}")

    products = matched_products(match.read_csv(fuzzy.MATCHES_PATH), catalogs)
    write_json(f"{out}/products.json", products)
    print(f"{len(products)} matched products")

    write_json(
        f"{out}/index.json",
        {
            "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "stores": {store: date for store, (date, _) in sorted(latest.items())},
        },
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help=f"write the files under {SITE_DIRECTORY}/")
    commands.add_parser("latest", help="print the latest price file of each store")
    args = parser.parse_args(argv)

    if args.command == "latest":
        for _, name in sorted(latest_files(sys.stdin).values()):
            print(name)
    else:
        build()

    return 0


if __name__ == "__main__":
    sys.exit(main())
