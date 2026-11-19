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

LOOKALIKES = str.maketrans("ABEHIKMNOPTXYZ", "ΑΒΕΗΙΚΜΝΟΡΤΧΥΖ")

# latin() words in brands that say nothing about which brand it is:
# estate, cooperative, winery, company forms
BRAND_NOISE = {"ktima", "ktimata", "eas", "oinopoiitiki", "oinopoieio", "abee", "spa"}

# size units, after normalise(): (pattern, base unit, factor)
SIZE_UNITS = [
    (r"kg|kgr|kilo|κιλ\w*|κ", "g", 1000),
    (r"g|gr|γρ\w*|γ", "g", 1),
    (r"ml|μλ", "ml", 1),
    (r"cl", "ml", 10),
    (r"l|lt|ltr|lit\w*|λιτ\w*|λ", "ml", 1000),
    (r"τεμ\w*|τμχ|pcs|τεμαχι\w*|αρι|αδα|φυλλα|δισκι\w*|καψουλ\w*|ταινι\w*", "piece", 1),
    (r"μεζ\w*|wash\w*|μεζουρ\w*", "wash", 1),
]
# sizes this close are the same, rounded differently; a wrong EAN hit is
# usually a multipack, 2x or more
TOLERANCE = 0.1
# drained weight, after normalise(): 'ΣΤ.Β.', 'ΣΤΡ.ΒΑΡΟΣ', 'ΣΤΡΑΓ.ΒΑΡΟΣ',
# not 'ΣΤΡ.ΒΙΟΛ.'
DRAINED = re.compile(r"\bστρ?(?:αγ)?\.\s*β(?:\.|αρ)")
PROMO = re.compile(r"(\d+)\s*\+\s*(\d+)")
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
    for greek, latin_ in (("ου", "ou"), ("αυ", "av"), ("ευ", "ev"), ("μπ", "b")):
        text = normalise(text).replace(greek, latin_)

    return re.sub(r"[^a-z0-9]", "", "".join(GREEK.get(c, c) for c in text))


def as_greek(text):
    """Latin capitals that look like Greek ones as Greek: 'HBH' -> 'ΗΒΗ',
    as some stores type Greek brands in Latin letters."""
    return (text or "").translate(LOOKALIKES)


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


def name_sizes(text):
    """sizes() of a product name, where a size next to a piece count may be
    per piece or the total: 'Snickers 50gr 3τεμ' is 150g, 'Zewa 90τεμ
    0,162kg' is 162g, so both are kept."""
    out = sizes(text)
    # '330ml 4+2 Δώρο' is a 6 pack
    out |= {(int(a) + int(b), "piece") for a, b in PROMO.findall(text or "")}
    pieces = [q for q, u in out if u == "piece" and q > 1]

    return out | {(round(q * n, 3), u) for q, u in out if u != "piece" for n in pieces}


def compare(a, b):
    """True/False when a and b have a size in the same unit, None when
    they don't."""
    units = {u for _, u in a} & {u for _, u in b}

    if not units:
        return None

    return any(
        ua == ub and abs(qa - qb) < TOLERANCE * max(qa, qb)
        for qa, ua in a
        for qb, ub in b
        if ua in units
    )


def product_sizes(product):
    out = sizes(product["size"]) | name_sizes(product["name"])

    # a drained weight can't be compared with a net weight
    if DRAINED.search(normalise(product["name"])):
        out = {(q, u) for q, u in out if u != "g"}

    return out


def same_size(a, b):
    """True/False when both products have a size in the same unit (within
    TOLERANCE), None when that can't be told. Sizes come from the size field and
    the name, any of them agreeing is enough, as either can be wrong (ab
    '100 γρ' for 'Τσίχλες 90g')."""
    return compare(product_sizes(a), product_sizes(b))


def words(text):
    """The latin() words of text, without short and BRAND_NOISE ones."""
    out = (latin(w) for w in re.split(r"[^\w]+", normalise(text)))

    return {w for w in out if len(w) >= 3 and w not in BRAND_NOISE}


def similar(a, b):
    """Two words that differ by an ending: 'skoura' and 'skouras'."""
    return SequenceMatcher(None, a, b).ratio() >= 0.8


def same_brand(a, b):
    """True/False when both products have a brand, None otherwise. Brands
    are spelled differently across stores ('NICO LAZARIDI', 'ΚΤΗΜΑ Ν.
    ΛΑΖΑΡΙΔΗ'), so one similar word is enough, in the other product's
    brand or name."""
    ba, bb = latin(a["brand"]), latin(b["brand"])

    if not ba or not bb:
        return None

    if (
        ba in bb
        or bb in ba
        or similar(ba, bb)
        or similar(latin(as_greek(a["brand"])), latin(as_greek(b["brand"])))
    ):
        return True

    wa = words(a["brand"])
    wb = words(b["brand"])

    return any(
        similar(x, y)
        for x, y in [
            *((x, y) for x in wa for y in wb | words(b["name"])),
            *((x, y) for x in wb for y in words(a["name"])),
        ]
    )


def trigrams(text):
    return {text[i : i + 3] for i in range(len(text) - 2)}


def score(a, b):
    """Name similarity, 0 to 1: trigram overlap of brand and name."""
    ta = trigrams(latin(f"{a['brand']} {a['name']}"))
    tb = trigrams(latin(f"{b['brand']} {b['name']}"))

    return round(len(ta & tb) / len(ta | tb), 2) if ta and tb else 0.0


def verdict(product, hit, sole=True):
    """'ok', or why the hit is not the product: 'size', 'brand'. A brand
    spelled differently doesn't count when the size agrees and the hit was
    the only result, a sure EAN hit; several results mean the site fell
    back to a text search."""
    size = same_size(product, hit)
    wrong = []

    if size is False:
        wrong.append("size")

    if same_brand(product, hit) is False and not (size and sole):
        wrong.append("brand")

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


def pending(products, results, store, matched):
    """The products with an EAN not searched yet on store, unless one of
    their hits there was accepted (kritikos code in matched)."""
    searched = {r["ean"] for r in results if r["store"] == store}

    return [
        p
        for p in products
        if p["code"] not in matched and set(product_eans(p)) - searched
    ]


def search(stores, limit=None, path=SEARCH_PATH, kritikos="catalog/kritikos.csv"):
    """Search each store for the EANs of up to `limit` pending products,
    one product's EANs until a hit is accepted, appending results to
    path."""
    results = read_csv(path)
    products = {code: p for code, p in catalog.read(kritikos).items() if p["ean"]}
    catalogs = {store: catalog.read(catalog.path(store)) for store in stores}
    found = candidates(products, results, catalogs)
    today = datetime.date.today().isoformat()
    lock = threading.Lock()

    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = open(path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out, SEARCH_FIELDS, lineterminator="\n")

    if new:
        writer.writeheader()

    def one(store):
        matched = {c["kritikos"] for c in found if c["store"] == store and c["verdict"] == "ok"}
        todo = pending(products.values(), results, store, matched)[:limit]
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

                if any(
                    verdict(product, catalogs[store].get(r["code"]) or r, len(rows) == 1) == "ok"
                    for r in rows
                ):
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
    results_per_search = {}

    for r in results:
        if r["code"]:
            hits.setdefault(r["ean"], []).append(r)
            key = (r["store"], r["ean"])
            results_per_search[key] = results_per_search.get(key, 0) + 1

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
                        "verdict": verdict(
                            product, hit, results_per_search[(r["store"], ean)] == 1
                        ),
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
