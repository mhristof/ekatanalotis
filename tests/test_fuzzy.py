import pytest

import fuzzy
import match


def product(name, brand="", size="", **extra):
    p = {"code": "1", "name": name, "brand": brand, "size": size, "ean": "", **extra}

    return {
        **p,
        "sizes": match.product_sizes(p),
        "brands": fuzzy.brand_keys(brand),
        "name_brands": fuzzy.brand_keys(name),
        "brand_latin": fuzzy.fold(match.latin(brand)),
        "numbers": fuzzy.numbers(p),
        "stems": fuzzy.stems(p),
    }


@pytest.mark.parametrize(
    "a, b",
    [
        ("papadopoulou", "papadopoyloy"),
        ("chrysi", "xrysh"),
        ("bira", "mpyra"),
        ("avga", "ayga"),
        ("choris", "xwris"),
    ],
)
def test_fold_both_greek_in_latin_spellings(a, b):
    assert fuzzy.fold(a) == fuzzy.fold(b)


def test_stems_of_efresh_slug_meet_greek_names():
    efresh = product(
        "Instant Coffee Nescafe (200g)", "Nescafe", slug="stigmiaios-kafes-nescafe-classic-200-g"
    )
    greek = product("Nescafe Classic Στιγμιαίος Καφές 200gr", "Nescafe")

    assert {"stigm", "kafes", "nesca", "class"} <= efresh["stems"] & greek["stems"]


def test_stems_without_sizes():
    assert fuzzy.stems({"name": "ΔΩΔΩΝΗ ΓΙΑΟΥΡΤΙ 8% 1Κ", "brand": "ΔΩΔΩΝΗ"}) == {
        "dodon",
        "giaur",
        "n8",
    }


def test_brand_keys_meet_across_spellings():
    assert fuzzy.brand_keys("NICO LAZARIDI") & fuzzy.brand_keys("ΚΤΗΜΑ Ν. ΛΑΖΑΡΙΔΗ")
    assert fuzzy.brand_keys("HBH") & fuzzy.brand_keys("ΗΒΗ")
    assert fuzzy.brand_keys("IFANTIS") & fuzzy.brand_keys("Υφαντής")


def test_candidates_same_size_and_brand_and_no_other_numbers():
    products = {
        ("kritikos", "1"): product("ΚΡΙ-ΚΡΙ ΓΙΑΟΥΡΤΙ ΣΤΡΑΓΓΙΣΤΟ 2% 3*200ΓΡ", "ΚΡΙ ΚΡΙ", "3*200gr"),
        ("ab", "2"): product("Γιαούρτι Στραγγιστό 2% Λιπαρά 3x200g", "ΚΡΙ ΚΡΙ", "600 γρ"),
        ("ab", "3"): product("Γιαούρτι Στραγγιστό 5% Λιπαρά 3x200g", "ΚΡΙ ΚΡΙ", "600 γρ"),
        ("ab", "4"): product("Γιαούρτι Στραγγιστό 2% 1kg", "ΚΡΙ ΚΡΙ", "1 κιλ"),
        ("ab", "5"): product("Γιαούρτι Στραγγιστό 2% 3x200g", "ΦΑΓΕ", "600 γρ"),
    }

    found = fuzzy.candidates(products)

    assert found[("kritikos", "1")]["ab"] == [("ab", "2")]


def test_candidates_brand_in_the_other_name():
    # sklavenitis files it under the line, mymarket under the maker
    products = {
        ("sklavenitis", "1"): product("ΦΑΓΕ Total Γιαούρτι Στραγγιστό 5% 500g", "TOTAL"),
        ("mymarket", "2"): product("ΦΑΓΕ Total Στραγγιστό Γιαούρτι 5% Λιπαρά 500gr", "ΦΑΓΕ"),
    }

    found = fuzzy.candidates(products)

    assert found[("sklavenitis", "1")]["mymarket"] == [("mymarket", "2")]
    assert found[("mymarket", "2")]["sklavenitis"] == [("sklavenitis", "1")]


def test_solve():
    assert fuzzy.solve([[2.0, 1.0], [1.0, 3.0]], [3.0, 5.0]) == pytest.approx([0.8, 1.4])


def test_fit_separates():
    rows = [([x / 10], float(x > 5)) for x in range(11)] * 3
    weights = fuzzy.fit(rows, l2=0.01)

    assert fuzzy.probability(weights, [0.9]) > 0.9
    assert fuzzy.probability(weights, [0.1]) < 0.1


def ean(product_id, store, code, score=""):
    return {"product_id": product_id, "store": store, "code": code, "method": "ean", "score": score}


def test_cluster_ean_first_one_code_per_store():
    ean_rows = [ean("kritikos-1", "kritikos", "1"), ean("kritikos-1", "ab", "a1", "0.3")]
    fuzzy_pairs = [
        (0.9, ("ab", "a2"), ("kritikos", "1")),  # ab already has a1: skipped
        (0.8, ("kritikos", "1"), ("sklavenitis", "s1")),
        (0.7, ("efresh", "e1"), ("sklavenitis", "s1")),
        (0.6, ("efresh", "e2"), ("xalkiadakis", "x1")),
    ]

    rows = fuzzy.cluster(ean_rows, fuzzy_pairs)

    assert [(r["product_id"], r["store"], r["code"], r["method"], r["score"]) for r in rows] == [
        ("kritikos-1", "kritikos", "1", "ean", ""),
        ("kritikos-1", "ab", "a1", "ean", 0.3),
        ("kritikos-1", "sklavenitis", "s1", "fuzzy", 0.8),
        ("kritikos-1", "efresh", "e1", "fuzzy", 0.7),
        ("xalkiadakis-x1", "xalkiadakis", "x1", "fuzzy", 0.6),
        ("xalkiadakis-x1", "efresh", "e2", "fuzzy", 0.6),
    ]


def test_cluster_keeps_ean_method_when_joined_by_name():
    ean_rows = [ean("kritikos-1", "kritikos", "1"), ean("kritikos-1", "ab", "a1", "0.3")]
    fuzzy_pairs = [(0.8, ("ab", "a1"), ("sklavenitis", "s1"))]

    rows = fuzzy.cluster(ean_rows, fuzzy_pairs)

    assert {(r["store"], r["method"]) for r in rows} == {
        ("kritikos", "ean"),
        ("ab", "ean"),
        ("sklavenitis", "fuzzy"),
    }
