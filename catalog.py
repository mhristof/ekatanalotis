"""Product details for matching products across stores, kept next to the
daily prices in catalog/<store>.csv: one row per product code ever seen,
updated in place by every run.

Fetchers return rows as [code, name, price, details], where details is a
dict with any of FIELDS; the price csv files only use the first three."""

import csv
import os
import re
import unicodedata

FIELDS = ["code", "name", "brand", "category", "size", "unit", "unit_price", "ean"]

# unit prefixes, after lowercasing and removing accents
UNITS = [
    ("kg", ("κιλ", "kg", "kilo")),
    ("l", ("λιτ", "lt", "lit", "l")),
    ("piece", ("τεμ", "τμχ", "κομ", "piece", "pcs")),
    ("wash", ("μεζ", "wash")),
    ("m", ("μετρ", "m")),
]


def strip_accents(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def unit(text):
    """The unit a unit price is per: kg, l, piece, wash, m, or the text
    itself, e.g. 'Τιμή λίτρου', '/ κιλ', 'ΤΕΜ', 'kilogram'."""
    text = strip_accents(text or "").lower().replace("τιμη", "").strip(" /.:")

    for name, prefixes in UNITS:
        if text.startswith(prefixes):
            return name

    return text


def price(text):
    """'1,05€', '3,47 €', '0.18&euro;' -> 1.05, 3.47, 0.18; None if there is
    no number."""
    m = re.search(r"\d+(?:[.,]\d+)?", text or "")

    return float(m.group(0).replace(",", ".")) if m else None


def valid_ean(code):
    """EAN-13 or EAN-8 with a valid check digit, and not an in-store code
    (prefix 2, used for weighed products and the store's own labels)."""
    if not code.isdigit() or len(code) not in (8, 13) or code[0] == "2":
        return False

    digits = [int(c) for c in code]
    total = sum(d * (3 if i % 2 else 1) for i, d in enumerate(reversed(digits[:-1]), 1))

    return (10 - total % 10) % 10 == digits[-1]


def eans(codes):
    """The valid EANs in codes, 12 digit UPCs as EAN-13, joined by ';'."""
    codes = {c if len(c) != 12 else "0" + c for c in codes}

    return ";".join(sorted(c for c in codes if valid_ean(c)))


def path(store, directory="catalog"):
    return f"{directory}/{store}.csv"


def read(path):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return {row["code"]: row for row in csv.DictReader(f)}
    except FileNotFoundError:
        return {}


def write(path, products):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(products[code] for code in sorted(products))


def products(rows):
    """{code: catalog row} for the fetcher rows that have details."""
    out = {}

    for row in rows:
        if len(row) < 4:
            continue

        code, name, _, details = row[:4]
        product = {field: "" for field in FIELDS}
        product.update({k: v for k, v in details.items() if v not in (None, "")})
        product.update(code=str(code), name=product["name"] or name)
        out[str(code)] = {k: str(v).strip() for k, v in product.items()}

    return out


def update(path, new):
    """Add or replace the products in new; products no longer listed are
    kept, they often come back."""
    products = read(path)
    products.update(new)
    write(path, products)

    return len(new)
