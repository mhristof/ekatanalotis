import pytest

import masoutis


def item(**fields):
    return {
        "Itemcode": "0380626",
        "ItemDescr": "Νουνού Family Γάλα 3,6% Λιπαρά 1lt.",
        "StartPrice": 1.98,
        "PosPrice": 1.98,
        "ItemVolume": "1.98€/λιτ",
        "BrandNameDesciption": "ΝΟΥΝΟΥ",
        "TeamId": "01141015",
        "breadcrumbLinkL2": "Είδη Ψυγείου",
        "PassKey": 94,
        **fields,
    }


@pytest.fixture(autouse=True)
def menu(monkeypatch):
    monkeypatch.setattr(masoutis, "categories", lambda: {"011410": "Γάλα"})
    monkeypatch.setattr(masoutis, "_totals", {})


def test_parse():
    assert masoutis.parse([item()]) == [
        [
            "0380626",
            "Νουνού Family Γάλα 3,6% Λιπαρά 1lt.",
            1.98,
            {"brand": "ΝΟΥΝΟΥ", "category": "Γάλα", "unit": "l", "unit_price": 1.98},
        ]
    ]


def test_parse_offer_and_weighed():
    # the price now, per kg for weighed products
    (row,) = masoutis.parse(
        [
            item(
                Itemcode="3568433",
                ItemDescr="Σπάλα Βόεια Άνευ Οστού Γαλλίας Νωπή ",
                StartPrice=14.99,
                PosPrice=12.99,
                ItemVolume="12.99€/κιλ",
                BrandNameDesciption="NO BRAND",
                TeamId="01111010",
            )
        ]
    )

    assert row == [
        "3568433",
        "Σπάλα Βόεια Άνευ Οστού Γαλλίας Νωπή",
        12.99,
        {"brand": None, "category": "Είδη Ψυγείου", "unit": "kg", "unit_price": 12.99},
    ]


def test_parse_skips_products_without_a_price():
    assert masoutis.parse([item(PosPrice=None), item(PosPrice=0)]) == []


def test_fetch_page_stops_after_the_last_page(monkeypatch):
    calls = []

    def call(name, body):
        calls.append(body["IfWeight"])

        return [item(PassKey=94)]

    monkeypatch.setattr(masoutis, "call", call)

    assert masoutis.fetch_page("568,011410", 1)
    assert masoutis.fetch_page("568,011410", 2)
    # 94 products are 2 pages of 50, page 3 is not requested
    assert masoutis.fetch_page("568,011410", 3) == []
    assert calls == ["1", "2"]


def test_fetch_page_past_the_end_when_the_total_is_not_known_yet(monkeypatch):
    # pages are fetched ahead, so page 3 can come back before page 1
    monkeypatch.setattr(masoutis, "call", lambda name, body: [item(PassKey=94)])

    assert masoutis.fetch_page("568,011410", 3) == []


def test_fetch_page_empty(monkeypatch):
    monkeypatch.setattr(masoutis, "call", lambda name, body: [])

    assert masoutis.fetch_page("568", 1) == []


def test_masoutis_keeps_one_row_per_code(monkeypatch):
    pages = {("562", 1): [item()], ("568", 1): [item(), item(Itemcode="4089678")]}
    monkeypatch.setattr(
        masoutis, "fetch_page", lambda section, page: masoutis.parse(pages.get((section, page), []))
    )

    rows = masoutis.masoutis(sections=["562", "568"])

    assert sorted(r[0] for r in rows) == ["0380626", "4089678"]
