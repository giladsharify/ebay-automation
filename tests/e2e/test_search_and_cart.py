import os

import allure
import pytest

from pages.base_page import BotChallengeError
from utils.data_loader import load_scenarios

pytestmark = pytest.mark.e2e

SCENARIOS_FILE = os.getenv("SCENARIOS_FILE", "search_scenarios.json")


@allure.feature("Shopping")
@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS_FILE), ids=lambda s: s.id)
def test_search_add_to_cart_and_verify_total(shopping, scenario):
    """Run the data-driven search, add-to-cart, and cart-budget scenario."""
    try:
        shopping.login()
        urls = shopping.search_items_by_name_under_price(
            scenario.query, scenario.max_price, scenario.limit
        )
        if not urls:
            pytest.skip("No items found under the price limit - nothing to add")
        shopping.add_items_to_cart(urls)
        shopping.assert_cart_total_not_exceeds(scenario.budget, len(urls))
    except BotChallengeError as exc:
        pytest.skip(f"eBay access challenge; not required to solve for this exercise: {exc}")
