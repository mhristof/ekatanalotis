import pytest

import catalog
import sm


@pytest.mark.parametrize(
    "text, unit",
    [
        ("Τιμή λίτρου", "l"),
        ("/ κιλ", "kg"),
        ("κιλό", "kg"),
        ("ΤΕΜ", "piece"),
        ("τεμ.", "piece"),
        ("kilogram", "kg"),
        ("pcs", "piece"),
        ("lt", "l"),
        ("ΜΕΖ", "wash"),
        ("Τιμή τεμαχίου", "piece"),
    ],
)
def test_unit(text, unit):
    assert catalog.unit(text) == unit


def test_price():
    assert catalog.price("1,05€") == 1.05
    assert catalog.price("0.18&euro;") == 0.18
    assert catalog.price("") is None


def test_eans_keeps_valid_ean13_ean8_and_upc():
    assert catalog.eans(["5449000000996", "96385074", "036000291452"]) == (
        "0036000291452;5449000000996;96385074"
    )


def test_eans_drops_bad_check_digit_in_store_and_case_codes():
    assert catalog.eans(["5449000000997", "2270002486001", "15201314076619", "123"]) == ""


def test_products_skips_rows_without_details():
    rows = [["1", "a", 1.0], ["2", "b", 2.0, {"brand": "B", "unit_price": 4.0, "size": None}]]

    assert catalog.products(rows) == {
        "2": {
            "code": "2",
            "name": "b",
            "brand": "B",
            "category": "",
            "size": "",
            "unit": "",
            "unit_price": "4.0",
            "ean": "",
        }
    }


def test_update_merges_by_code(tmp_path):
    path = str(tmp_path / "catalog/store.csv")
    catalog.update(path, catalog.products([["2", "b", 1, {}], ["1", "a", 1, {"brand": "x"}]]))
    catalog.update(path, catalog.products([["1", "a2", 1, {"brand": "y,z"}]]))

    assert open(path).read() == (
        "code,name,brand,category,size,unit,unit_price,ean\n"
        '1,a2,"y,z",,,,,\n'
        "2,b,,,,,,\n"
    )


def test_save_catalog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    sm.save_catalog({"store": [["1", "a", 1.0, {"unit": "kg"}]]})

    assert (tmp_path / "catalog/store.csv").read_text().splitlines()[1] == "1,a,,,,kg,,"
