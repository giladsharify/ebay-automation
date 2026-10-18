from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from flows import shopping_flow as shopping_flow_module
from flows.shopping_flow import ShoppingFlow
from utils.price_parser import Money

pytestmark = pytest.mark.unit

URLS = ["https://www.ebay.com/itm/111", "https://www.ebay.com/itm/222"]


def _flow(total: str, currency: str = "ILS", cart_ids=("111", "222"), count=2) -> ShoppingFlow:
    """Build a flow whose cart page reports the given state."""
    flow = ShoppingFlow.__new__(ShoppingFlow)
    flow.log = MagicMock()
    flow._added_urls = list(URLS)
    flow.search_page = MagicMock(result_currency="ILS")
    flow.cart_page = MagicMock()
    flow.cart_page.read_total.return_value = Money(Decimal(total), currency)
    flow.cart_page.read_item_ids.return_value = set(cart_ids)
    flow.cart_page.read_items_count.return_value = count
    return flow


def test_passes_when_total_is_within_budget():
    """Verify a cart with the added items and a total under the threshold passes."""
    flow = _flow("440.00")

    flow.assert_cart_total_not_exceeds(budget_per_item=220, items_count=2)

    flow.cart_page.open.assert_called_once_with()


def test_fails_when_total_exceeds_budget():
    """Verify the whole cart total, not a delta, is compared with budget x count."""
    with pytest.raises(AssertionError, match="Cart total 440.01 ILS exceeds threshold 440"):
        _flow("440.01").assert_cart_total_not_exceeds(budget_per_item=220, items_count=2)


def test_fails_when_cart_currency_differs_from_search_currency():
    """Verify amounts in different currencies are never compared."""
    with pytest.raises(AssertionError, match="Cart total is in USD but item prices were compared in ILS"):
        _flow("10.00", currency="USD").assert_cart_total_not_exceeds(220, 2)


def test_fails_when_an_added_item_is_missing_from_cart():
    """Verify each added item must actually be in the cart."""
    with pytest.raises(AssertionError, match=r"missing from the cart: \['222'\]"):
        _flow("10.00", cart_ids=("111",)).assert_cart_total_not_exceeds(220, 2)


def test_fails_when_cart_item_count_differs():
    """Verify the cart's item count matches the number of added items."""
    with pytest.raises(AssertionError, match="Cart shows 3 item"):
        _flow("10.00", count=3).assert_cart_total_not_exceeds(220, 2)


def test_add_items_requires_an_empty_cart(monkeypatch):
    """Verify the scenario stops before adding anything when the cart is not empty."""
    tab = MagicMock()
    flow = ShoppingFlow.__new__(ShoppingFlow)
    flow.page = MagicMock()
    flow.page.context.new_page.return_value = tab
    flow.settings = MagicMock()

    class NonEmptyCart:
        def __init__(self, page, settings):
            """Create a cart stub that already holds items."""

        def open(self):
            """Stand in for navigating to the cart."""

        def read_total(self):
            """Return a non-zero existing subtotal."""
            return Money(Decimal("45.50"), "ILS")

    monkeypatch.setattr(shopping_flow_module, "CartPage", NonEmptyCart)
    item_page = MagicMock()
    monkeypatch.setattr(shopping_flow_module, "ItemPage", item_page)

    with pytest.raises(AssertionError, match="Cart must be empty"):
        flow.add_items_to_cart(URLS)

    item_page.assert_not_called()
    tab.close.assert_called_once_with()
