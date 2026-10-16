from unittest.mock import MagicMock

import pytest

from flows import shopping_flow as shopping_flow_module
from flows.shopping_flow import ShoppingFlow


@pytest.mark.unit
def test_add_items_captures_existing_cart_subtotal(monkeypatch):
    """Verify the flow stores the existing subtotal before adding any items."""
    tab = MagicMock()
    page = MagicMock()
    page.context.new_page.return_value = tab
    flow = ShoppingFlow.__new__(ShoppingFlow)
    flow.page = page
    flow.settings = MagicMock()
    flow.log = MagicMock()
    flow._cart_subtotal_before_add = None

    class CartPageStub:
        def __init__(self, page, settings):
            """Create a minimal cart-page stub for baseline capture."""
            pass

        def open(self):
            """Stand in for navigating to the cart."""
            pass

        def read_total(self):
            """Return a fixed existing subtotal for the test."""
            return 45.5

    monkeypatch.setattr(shopping_flow_module, "CartPage", CartPageStub)

    flow.add_items_to_cart([])

    assert flow._cart_subtotal_before_add == 45.5
    tab.close.assert_called_once_with()


@pytest.mark.unit
def test_cart_budget_uses_only_this_runs_subtotal_delta():
    """Verify existing cart value is excluded from this run's budget."""
    flow = ShoppingFlow.__new__(ShoppingFlow)
    flow._cart_subtotal_before_add = 300.0
    flow.cart_page = MagicMock()
    flow.cart_page.read_total.return_value = 510.0

    flow.assert_cart_total_not_exceeds(budget_per_item=220, items_count=1)

    flow.cart_page.open.assert_called_once_with()


@pytest.mark.unit
def test_cart_budget_fails_when_this_runs_delta_exceeds_limit():
    """Verify the assertion fails when this run's subtotal increase exceeds budget."""
    flow = ShoppingFlow.__new__(ShoppingFlow)
    flow._cart_subtotal_before_add = 300.0
    flow.cart_page = MagicMock()
    flow.cart_page.read_total.return_value = 521.0

    with pytest.raises(AssertionError, match="subtotal increase 221.0 exceeds threshold 220"):
        flow.assert_cart_total_not_exceeds(budget_per_item=220, items_count=1)
