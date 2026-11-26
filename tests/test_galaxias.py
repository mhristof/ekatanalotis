import galaxias


def item(**fields):
    return {
        "sku": "5203149004488",
        "name": "ΡΟΔΟΠΗ ΚΡΕΜΑ ΚΑΡΑΜΕΛΕ 160g ",
        "unit_measurement": "Κιλό",
        "cost_per_unit": "8.125",
        "categories": [{"name": "Είδη Ψυγείου", "level": 2}, {"name": "Κρέμες", "level": 3}],
        "price_range": {"minimum_price": {"final_price": {"value": 1.3}}},
        **fields,
    }


def response(items, pages=1):
    return {"data": {"products": {"page_info": {"total_pages": pages}, "items": items}}}


def test_parse():
    assert galaxias.parse(response([item()])) == [
        [
            "5203149004488",
            "ΡΟΔΟΠΗ ΚΡΕΜΑ ΚΑΡΑΜΕΛΕ 160g",
            1.3,
            {"category": "Κρέμες", "unit": "kg", "unit_price": 8.12, "ean": "5203149004488"},
        ]
    ]


def test_parse_without_a_unit_price_or_a_barcode():
    # in-store codes (prefix 2) are no EAN
    (row,) = galaxias.parse(response([item(sku="2101209000000", unit_measurement=None, cost_per_unit=None)]))

    assert row[3] == {"category": "Κρέμες", "unit": None, "unit_price": None, "ean": ""}


def test_fetch_page_stops_after_the_last_page(monkeypatch):
    requests = []

    class Response:
        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

    def get(url, params, headers):
        requests.append(params["query"])
        # magento answers a page past the last with an error and no products
        if "currentPage:3" in params["query"]:
            return Response({"errors": [{"message": "currentPage value 3 is greater than 2"}], "data": {"products": None}})

        return Response(response([item()], pages=2))

    monkeypatch.setattr(galaxias, "_pages", {})
    monkeypatch.setattr(galaxias.net, "get", get)

    assert galaxias.fetch_page("69", 1)
    assert galaxias.fetch_page("69", 2)
    # known to be past the last page: not requested
    assert galaxias.fetch_page("69", 3) == []
    assert len(requests) == 2
