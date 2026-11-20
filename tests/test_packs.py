import packs

FIELDS = {"brand": "", "category": "", "size": "", "unit": "", "unit_price": "", "ean": ""}


def product(code, name, **fields):
    return {**FIELDS, "code": code, "name": name, **fields}


def test_cheaper_pack_of_the_same_product():
    products = {
        "1": product("1", "FINISH Ταμπλέτες Λεμόνι 22τεμ", unit="piece", unit_price="0.36"),
        "2": product("2", "FINISH Ταμπλέτες Λεμόνι 48τεμ", unit="piece", unit_price="0.27"),
        # another variant
        "3": product("3", "FINISH Quantum Ταμπλέτες Λεμόνι 120τεμ", unit="piece", unit_price="0.16"),
    }

    found = packs.cheaper(products, {"1": 7.92, "2": 12.96, "3": 19.2})

    assert list(found) == ["1"]
    assert found["1"]["unit_price"] == 0.36
    assert found["1"]["cheaper"] == [["2", "FINISH Ταμπλέτες Λεμόνι 48τεμ", 12.96, 0.27, False]]


def test_unit_price_from_the_size_not_a_stale_store_one():
    products = {
        # the store says 10.75 and 13.67 €/kg, the prices say 14.38 and 10.25
        "1": product("1", "7 Days Strudel Μήλο 80 gr", unit="kg", unit_price="10.75"),
        "2": product("2", "7 Days Strudel Μήλο 3 x 80 gr", unit="kg", unit_price="13.67"),
    }

    found = packs.cheaper(products, {"1": 1.15, "2": 2.46})

    assert list(found) == ["1"]
    assert found["1"]["cheaper"][0][3] == 10.25
    assert found["1"]["cheaper"][0][4] is True


def test_variants_numbers_and_same_sizes_are_not_alternatives():
    products = {
        "1": product("1", "ΦΑΓΕ Total Γιαούρτι 500gr", unit="kg"),
        "2": product("2", "ΦΑΓΕ Total Γιαούρτι 2% 1kg", unit="kg"),
        "3": product("3", "Pampers Pants Size 4 35τεμ", unit="piece"),
        "4": product("4", "Pampers Pants Size 3 76τεμ", unit="piece"),
        # one name, one size: two products, not a pack size
        "5": product("5", "Surimi 250 g", unit="kg"),
        "6": product("6", "Surimi 250 g", unit="kg"),
    }

    assert packs.cheaper(products, {"1": 3, "2": 4, "3": 9.27, "4": 20, "5": 5, "6": 3}) == {}


def test_store_unit_price_when_the_size_is_way_off():
    # '5x550 g' is 5x55g: 41.45 €/kg, not 4.15
    p = product("1", "Nescafe (5x550 g)", unit="kg", unit_price="41.455")

    assert packs.unit_price(p, 11.4) == ("kg", 41.455, None)
