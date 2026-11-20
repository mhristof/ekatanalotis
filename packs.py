"""Cheaper pack sizes of the same product in the same store: 'the 48 pack
is 25% cheaper per tablet', or the other way round when a big pack costs
more per unit than the small one.

Products are the same when their names (and efresh's slugs) have the same
words and numbers once the sizes are taken out (fuzzy.stems()): fat %,
stars and nappy sizes keep variants apart. The unit price is worked out
from the latest price and the pack size in the name or size field, as the
stores' own unit prices can be stale (an offer changes the price, not the
unit price); the store's unit price is used when there's no size, or when
the two disagree by more than WAY_OFF (a misparsed size, or a store typo
like '5x550g')."""

import re

import fuzzy
import match

# the catalog's unit -> (match.sizes() unit, how many of it are one unit)
UNITS = {"kg": ("g", 1000), "l": ("ml", 1000), "piece": ("piece", 1), "wash": ("wash", 1)}
# an alternative this much cheaper per unit is worth showing
SAVING = 0.1
WAY_OFF = 2
MAX_SHOWN = 3
MULTIPACK = re.compile(r"\d+\s*[x*χ×]\s*\d")


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def unit_of(product, sizes):
    """The catalog's unit, or the unit of the sizes when it has none (a
    weight or volume before a piece count)."""
    if product["unit"] in UNITS:
        return product["unit"]

    found = {u for _, u in sizes}

    for unit, (base, _) in UNITS.items():
        if base in found:
            return unit

    return None


def unit_price(product, price):
    """(unit, unit price, quantity in the unit's base) of a product at
    price; quantity is None when it came from the store's unit price."""
    sizes = match.product_sizes(product)
    unit = unit_of(product, sizes)

    if not unit or not price:
        return None

    base, per = UNITS[unit]
    store = number(product["unit_price"]) if product["unit"] == unit else None
    quantities = sorted({q for q, u in sizes if u == base and q > 0})

    if quantities:
        # 'Snickers 50gr 3τεμ' is 50g or 150g: the one the store agrees with
        q = min(quantities, key=lambda q: abs(price / q * per - store)) if store else quantities[0]
        computed = price / q * per

        if len(quantities) == 1 or store:
            if not store or 1 / WAY_OFF <= computed / store <= WAY_OFF:
                return unit, round(computed, 4), q

    return (unit, store, None) if store else None


def multipack(product):
    return bool(MULTIPACK.search(match.normalise(product["name"])))


def cheaper(products, prices):
    """{code: {name, unit, unit_price, multipack, cheaper: [[code, name,
    price, unit_price, multipack], ...]}} of one store's products that
    have a pack at least SAVING cheaper per unit, cheapest first.

    products: the store's catalog, prices: {code: price} of the products
    it sells now."""
    groups = {}

    for code, p in products.items():
        found = unit_price(p, prices.get(code))

        if found and found[1]:
            unit, value, quantity = found
            key = (unit, frozenset(fuzzy.stems(p)))
            groups.setdefault(key, []).append((value, code, quantity))

    out = {}

    for (unit, _), group in groups.items():
        if len(group) < 2:
            continue

        group.sort()

        for value, code, quantity in group:
            better = [
                (v, c)
                for v, c, q in group
                if v <= value * (1 - SAVING)
                # the same size twice is two products with one name
                and not (q and quantity and abs(q - quantity) < match.TOLERANCE * max(q, quantity))
            ][:MAX_SHOWN]

            if better:
                p = products[code]
                out[code] = {
                    "name": p["name"],
                    "unit": unit,
                    "unit_price": value,
                    "multipack": multipack(p),
                    "cheaper": [
                        [c, products[c]["name"], prices[c], v, multipack(products[c])] for v, c in better
                    ],
                }

    return out
