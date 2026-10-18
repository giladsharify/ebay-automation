from unittest.mock import MagicMock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from decimal import Decimal

from pages.cart_page import CartPage, item_id_from_url
from utils.price_parser import Money


@pytest.mark.unit
def test_read_total_skips_currency_label_without_amount(monkeypatch):
    """Verify a currency-only line is skipped until a numeric subtotal is found."""
    page = MagicMock()
    page.locator.return_value.inner_text.return_value = "Subtotal\nILS\nILS 25.00"
    settings = MagicMock()
    cart = CartPage(page, settings)
    monkeypatch.setattr(cart, "assert_not_blocked", lambda: None)
    monkeypatch.setattr(cart, "screenshot", lambda name: None)

    assert cart.read_total() == Money(Decimal("25.00"), "ILS")


@pytest.mark.unit
def test_read_total_returns_zero_for_explicit_empty_cart(monkeypatch):
    """Verify an explicitly empty cart has a zero subtotal."""
    page = MagicMock()
    page.get_by_text.return_value.first.wait_for.side_effect = PlaywrightTimeout("no subtotal")
    page.locator.return_value.inner_text.return_value = "Your shopping cart is empty"
    cart = CartPage(page, MagicMock())
    monkeypatch.setattr(cart, "assert_not_blocked", lambda: None)
    monkeypatch.setattr(cart, "screenshot", lambda name: None)

    assert cart.read_total().amount == 0


@pytest.mark.unit
def test_read_total_fails_if_subtotal_and_empty_message_are_missing(monkeypatch):
    """Verify an unexpected cart page does not silently become a zero subtotal."""
    page = MagicMock()
    page.get_by_text.return_value.first.wait_for.side_effect = PlaywrightTimeout("no subtotal")
    page.locator.return_value.inner_text.return_value = "Unexpected cart page"
    cart = CartPage(page, MagicMock())
    monkeypatch.setattr(cart, "assert_not_blocked", lambda: None)
    monkeypatch.setattr(cart, "screenshot", lambda name: None)

    with pytest.raises(AssertionError, match="neither a subtotal nor an empty-cart message"):
        cart.read_total()


@pytest.mark.unit
def test_reads_items_count_from_order_summary():
    """Verify the "Items (N)" summary line is parsed."""
    page = MagicMock()
    page.locator.return_value.inner_text.return_value = "Order summary\nItems (5)\nILS 318.17"

    assert CartPage(page, MagicMock()).read_items_count() == 5


@pytest.mark.unit
@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.ebay.com/itm/195500334487?var=495370767510", "195500334487"),
        ("https://www.ebay.com/itm/Some-Title/296604499668", "296604499668"),
        ("https://www.ebay.com/sch/i.html", None),
    ],
)
def test_item_id_from_url(url, expected):
    """Verify item ids are extracted from cart and search URLs alike."""
    assert item_id_from_url(url) == expected
