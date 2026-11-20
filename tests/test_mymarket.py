import pytest

import mymarket


@pytest.mark.parametrize(
    "label, unit_price, unit",
    [
        ("Τιμή κιλού", 32.6, "kg"),
        ("Τελ. τιμή κιλού", 32.6, "kg"),
        # the product's offer price, not a unit price
        ("Τελ. τιμή", None, None),
    ],
)
def test_details_unit_price(label, unit_price, unit):
    body = (
        '<div class="measure-label-wrapper">\n'
        f'  <span class="font-semibold">32,60€</span>\n  <span>{label}</span>\n</div>'
    )

    found = mymarket.details({}, body)

    assert (found["unit_price"], found["unit"]) == (unit_price, unit)
