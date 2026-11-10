import kritikos


def test_parse_price_in_cents():
    data = {"payload": {"products": [{"sku": "713664", "displayName": "Μπανάνες", "finalPrice": 195}]}}

    assert [row[:3] for row in kritikos.parse(data)] == [["713664", "Μπανάνες", 1.95]]


def test_parse_details():
    item = {
        "sku": "102694",
        "displayName": "NOXZEMA Sensitive",
        "finalPrice": 570,
        "name": "NOXZEMA ΑΦΡΟΣ EYAIΣΘΗΤΑ 300ML",
        "brand": "NOXZEMA",
        "categoryKind": "Αφρός Ξυρίσματος",
        "quantity": "300ml",
        "unitOfMeasurement": "ΛΙΤ",
        "unitOfMeasurementFinalPrice": 1900,
        # a GTIN-14 case, an in-store code, a bad check digit and two EANs
        "barcodes": ["15201314076619", "22700024865", "5201314076613", "5201314076612", "5201314208006"],
    }

    (row,) = kritikos.parse({"payload": {"products": [item]}})

    assert row[3] == {
        "name": "NOXZEMA ΑΦΡΟΣ EYAIΣΘΗΤΑ 300ML",
        "brand": "NOXZEMA",
        "category": "Αφρός Ξυρίσματος",
        "size": "300ml",
        "unit": "l",
        "unit_price": 19.0,
        "ean": "5201314076612;5201314208006",
    }
