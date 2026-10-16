from unittest.mock import MagicMock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pages.item_page import ItemPage


@pytest.mark.unit
def test_reads_cart_count_from_accessible_label():
    """Verify the cart item count is parsed from its accessible label."""
    page = MagicMock()
    cart_link = MagicMock()
    page.locator.return_value.count.return_value = 1
    page.locator.return_value.first = cart_link
    cart_link.get_attribute.return_value = "Your shopping cart contains 2 items"
    item = ItemPage(page, MagicMock())

    assert item._read_cart_count() == 2


@pytest.mark.unit
def test_add_to_cart_accepts_cart_count_increase_without_toast(monkeypatch):
    """Verify a cart-count increase confirms add-to-cart when no toast appears."""
    page = MagicMock()
    page.url = "https://www.ebay.com/itm/123456789"
    item = ItemPage(page, MagicMock())
    monkeypatch.setattr(item, "select_random_variants", lambda rng: 2)
    monkeypatch.setattr(item, "_read_cart_count", MagicMock(side_effect=[2, 3]))
    monkeypatch.setattr(item, "_wait_for_cart_count_increase", lambda count: count == 2)
    monkeypatch.setattr(item, "assert_not_blocked", lambda: None)
    page.get_by_text.return_value.first.wait_for.side_effect = PlaywrightTimeout("no toast")

    item.add_to_cart(MagicMock())


@pytest.mark.unit
def test_ignores_unrelated_select_error_outside_variant_panel():
    """Verify unrelated page text is not treated as a variant-selection error."""
    page = MagicMock()
    item = ItemPage(page, MagicMock())
    variant_panel = page.locator.return_value
    error_text = variant_panel.get_by_text.return_value
    error_text.count.return_value = 1
    error_text.nth.return_value.is_visible.return_value = False

    assert item._has_visible_variant_error() is False