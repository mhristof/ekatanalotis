"""Build the static files the browser extension reads, from the latest
price files, the catalog and the matches.

`build` writes, under site/:

- `index.json`: when it was built and each store's price date
- `latest/<store>.json`: `{"date": ..., "prices": {code: [price,
  unit_price, unit]}}`, every product in the store's latest price file
- `products.json`: `{product_id: {"name", "brand", "size", "codes":
  {store: code}}}`, the products matched in 2 or more stores
- `history/<product_id>.json`: `{store: [[date, price], ...]}`, the
  matched product's price changes in each store
- `packs/<store>.json`: the store's products with a pack size that is
  cheaper per unit (packs.cheaper())

`history` adds the price files not seen before to `history/<store>.csv`
(`code,date,price` rows, one per price change, sorted by code and date;
`history/dates.json` has the last date added per store), the committed
history the build reads.

In CI smdata/ isn't checked out (~3GB), so `needed` reads file names on
stdin (`git ls-tree --name-only HEAD smdata/`) and prints the files
`history` and `build` read: the ones newer than the history and the
latest of each store, to fetch only those."""

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
import packs

PRICES_DIRECTORY = "smdata"
SITE_DIRECTORY = "site"
HISTORY_DIRECTORY = "history"
PRICE_FILE = re.compile(r"(?:.*/)?([a-z_]+)-(\d{4}-\d{2}-\d{2})\.csv")
# the store whose name is shown for a product: these have the brand in the
# name, ab's names don't and kritikos' are abbreviated capitals
NAME_ORDER = ["mymarket", "sklavenitis", "masoutis", "marketin", "xalkiadakis", "ab", "kritikos", "efresh", "galaxias"]


def price_files(names):
    """{store: [(date, name), ...]} sorted by date, of the known stores."""
    out = defaultdict(list)

    for name in names:
        m = PRICE_FILE.fullmatch(name.strip())

        if m and m[1] in fuzzy.STORES:
            out[m[1]].append((m[2], name.strip()))

    return {store: sorted(files) for store, files in out.items()}


def latest_files(names):
    """{store: (date, name)} of the newest price file of each store."""
    return {store: files[-1] for store, files in price_files(names).items()}


def needed_files(names, dates):
    """The price files newer than `dates` ({store: last date in the
    history}) and the newest of each store."""
    out = set()

    for store, files in price_files(names).items():
        out.add(files[-1][1])
        out.update(name for date, name in files if date > dates.get(store, ""))

    return sorted(out)


def read_history(path):
    """{code: [[date, price], ...]} from a history csv."""
    out = defaultdict(list)

    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out[row["code"]].append([row["date"], float(row["price"])])

    return out


def write_history(path, history):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["code", "date", "price"])

        for code in sorted(history):
            for date, price in history[code]:
                w.writerow([code, date, f"{price:g}"])


def add_prices(history, date, path):
    """Append the price file's prices that differ from the code's last."""
    with open(path, newline="", encoding="utf-8") as f:
        for _, code, _, price in csv.reader(f):
            price = number(price)

            # old mymarket files have a "None" code
            if code != "None" and price is not None and (not history[code] or history[code][-1][1] != price):
                history[code].append([date, price])


def read_dates(directory=HISTORY_DIRECTORY):
    path = f"{directory}/dates.json"

    if not os.path.exists(path):
        return {}

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def update_history(prices_directory=PRICES_DIRECTORY, directory=HISTORY_DIRECTORY):
    dates = read_dates(directory)

    for store, files in sorted(price_files(os.listdir(prices_directory)).items()):
        new = [(date, name) for date, name in files if date > dates.get(store, "")]

        if not new:
            continue

        path = f"{directory}/{store}.csv"
        history = read_history(path)

        for date, name in new:
            add_prices(history, date, os.path.join(prices_directory, name))

        write_history(path, history)
        dates[store] = new[-1][0]
        print(f"{store}: {len(new)} files, up to {dates[store]}")

    write_json(f"{directory}/dates.json", dict(sorted(dates.items())))


def number(text):
    try:
        return float(text)
    except ValueError:
        return None


def prices(path, products):
    """{code: [price, unit_price, unit]}; the unit price is the catalog's,
    updated by the same run. A 4th item is the store's own unit when the
    unit was corrected (ab.fix_unit())."""
    out = {}

    with open(path, newline="", encoding="utf-8") as f:
        for _, code, _, price in csv.reader(f):
            p = products.get(code, {})
            out[code] = [number(price), number(p.get("unit_price", "")), p.get("unit") or None]

            if p.get("unit_fixed"):
                out[code].append(p["unit_fixed"])

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


# the first date a store's prices can be trusted from; the published
# history starts there, history/ keeps everything. efresh's scraper took
# the next product's price for prices with one decimal until cf0544f.
HISTORY_FROM = {"efresh": "2026-11-11"}


def trusted(store, points):
    """points from HISTORY_FROM[store] on; the price in effect then (the
    last change before it, which the first good scrape didn't change) is
    kept, dated HISTORY_FROM."""
    start = HISTORY_FROM.get(store)

    if not start or not points or points[0][0] >= start:
        return points

    before = [p for p in points if p[0] < start]
    after = [p for p in points if p[0] >= start]

    if after and after[0][0] == start:
        return after

    return [[start, before[-1][1]], *after]


def product_history(products, histories):
    """{product_id: {store: [[date, price], ...]}} of the matched codes
    with a history."""
    out = {}

    for product_id, p in products.items():
        found = {
            store: trusted(store, histories[store][code])
            for store, code in p["codes"].items()
            if histories.get(store, {}).get(code)
        }

        if found:
            out[product_id] = found

    return out


def build(
    prices_directory=PRICES_DIRECTORY,
    catalog_directory="catalog",
    history_directory=HISTORY_DIRECTORY,
    out=SITE_DIRECTORY,
):
    catalogs = {s: catalog.read(catalog.path(s, catalog_directory)) for s in fuzzy.STORES}
    latest = latest_files(os.listdir(prices_directory))

    for store, (date, name) in sorted(latest.items()):
        found = prices(os.path.join(prices_directory, name), catalogs[store])
        write_json(f"{out}/latest/{store}.json", {"date": date, "prices": found})
        alternatives = packs.cheaper(catalogs[store], {c: v[0] for c, v in found.items() if v[0]})
        write_json(f"{out}/packs/{store}.json", alternatives)
        print(f"{store}: {len(found)} prices of {date}, {len(alternatives)} with a cheaper pack")

    products = matched_products(match.read_csv(fuzzy.MATCHES_PATH), catalogs)
    write_json(f"{out}/products.json", products)
    print(f"{len(products)} matched products")

    histories = {s: read_history(f"{history_directory}/{s}.csv") for s in fuzzy.STORES}

    for product_id, found in product_history(products, histories).items():
        write_json(f"{out}/history/{product_id}.json", found)

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
    commands.add_parser("history", help=f"add new price files to {HISTORY_DIRECTORY}/")
    commands.add_parser("needed", help="print the price files history and build read")
    args = parser.parse_args(argv)

    if args.command == "needed":
        for name in needed_files(sys.stdin, read_dates()):
            print(name)
    elif args.command == "history":
        update_history()
    else:
        build()

    return 0


if __name__ == "__main__":
    sys.exit(main())
