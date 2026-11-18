import pytest

import match


def product(name="", brand="", size="", code="1", ean=""):
    return {"code": code, "name": name, "brand": brand, "size": size, "ean": ean}


@pytest.mark.parametrize(
    "text, sizes",
    [
        ("4*125gr", {(500, "g")}),
        ("1,5L", {(1500, "ml")}),
        ("500γρ.", {(500, "g")}),
        ("1 κιλ", {(1000, "g")}),
        ("Χαρτί Κουζίνας Giga 2x400g", {(800, "g")}),
        ("Κάψουλες Καφέ 10x5.2g", {(52, "g")}),
        ("ZEWA Χ.ΥΓΕΙΑΣ DELUXE 8ΑΡΙ LAVENDER 704ΓΡ", {(8, "piece"), (704, "g")}),
        ("28 μεζ", {(28, "wash")}),
        ("Χρυσά Αυγά Φρέσκα 10άδα", {(10, "piece")}),
        ("33cl", {(330, "ml")}),
        ("Κιλό", set()),
        ("Τιμή Κιλού", set()),
    ],
)
def test_sizes(text, sizes):
    assert match.sizes(text) == sizes


def test_same_size_compares_totals_within_5_percent():
    assert match.same_size(product(size="6*330ml"), product(size="1,98 λιτ"))
    assert match.same_size(product(size="500γρ."), product(name="Ρύζι 510g"))
    # a single can is not the 6 pack
    assert match.same_size(product(size="6*330ml"), product(size="330 ml")) is False


def test_same_size_unknown_without_a_shared_unit():
    assert match.same_size(product(size="Κιλό"), product(size="1 κιλ")) is None
    assert match.same_size(product(size="500γρ."), product(size="1 λιτ")) is None


def test_same_brand_across_scripts_and_spelling():
    assert match.same_brand(product(brand="PAPOUTSANIS"), product(brand="ΠΑΠΟΥΤΣΑΝΗΣ"))
    assert match.same_brand(product(brand="COCA-COLA"), product(brand="Coca Cola"))
    assert match.same_brand(product(brand="NOXZEMA"), product(brand="GILLETTE")) is False
    assert match.same_brand(product(brand=""), product(brand="GILLETTE")) is None


def test_same_brand_in_the_other_name():
    assert match.same_brand(
        product(name="Lavazza Καφές Qualita Oro 250gr", brand="Luigi Lavazza Spa"),
        product(brand="LAVAZZA"),
    )


def test_verdict():
    kritikos = product("NESCAFE CLASSIC 200ΓΡ", "NESCAFE", "200γρ.")

    assert match.verdict(kritikos, product("Στιγμιαίος Καφές 200g", "NESCAFE", "200 γρ")) == "ok"
    assert match.verdict(kritikos, product("Classic 100g", "NESCAFE", "100 γρ")) == "size"
    assert match.verdict(kritikos, product("Καφές 100g", "JACOBS", "100 γρ")) == "size,brand"


def test_pending_skips_found_and_fully_searched_products():
    products = [
        product(code="1", ean="5449000000996"),
        product(code="2", ean="5201314076612;96385074"),
        product(code="3", ean="5000112637922"),
    ]
    results = [
        {"store": "ab", "ean": "5449000000996", "code": "7"},
        {"store": "ab", "ean": "5201314076612", "code": ""},
        {"store": "mymarket", "ean": "5000112637922", "code": ""},
    ]

    assert [p["code"] for p in match.pending(products, results, "ab")] == ["2", "3"]
    assert [p["code"] for p in match.pending(products, results, "mymarket")] == ["1", "2"]


def test_product_eans_ean13_first():
    assert match.product_eans(product(ean="96385074;5449000000996")) == [
        "5449000000996",
        "96385074",
    ]


def test_matches_best_hit_and_each_store_code_once():
    products = {
        "1": product("NOXZEMA ΑΦΡΟΣ SENSITIVE 300ML", "NOXZEMA", "300ml", "1", "5201314076612"),
        "2": product("NOXZEMA ΑΦΡΟΣ CLASSIC 300ML", "NOXZEMA", "300ml", "2", "5201314076629"),
    }
    results = [
        {"store": "ab", "ean": "5201314076612", "code": "9"},
        {"store": "ab", "ean": "5201314076629", "code": "9"},
        {"store": "ab", "ean": "5201314076629", "code": "8"},
    ]
    catalogs = {
        "ab": {
            "9": product("Αφρός Ξυρίσματος Classic 300ml", "NOXZEMA", "300 ml", "9"),
            "8": product("Αφρός Ξυρίσματος Μπλε 100ml", "NOXZEMA", "100 ml", "8"),
        }
    }

    found = match.candidates(products, results, catalogs)

    assert [(c["kritikos"], c["code"], c["verdict"]) for c in found] == [
        ("2", "9", "ok"),
        ("1", "9", "ok"),
        ("2", "8", "size"),
    ]
    assert match.matches(found) == [
        {"product_id": "kritikos-2", "store": "ab", "code": "9", "method": "ean", "score": found[0]["score"]},
        {"product_id": "kritikos-2", "store": "kritikos", "code": "2", "method": "ean", "score": ""},
    ]
