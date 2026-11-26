import json

import publish


def test_latest_files_newest_per_store():
    names = [
        "smdata/ab-2026-11-17.csv",
        "smdata/ab-2026-11-18.csv\n",
        "smdata/xalkiadakis-2026-11-11.csv",
        "smdata/lidl-2026-11-18.csv",
        "smdata/README",
    ]

    assert publish.latest_files(names) == {
        "ab": ("2026-11-18", "smdata/ab-2026-11-18.csv"),
        "xalkiadakis": ("2026-11-11", "smdata/xalkiadakis-2026-11-11.csv"),
    }


def test_needed_files_newer_than_history_and_latest():
    names = [
        "smdata/ab-2026-11-16.csv",
        "smdata/ab-2026-11-17.csv",
        "smdata/ab-2026-11-18.csv",
        "smdata/efresh-2026-11-10.csv",
        "smdata/efresh-2026-11-11.csv",
    ]

    assert publish.needed_files(names, {"ab": "2026-11-16", "efresh": "2026-11-11"}) == [
        "smdata/ab-2026-11-17.csv",
        "smdata/ab-2026-11-18.csv",
        "smdata/efresh-2026-11-11.csv",
    ]


def test_update_history_keeps_price_changes(tmp_path):
    prices = tmp_path / "smdata"
    prices.mkdir()
    (prices / "ab-2026-11-16.csv").write_text("2026-11-16,a1,Καφές,4.00\n")
    (prices / "ab-2026-11-17.csv").write_text("2026-11-17,a1,Καφές,4.00\n2026-11-17,a2,Τσάι,1.10\n")
    history = tmp_path / "history"

    publish.update_history(prices, history)
    # a second run only adds the new file
    (prices / "ab-2026-11-18.csv").write_text("2026-11-18,a1,Καφές,4.20\n2026-11-18,a2,Τσάι,1.10\n")
    publish.update_history(prices, history)

    assert (history / "ab.csv").read_text() == (
        "code,date,price\na1,2026-11-16,4\na1,2026-11-18,4.2\na2,2026-11-17,1.1\n"
    )
    assert json.loads((history / "dates.json").read_text()) == {"ab": "2026-11-18"}


def test_matched_products_name_from_preferred_store():
    rows = [
        {"product_id": "kritikos-1", "store": "kritikos", "code": "1"},
        {"product_id": "kritikos-1", "store": "ab", "code": "a1"},
        {"product_id": "kritikos-1", "store": "mymarket", "code": "m1"},
    ]
    catalogs = {
        "kritikos": {"1": {"name": "NESCAFE CLASSIC 200ΓΡ", "brand": "NESCAFE", "size": "200γρ."}},
        "ab": {"a1": {"name": "Στιγμιαίος Καφές 200g", "brand": "NESCAFE", "size": "200 γρ"}},
        # mymarket's code is not in its catalog: the next store is shown
        "mymarket": {},
    }

    assert publish.matched_products(rows, catalogs) == {
        "kritikos-1": {
            "name": "Στιγμιαίος Καφές 200g",
            "brand": "NESCAFE",
            "size": "200 γρ",
            "codes": {"kritikos": "1", "ab": "a1", "mymarket": "m1"},
        }
    }


def test_build(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "smdata").mkdir()
    (tmp_path / "smdata" / "ab-2026-11-17.csv").write_text("2026-11-17,a1,Καφές,4.00\n")
    (tmp_path / "smdata" / "ab-2026-11-18.csv").write_text(
        "2026-11-18,a1,Καφές,4.20\n2026-11-18,a2,Τσάι,1.10\n"
    )
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "ab.csv").write_text(
        "code,name,brand,category,size,unit,unit_price,ean\n"
        "a1,Καφές 200g,NESCAFE,Καφές,200 γρ,kg,21.0,\n"
    )
    (tmp_path / "matches").mkdir()
    (tmp_path / "matches" / "matches.csv").write_text(
        "product_id,store,code,method,score\nab-a1,ab,a1,fuzzy,0.9\nab-a1,efresh,e1,fuzzy,0.9\n"
    )

    (tmp_path / "history").mkdir()
    (tmp_path / "history" / "ab.csv").write_text("code,date,price\na1,2026-11-17,4\na1,2026-11-18,4.2\n")

    publish.build()

    site = tmp_path / "site"
    assert json.loads((site / "latest" / "ab.json").read_text()) == {
        "date": "2026-11-18",
        "prices": {"a1": [4.2, 21.0, "kg"], "a2": [1.1, None, None]},
    }
    assert json.loads((site / "products.json").read_text())["ab-a1"]["codes"] == {
        "ab": "a1",
        "efresh": "e1",
    }
    assert json.loads((site / "history" / "ab-a1.json").read_text()) == {
        "ab": [["2026-11-17", 4.0], ["2026-11-18", 4.2]]
    }
    assert json.loads((site / "packs" / "ab.json").read_text()) == {}
    assert json.loads((site / "index.json").read_text())["stores"] == {"ab": "2026-11-18"}


def test_prices_flags_a_corrected_unit(tmp_path):
    path = tmp_path / "ab-2026-11-26.csv"
    path.write_text("2026-11-26,1,Doritos Nacho 90g,1.54\n2026-11-26,2,Γάλα 1lt,1.98\n")
    products = {
        "1": {"unit_price": "17.11", "unit": "kg", "unit_fixed": "piece"},
        "2": {"unit_price": "1.98", "unit": "l", "unit_fixed": ""},
    }

    assert publish.prices(str(path), products) == {
        "1": [1.54, 17.11, "kg", "piece"],
        "2": [1.98, 1.98, "l"],
    }


def test_trusted_starts_efresh_history_at_the_fix():
    points = [["2026-10-01", 0.08], ["2026-11-07", 1.65], ["2026-11-20", 3.72]]

    # the price on 2026-11-11 is the one in effect then
    assert publish.trusted("efresh", points) == [["2026-11-11", 1.65], ["2026-11-20", 3.72]]


def test_trusted_keeps_a_change_on_the_day():
    points = [["2026-11-07", 1.65], ["2026-11-11", 3.72]]

    assert publish.trusted("efresh", points) == [["2026-11-11", 3.72]]


def test_trusted_keeps_other_stores_and_new_products():
    points = [["2025-01-01", 1.0], ["2026-11-20", 2.0]]

    assert publish.trusted("ab", points) == points
    assert publish.trusted("efresh", [["2026-11-20", 2.0]]) == [["2026-11-20", 2.0]]
