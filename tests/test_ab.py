import pytest

import ab


def product(name, label1, label2):
    return {
        "name": name,
        "manufacturerName": "DORITOS",
        "categories": [{"name": "Σνακ"}],
        "price": {"supplementaryPriceLabel1": label1, "supplementaryPriceLabel2": label2},
    }


@pytest.mark.parametrize(
    "name, size, unit",
    [
        ("Σνακ Καλαμποκιού Nacho Cheese 90g", "0,09 κιλ", "kg"),
        ("Αφρόλουτρο Βιολογικό 650ml", "0,65 λιτ", "l"),
        ("Καραμέλες Ζελίνια 85γρ", "0,85 κιλ", "kg"),
    ],
)
def test_details_corrects_a_fraction_of_a_piece(name, size, unit):
    # ab gives 17,11 €/kg as "17,11 €/τεμ" of "0,09 τεμ"
    amount = size.split()[0]
    found = ab.details(product(name, "17,11 €/τεμ", f"{amount} τεμ"))

    assert (found["size"], found["unit"], found["unit_price"], found["unit_fixed"]) == (size, unit, 17.11, "piece")


def test_details_keeps_real_pieces():
    found = ab.details(product("Αγγούρια Τεμάχιο Ελληνικά", "0,73 €/τεμ", "1 τεμ"))

    assert (found["unit"], "unit_fixed" in found) == ("piece", False)


def test_details_keeps_a_fraction_without_a_size_in_the_name():
    # nothing to correct it from
    found = ab.details(product("Λουρί Σκύλου Πτυσσόμενο Small 1 Τεμάχιο", "192,86 €/τεμ", "0,07 τεμ"))

    assert (found["unit"], "unit_fixed" in found) == ("piece", False)
