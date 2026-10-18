import pytest

from decimal import Decimal

from utils.price_parser import Money, parse_money, parse_price, parse_price_range

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


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2 for $19.99", Money(Decimal("19.99"), "USD")),
        ("save 20% now $90.00", Money(Decimal("90.00"), "USD")),
        ("$59.99 + $10 shipping", Money(Decimal("59.99"), "USD")),
        ("ILS 52.54 to ILS 80.00", Money(Decimal("52.54"), "ILS")),
        ("C $2.49", Money(Decimal("2.49"), "CAD")),
        ("1.234,50 €", Money(Decimal("1234.50"), "EUR")),
        ("12,50", Money(Decimal("12.50"), None)),
    ],
)
def test_parse_money_prefers_currency_marked_amount(text, expected):
    """Verify quantities, percentages and shipping are not mistaken for the price."""
    assert parse_money(text) == expected


def test_shipping_after_price_is_not_a_range():
    """Verify only an explicit "to" joins two amounts into a range."""
    assert parse_price_range("$59.99 + $10 shipping") == (59.99, 59.99)
