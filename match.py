"""Match products across stores by EAN: only kritikos lists barcodes, and
the ab and mymarket site searches find a product by its EAN.

`search` looks up the EANs of kritikos products not searched before and
appends every result, "not found" included, to matches/ean_search.csv, so
it can be stopped and resumed. `accept` is offline: it checks every hit
against the kritikos product (same size and brand; the price is no check,
as promotions differ) and writes matches/matches.csv and, for review,
matches/ean_candidates.csv."""

import argparse
import csv
import datetime
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

import ab
import catalog
import mymarket

# stores whose site search finds an EAN
SEARCH = {"ab": ab.search, "mymarket": mymarket.search}
# seconds between searches, per store
DELAY = 1.5

SEARCH_PATH = "matches/ean_search.csv"
SEARCH_FIELDS = ["store", "ean", "searched", *catalog.FIELDS[:-1]]
MATCHES_PATH = "matches/matches.csv"
MATCH_FIELDS = ["product_id", "store", "code", "method", "score"]
CANDIDATES_PATH = "matches/ean_candidates.csv"
CANDIDATE_FIELDS = [
    "kritikos",
    "kritikos_name",
    "kritikos_brand",
    "kritikos_size",
    "store",
    "code",
    "name",
    "brand",
    "size",
    "score",
    "verdict",
]

GREEK = dict(
    zip(
        "αβγδεζηθικλμνξοπρσςτυφχψω",
        "a v g d e z i th i k l m n x o p r s s t y f ch ps o".split(),
    )
)

# size units, after normalise(): (pattern, base unit, factor)
SIZE_UNITS = [
    (r"kg|kgr|kilo|κιλ\w*|κ", "g", 1000),
    (r"g|gr|γρ\w*|γ", "g", 1),
    (r"ml|μλ", "ml", 1),
    (r"cl", "ml", 10),
    (r"l|lt|ltr|lit\w*|λιτ\w*|λ", "ml", 1000),
    (r"τεμ\w*|τμχ|pcs|τεμαχι\w*|αρι|αδα|φυλλα", "piece", 1),
    (r"μεζ\w*|wash\w*|μεζουρ\w*", "wash", 1),
]
SIZE = re.compile(
    r"(?:(\d+)\s*[x*χ×]\s*)?(\d+(?:\.\d+)?)\s*("
    + "|".join(f"(?:{pattern})" for pattern, _, _ in SIZE_UNITS)
    + r")(?![a-zα-ω])"
)


def normalise(text):
    """Lowercase, no accents, '.' as the decimal point."""
    text = catalog.strip_accents(text or "").lower()

    return re.sub(r"(\d),(\d)", r"\1.\2", text)


def latin(text):
    """normalise()d text in Latin letters, letters and digits only."""
    text = normalise(text).replace("ου", "ou").replace("μπ", "b")

    return re.sub(r"[^a-z0-9]", "", "".join(GREEK.get(c, c) for c in text))


def sizes(text):
    """{(total quantity, unit)} in text, packs multiplied out: '4*125gr'
    -> {(500, 'g')}, '1,5L' -> {(1500, 'ml')}."""
    out = set()

    for packs, qty, unit in SIZE.findall(normalise(text)):
        for pattern, base, factor in SIZE_UNITS:
            if re.fullmatch(pattern, unit):
                out.add((round(float(qty) * factor * int(packs or 1), 3), base))
                break

    return out


def same_size(a, b):
    """True/False when both products have a size in the same unit (within
    5%), None when that can't be told."""
    a = sizes(f"{a['size']} {a['name']}")
    b = sizes(f"{b['size']} {b['name']}")
    units = {u for _, u in a} & {u for _, u in b}

    if not units:
        return None

    return any(
        ua == ub and abs(qa - qb) <= 0.05 * max(qa, qb)
        for qa, ua in a
        for qb, ub in b
        if ua in units
    )


def same_brand(a, b):
    """True/False when both products have a brand, None otherwise. A brand
    in the other product's name counts, as names often carry it."""
    ba, bb = latin(a["brand"]), latin(b["brand"])

    if not ba or not bb:
        return None

    return (
        ba in bb
        or bb in ba
        or ba in latin(b["name"])
        or bb in latin(a["name"])
        or SequenceMatcher(None, ba, bb).ratio() >= 0.8
    )


def trigrams(text):
    return {text[i : i + 3] for i in range(len(text) - 2)}


def score(a, b):
    """Name similarity, 0 to 1: trigram overlap of brand and name."""
    ta = trigrams(latin(f"{a['brand']} {a['name']}"))
    tb = trigrams(latin(f"{b['brand']} {b['name']}"))

    return round(len(ta & tb) / len(ta | tb), 2) if ta and tb else 0.0


def verdict(product, hit):
    """'ok', or why the hit is not the product: 'size', 'brand'."""
    wrong = [
        name
        for name, same in (("size", same_size), ("brand", same_brand))
        if same(product, hit) is False
    ]

    return ",".join(wrong) or "ok"


def read_csv(path):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def write_csv(path, fields, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def product_eans(product):
    """The product's EANs, EAN-13 before EAN-8."""
    return sorted(filter(None, product["ean"].split(";")), key=lambda e: (-len(e), e))


def pending(products, results, store):
    """The products with an EAN not searched yet on store, unless an
    earlier search already found them."""
    searched = {r["ean"] for r in results if r["store"] == store}
    found = {r["ean"] for r in results if r["store"] == store and r["code"]}

    return [
        p
        for p in products
        if not found & set(product_eans(p)) and set(product_eans(p)) - searched
    ]


def search(stores, limit=None, path=SEARCH_PATH, kritikos="catalog/kritikos.csv"):
    """Search each store for the EANs of up to `limit` pending products,
    one product's EANs until one is found, appending results to path."""
    results = read_csv(path)
    products = [p for p in catalog.read(kritikos).values() if p["ean"]]
    today = datetime.date.today().isoformat()
    lock = threading.Lock()

    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = open(path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out, SEARCH_FIELDS, lineterminator="\n")

    if new:
        writer.writeheader()

    def one(store):
        todo = pending(products, results, store)[:limit]
        searched = {r["ean"] for r in results if r["store"] == store}
        counts = {"products": len(todo), "searches": 0, "found": 0}
        print(f"[{store}] {len(todo)} products to search")

        for i, product in enumerate(todo, 1):
            for ean in product_eans(product):
                if ean in searched:
                    continue

                time.sleep(DELAY)

                try:
                    rows = catalog.products(SEARCH[store](ean)).values()
                except Exception as e:
                    # likely blocked; stop without marking the rest searched
                    print(f"[{store}] {ean}: error {e!r}, stopping")

                    return counts

                rows = [{**r, "store": store, "ean": ean, "searched": today} for r in rows]
                counts["searches"] += 1

                with lock:
                    writer.writerows(
                        [{k: r[k] for k in SEARCH_FIELDS} for r in rows]
                        or [{"store": store, "ean": ean, "searched": today}]
                    )
                    out.flush()

                if rows:
                    counts["found"] += 1
                    break

            if i % 100 == 0:
                print(f"[{store}] {i}/{len(todo)}, {counts['found']} found")

        return counts

    try:
        with ThreadPoolExecutor(len(stores)) as executor:
            counts = dict(zip(stores, executor.map(one, stores)))
    finally:
        out.close()

    # sorted, for small diffs
    rows = read_csv(path)
    rows.sort(key=lambda r: (r["store"], r["ean"], r["code"]))
    write_csv(path, SEARCH_FIELDS, rows)

    for store, c in counts.items():
        print(f"[{store}] {c['products']} products, {c['searches']} searches, {c['found']} found")

    return counts


def candidates(products, results, catalogs):
    """Every (kritikos product, store hit) pair, best first, with its
    score and verdict. Hits are checked with the store's catalog row when
    there is one, as it has more details than a search result."""
    hits = {}

    for r in results:
        if r["code"]:
            hits.setdefault(r["ean"], []).append(r)

    out = []

    for product in products.values():
        seen = set()

        for ean in product_eans(product):
            for r in hits.get(ean, []):
                key = (r["store"], r["code"])

                if key in seen:
                    continue

                seen.add(key)
                hit = catalogs.get(r["store"], {}).get(r["code"]) or r
                out.append(
                    {
                        "kritikos": product["code"],
                        "kritikos_name": product["name"],
                        "kritikos_brand": product["brand"],
                        "kritikos_size": product["size"],
                        "store": r["store"],
                        "code": r["code"],
                        "name": hit["name"],
                        "brand": hit["brand"],
                        "size": hit["size"],
                        "score": score(product, hit),
                        "verdict": verdict(product, hit),
                    }
                )

    out.sort(key=lambda c: (c["verdict"] != "ok", -c["score"], c["kritikos"], c["store"]))

    return out


def matches(candidates):
    """matches.csv rows: one product per kritikos code with an accepted
    hit, the best scored hit per store, and each store code used once."""
    taken = set()
    products = {}

    for c in candidates:
        if c["verdict"] != "ok" or (c["store"], c["code"]) in taken:
            continue

        stores = products.setdefault(c["kritikos"], {})

        if c["store"] in stores:
            continue

        stores[c["store"]] = c
        taken.add((c["store"], c["code"]))

    rows = []

    for code, stores in products.items():
        product_id = f"kritikos-{code}"
        rows.append(
            {"product_id": product_id, "store": "kritikos", "code": code, "method": "ean", "score": ""}
        )
        rows += [
            {
                "product_id": product_id,
                "store": store,
                "code": c["code"],
                "method": "ean",
                "score": c["score"],
            }
            for store, c in stores.items()
        ]

    rows.sort(key=lambda r: (r["product_id"], r["store"]))

    return rows


def accept():
    products = catalog.read(catalog.path("kritikos"))
    catalogs = {store: catalog.read(catalog.path(store)) for store in SEARCH}
    found = candidates(products, read_csv(SEARCH_PATH), catalogs)

    # by kritikos code, for review
    write_csv(
        CANDIDATES_PATH,
        CANDIDATE_FIELDS,
        sorted(found, key=lambda c: (c["kritikos"], c["store"], c["code"])),
    )
    rows = matches(found)
    write_csv(MATCHES_PATH, MATCH_FIELDS, rows)

    verdicts = {}

    for c in found:
        verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1

    print(f"candidates: {len(found)} {verdicts}")

    for store in SEARCH:
        print(f"{store}: {sum(r['store'] == store for r in rows)} matched")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    s = commands.add_parser("search", help="search EANs not searched yet (live)")
    s.add_argument("--limit", type=int, help="products per store")
    s.add_argument("--stores", nargs="+", choices=list(SEARCH), default=list(SEARCH))
    commands.add_parser("accept", help="check the hits and write matches (offline)")
    args = parser.parse_args(argv)

    if args.command == "search":
        search(args.stores, args.limit)

    accept()

    return 0


if __name__ == "__main__":
    sys.exit(main())
