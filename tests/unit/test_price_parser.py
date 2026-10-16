import pytest

from utils.price_parser import parse_price, parse_price_range

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "text, expected",
    [
        ("$1,234.50", 1234.50),
        ("US $49.99", 49.99),
        ("ILS 220.00", 220.0),
        ("1.234,50 €", 1234.50),
        ("$49.99/ea", 49.99),
        ("$20.00 to $30.00", 20.0),
        ("1,234", 1234.0),
        ("12,50", 12.5),
        ("Free", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_price(text, expected):
    """Verify localized price strings parse to the expected numeric value."""
    assert parse_price(text) == expected


def test_parse_price_range():
    """Verify both ranged and single prices produce the expected bounds."""
    assert parse_price_range("US $20.00 to US $30.00") == (20.0, 30.0)
    assert parse_price_range("$25.00") == (25.0, 25.0)
