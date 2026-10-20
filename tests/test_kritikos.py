import kritikos


def test_parse_price_in_cents():
    data = {"payload": {"products": [{"sku": "713664", "displayName": "Μπανάνες", "finalPrice": 195}]}}

    assert kritikos.parse(data) == [["713664", "Μπανάνες", 1.95]]
