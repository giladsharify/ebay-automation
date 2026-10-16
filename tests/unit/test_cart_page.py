from unittest.mock import MagicMock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pages.cart_page import CartPage


@pytest.mark.unit
def test_read_total_skips_currency_label_without_amount(monkeypatch):
    """Verify a currency-only line is skipped until a numeric subtotal is found."""
    page = MagicMock()
    page.locator.return_value.inner_text.return_value = "Subtotal\nILS\nILS 25.00"
    settings = MagicMock()
    cart = CartPage(page, settings)
    monkeypatch.setattr(cart, "assert_not_blocked", lambda: None)
    monkeypatch.setattr(cart, "screenshot", lambda name: None)

    assert cart.read_total() == 25.0


@pytest.mark.unit
def test_read_total_returns_zero_for_explicit_empty_cart(monkeypatch):
    """Verify an explicitly empty cart has a zero subtotal."""
    page = MagicMock()
    page.get_by_text.return_value.first.wait_for.side_effect = PlaywrightTimeout("no subtotal")
    page.locator.return_value.inner_text.return_value = "Your shopping cart is empty"
    cart = CartPage(page, MagicMock())
    monkeypatch.setattr(cart, "assert_not_blocked", lambda: None)
    monkeypatch.setattr(cart, "screenshot", lambda name: None)

    assert cart.read_total() == 0.0


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
