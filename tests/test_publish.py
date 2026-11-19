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
    assert json.loads((site / "index.json").read_text())["stores"] == {"ab": "2026-11-18"}
