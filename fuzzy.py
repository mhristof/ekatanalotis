"""Match products across stores by name, brand and size, for the stores
without barcodes and the products kritikos doesn't sell.

Products are compared only with products of the same size (same unit,
under match.TOLERANCE apart) and a brand word starting the same. A pair
is scored by a logistic regression over name similarity features, trained
on the EAN matches (`train`), and kept when each product is the other's
best match in its store, the score is at least THRESHOLD and beats the
second best candidate by MARGIN, as a generic name ('ΑΤΤΙΚΗ ΜΕΛΙ 1Κ')
fits several variants equally."""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from itertools import count

import catalog
import match

STORES = ["kritikos", "ab", "mymarket", "sklavenitis", "xalkiadakis", "marketin", "efresh"]
WEIGHTS_PATH = "matches/fuzzy_weights.json"
MATCHES_PATH = "matches/matches.csv"
# about 98% precision on the EAN matches, a lower bound as some of those
# are wrong (old EANs)
THRESHOLD = 0.1
MARGIN = 0.15

# size buckets of this ratio; neighbouring buckets are compared too, so
# sizes TOLERANCE apart always meet
BUCKET = math.log(1 + match.TOLERANCE)
BRAND_PREFIX = 4
# word endings differ across stores ('βαλσαμικο', 'βαλσαμικου')
STEM = 5
NUMBER = re.compile(r"\d+(?:\.\d+)?")
# Greek in Latin letters is spelled two ways: match.latin()'s ('chrysi',
# 'papadopoulou', 'bira') and efresh's slugs ('xrysh', 'papadopoyloy',
# 'mpyra'); both fold to one key
FOLDS = [
    ("ch", "x"),
    ("ks", "x"),
    ("ph", "f"),
    ("oy", "u"),
    ("ou", "u"),
    ("ay", "av"),
    ("ey", "ev"),
    ("mp", "b"),
    ("b", "v"),
    ("w", "o"),
    ("h", "i"),
    ("y", "i"),
]

FEATURES = [
    "cosine",
    "word_overlap",
    "unmatched_max",
    "unmatched_min",
    "shared_number",
    "one_sided_number",
    "same_size",
    "same_brand",
    "one_sided_pieces",
]


def without_sizes(product):
    return match.SIZE.sub(" ", match.normalise(f"{product['brand']} {product['name']}"))


def numbers(product):
    """The numbers in the name that are not sizes: fat %, ages, shades,
    model numbers. Variants of one product differ in them."""
    return set(NUMBER.findall(without_sizes(product)))


def fold(word):
    for a, b in FOLDS:
        word = word.replace(a, b)

    return word


def stems(product):
    """The name's words (and efresh's slug's) in Latin letters, fold()ed,
    cut to STEM letters, and its numbers."""
    slug = match.SIZE.sub(" ", match.normalise((product.get("slug") or "").replace("-", " ")))
    words = {fold(w)[:STEM] for w in match.words(f"{without_sizes(product)} {slug}")}

    return words | {f"n{n}" for n in numbers(product)}


def trigrams(words):
    padded = f" {' '.join(sorted(words))} "

    return Counter(padded[i : i + 3] for i in range(len(padded) - 2))


def size_keys(sizes):
    """Bucket keys of a product's sizes, for blocking."""
    return {(u, round(math.log(q) / BUCKET)) for q, u in sizes if q > 0}


def brand_keys(brand):
    """The first letters of the brand's words, Greek typed in Latin letters
    read both ways: 'ΚΤΗΜΑ Ν. ΛΑΖΑΡΙΔΗ' and 'NICO LAZARIDI' share 'laza'."""
    words = match.words(brand) | match.words(match.as_greek(brand))

    return {fold(w)[:BRAND_PREFIX] for w in words}


def load(stores=STORES, directory="catalog"):
    """{(store, code): product}, with what matching needs, for products
    with a size and a brand."""
    out = {}

    for store in stores:
        for code, p in catalog.read(catalog.path(store, directory)).items():
            sizes = match.product_sizes(p)
            brands = brand_keys(p["brand"])

            if sizes and brands:
                out[(store, code)] = {
                    **p,
                    "sizes": sizes,
                    "brands": brands,
                    "brand_latin": fold(match.latin(p["brand"])),
                    "numbers": numbers(p),
                    "stems": stems(p),
                }

    n = len(out)
    grams = {key: trigrams(p["stems"]) for key, p in out.items()}
    gram_df = Counter(g for counts in grams.values() for g in counts)
    stem_df = Counter(s for p in out.values() for s in p["stems"])

    for key, p in out.items():
        v = {g: c * math.log(n / gram_df[g]) for g, c in grams[key].items()}
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        p["vector"] = {g: w / norm for g, w in v.items()}
        p["idf"] = {s: math.log(n / stem_df[s]) for s in p["stems"]}

    return out


def candidates(products):
    """{(store, code): {other store: [(store, code)]}}, the products of
    other stores with the same size and brand and no other numbers."""
    index = defaultdict(list)

    for key, p in products.items():
        for unit, bucket in size_keys(p["sizes"]):
            for brand in p["brands"]:
                index[(unit, bucket, brand)].append(key)

    out = defaultdict(lambda: defaultdict(list))

    for key, p in products.items():
        blocks = {
            (unit, b, brand)
            for unit, bucket in size_keys(p["sizes"])
            for b in (bucket - 1, bucket, bucket + 1)
            for brand in p["brands"]
        }
        seen = set()

        for block in blocks:
            for other in index.get(block, ()):
                if other[0] == key[0] or other in seen:
                    continue

                seen.add(other)
                q = products[other]

                # '2% λιπαρά' is not '5% λιπαρά'
                if p["numbers"] and q["numbers"] and p["numbers"].isdisjoint(q["numbers"]):
                    continue

                if match.compare(p["sizes"], q["sizes"]):
                    out[key][other[0]].append(other)

    return out


def pieces(product):
    return {q for q, u in product["sizes"] if u == "piece"}


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a

    return sum(w * b.get(g, 0.0) for g, w in a.items())


def features(p, q):
    """FEATURES of a pair, symmetric in p and q."""
    shared = p["stems"] & q["stems"]
    mass_p = sum(p["idf"].values()) or 1.0
    mass_q = sum(q["idf"].values()) or 1.0
    shared_mass = sum(p["idf"][s] for s in shared)
    unmatched = [1 - shared_mass / mass_p, 1 - shared_mass / mass_q]

    return [
        cosine(p["vector"], q["vector"]),
        shared_mass / (mass_p + mass_q - shared_mass),
        max(unmatched),
        min(unmatched),
        float(bool(p["numbers"] & q["numbers"])),
        float(bool(p["numbers"]) != bool(q["numbers"])),
        float(any(qa == qb and ua == ub for qa, ua in p["sizes"] for qb, ub in q["sizes"])),
        float(p["brand_latin"] == q["brand_latin"]),
        # 'Βίκος Πορτοκαλάδα 1,5lt 6τεμ' is likely a pack of the 1,5L
        float(pieces(p) != pieces(q) and max(pieces(p) | pieces(q)) > 1 and not (pieces(p) and pieces(q))),
    ]


def probability(weights, x):
    z = weights[0] + sum(w * v for w, v in zip(weights[1:], x))

    return 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))


def solve(a, b):
    """x for a x = b, by Gaussian elimination."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]

    for i in range(n):
        pivot = max(range(i, n), key=lambda r: abs(m[r][i]))
        m[i], m[pivot] = m[pivot], m[i]

        for r in range(n):
            if r != i and m[i][i]:
                f = m[r][i] / m[i][i]
                m[r] = [x - f * y for x, y in zip(m[r], m[i])]

    return [m[i][n] / m[i][i] for i in range(n)]


def fit(rows, l2=1.0, iterations=25):
    """Logistic regression weights [bias, *FEATURES] for rows of
    (features, label), by Newton's method with an L2 penalty."""
    d = len(rows[0][0]) + 1
    weights = [0.0] * d

    for _ in range(iterations):
        grad = [0.0] * d
        hess = [[0.0] * d for _ in range(d)]

        for x, y in rows:
            x = [1.0, *x]
            p = probability(weights, x[1:])
            s = p * (1 - p)

            for i in range(d):
                grad[i] += (p - y) * x[i]

                for j in range(d):
                    hess[i][j] += s * x[i] * x[j]

        for i in range(1, d):
            grad[i] += l2 * weights[i]
            hess[i][i] += l2

        step = solve(hess, grad)
        weights = [w - s for w, s in zip(weights, step)]

        if max(abs(s) for s in step) < 1e-6:
            break

    return weights


def scorer(products, weights):
    cache = {}

    def score(a, b):
        key = (a, b) if a < b else (b, a)

        if key not in cache:
            cache[key] = probability(weights, features(products[a], products[b]))

        return cache[key]

    return score


def best_two(score, a, others):
    """(best score, best product, second best score) of a's candidates."""
    scored = sorted(((score(a, b), b) for b in others), reverse=True)
    best, product = scored[0] if scored else (0.0, None)

    return best, product, scored[1][0] if len(scored) > 1 else 0.0


def accepted(score, found, a, store, threshold=THRESHOLD, margin=MARGIN):
    """a's match in store, or None."""
    best, b, second = best_two(score, a, found[a].get(store, []))

    if b is None or best < threshold or best - second < margin:
        return None

    back, a2, back_second = best_two(score, b, found[b].get(a[0], []))

    if a2 != a or back - back_second < margin:
        return None

    return b


def pairs(products, weights, threshold=THRESHOLD, margin=MARGIN):
    """[(score, a, b)]: the accepted matches between stores, a < b."""
    found = candidates(products)
    score = scorer(products, weights)
    out = []

    for a in found:
        for store in found[a]:
            b = accepted(score, found, a, store, threshold, margin)

            if b is not None and a < b:
                out.append((score(a, b), a, b))

    return sorted(out, reverse=True)


def ean_truth():
    """{store: {kritikos code: store code}} from the EAN matches."""
    products = defaultdict(dict)

    for r in match.read_csv(match.MATCHES_PATH):
        if r["method"] == "ean":
            products[r["product_id"]][r["store"]] = r["code"]

    truth = defaultdict(dict)

    for stores in products.values():
        for store, code in stores.items():
            if store != "kritikos":
                truth[store][stores["kritikos"]] = code

    return truth


def training_rows(products, found, truth, half):
    """(features, label) for the candidates of the kritikos products with
    an EAN match, those whose code % 2 == half."""
    rows = []

    for store, codes in truth.items():
        for code, other in codes.items():
            a = ("kritikos", code)

            if a not in found or int(code) % 2 != half:
                continue

            for b in found[a].get(store, []):
                rows.append((features(products[a], products[b]), float(b == (store, other))))

    return rows


def evaluate(products, found, truth, weights, half, threshold=THRESHOLD, margin=MARGIN):
    """{store: (right, wrong, EAN matches)} on the kritikos products whose
    code % 2 == half."""
    score = scorer(products, weights)
    out = {}

    for store, codes in truth.items():
        right = wrong = total = 0

        for code, other in codes.items():
            if int(code) % 2 != half:
                continue

            total += 1
            a = ("kritikos", code)
            b = accepted(score, found, a, store, threshold, margin) if a in found else None

            if b == (store, other):
                right += 1
            elif b is not None:
                wrong += 1

        out[store] = (right, wrong, total)

    return out


def train():
    """Fit the weights on half the EAN matches, report on the other half,
    then fit on all and write WEIGHTS_PATH."""
    products = load()
    found = candidates(products)
    truth = ean_truth()

    weights = fit(training_rows(products, found, truth, 0))
    print("weights:", dict(zip(["bias", *FEATURES], (round(w, 2) for w in weights))))

    for threshold in (0.3, 0.5, 0.7, 0.9):
        for margin in (0.0, 0.2, 0.4):
            result = evaluate(products, found, truth, weights, 1, threshold, margin)
            print(
                f"threshold {threshold} margin {margin}: "
                + ", ".join(
                    f"{store} recall {r / t:.0%} precision {r / max(1, r + w):.1%}"
                    for store, (r, w, t) in sorted(result.items())
                )
            )

    weights = fit(training_rows(products, found, truth, 0) + training_rows(products, found, truth, 1))

    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(zip(["bias", *FEATURES], weights)), f, indent=2)
        f.write("\n")


def cluster(ean_rows, fuzzy_pairs):
    """matches.csv rows: products of codes linked by EAN matches first, then
    fuzzy pairs by score, never two codes of one store in a product."""
    edges = []
    groups = defaultdict(dict)

    for r in ean_rows:
        groups[r["product_id"]][r["store"]] = r

    for stores in groups.values():
        k = ("kritikos", stores["kritikos"]["code"])

        for store, r in stores.items():
            if store != "kritikos":
                edges.append((2, float(r["score"] or 0), k, (store, r["code"]), "ean"))

    edges += [(1, score, a, b, "fuzzy") for score, a, b in fuzzy_pairs]
    edges.sort(key=lambda e: (-e[0], -e[1], e[2], e[3]))

    product = {}  # (store, code) -> product number
    members = {}  # product number -> {store: (code, method, score)}
    numbers = count()

    for _, score, a, b, method in edges:
        for node in (a, b):
            if node not in product:
                product[node] = next(numbers)
                members[product[node]] = {node[0]: (node[1], method, score)}

        pa, pb = product[a], product[b]

        if pa == pb or members[pa].keys() & members[pb].keys():
            continue

        # codes joining a product get this edge's method and score
        if len(members[pa]) == 1:
            members[pa][a[0]] = (a[1], method, score)

        if len(members[pb]) == 1:
            members[pb][b[0]] = (b[1], method, score)

        for store, member in members[pb].items():
            members[pa][store] = member
            product[(store, member[0])] = pa

        del members[pb]

    rows = []

    for stores in members.values():
        if len(stores) < 2:
            continue

        first = min(stores, key=STORES.index)
        product_id = f"{first}-{stores[first][0]}"
        rows += [
            {
                "product_id": product_id,
                "store": store,
                "code": code,
                "method": method,
                "score": "" if store == "kritikos" and method == "ean" else round(score, 2),
            }
            for store, (code, method, score) in stores.items()
        ]

    rows.sort(key=lambda r: (r["product_id"], STORES.index(r["store"])))

    return rows


def run(directory="catalog"):
    """Match all STORES and write MATCHES_PATH."""
    with open(WEIGHTS_PATH, encoding="utf-8") as f:
        saved = json.load(f)

    weights = [saved[name] for name in ["bias", *FEATURES]]

    products = load(directory=directory)
    found = pairs(products, weights)
    rows = cluster(match.read_csv(match.MATCHES_PATH), found)
    match.write_csv(MATCHES_PATH, match.MATCH_FIELDS, rows)

    stores = Counter(r["store"] for r in rows)
    methods = Counter((r["store"], r["method"]) for r in rows)
    print(f"{len({r['product_id'] for r in rows})} products in 2 or more stores")

    for store in STORES:
        print(
            f"{store}: {stores[store]} matched"
            f" ({methods[(store, 'ean')]} by EAN, {methods[(store, 'fuzzy')]} by name)"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("train", help="fit the scorer on the EAN matches")
    commands.add_parser("match", help="match all stores, write matches/matches.csv")
    args = parser.parse_args(argv)

    if args.command == "train":
        train()
    else:
        run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
