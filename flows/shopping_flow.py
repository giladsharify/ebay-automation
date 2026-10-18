"""Orchestrates page objects into the four business functions required by the exercise."""
from __future__ import annotations

import random
from decimal import Decimal

import allure
from playwright.sync_api import Page

from config.settings import Settings
from pages.cart_page import CartPage, item_id_from_url
from pages.item_page import ItemPage
from pages.login_page import LoginPage
from pages.search_page import SearchPage
from utils.logger import get_logger


class ShoppingFlow:
    def __init__(self, page: Page, settings: Settings):
        """Initialize page objects and shared state for a shopping scenario."""
        self.page = page
        self.settings = settings
        self.rng = random.Random(settings.random_seed)  # reproducible "random" variants
        self.log = get_logger(self.__class__.__name__)
        self.login_page = LoginPage(page, settings)
        self.search_page = SearchPage(page, settings)
        self.cart_page = CartPage(page, settings)
        self._added_urls: list[str] = []

    def login(self) -> None:
        """Attempt login with the credentials configured for this run."""
        self.login_page.login(self.settings.username, self.settings.password)

    def search_items_by_name_under_price(self, query: str, max_price: float, limit: int = 5) -> list[str]:
        """Search by query and return up to limit item URLs within the price ceiling."""
        self.search_page.search(query, max_price)
        return self.search_page.collect_item_urls(max_price, limit)

    def _assert_cart_starts_empty(self) -> None:
        """Fail fast if the cart already has items, since the total check covers the whole cart."""
        tab = self.page.context.new_page()
        try:
            cart = CartPage(tab, self.settings)
            cart.open()
            total = cart.read_total()
        finally:
            tab.close()
        if total.amount != 0:
            raise AssertionError(
                f"Cart must be empty before the scenario, but its subtotal is {total.amount} "
                f"{total.currency}. Empty the cart (or use a fresh session) and run again."
            )

    def add_items_to_cart(self, urls: list[str]) -> None:
        """Verify the cart starts empty, then add each item in a separate tab."""
        self._assert_cart_starts_empty()
        for index, url in enumerate(urls, start=1):
            item_tab = self.page.context.new_page()
            try:
                item_page = ItemPage(item_tab, self.settings)
                item_page.open(url)
                item_page.add_to_cart(self.rng)
                item_page.screenshot(f"item_{index}_added")
                self._added_urls.append(url)
                self.log.info("Added item %d/%d: %s", index, len(urls), url)
            finally:
                item_tab.close()
                self.search_page.bring_to_front()

    @allure.step("Assert cart total <= {budget_per_item} * {items_count}")
    def assert_cart_total_not_exceeds(self, budget_per_item: float, items_count: int) -> None:
        """Assert the cart holds the added items and its total stays within the budget."""
        self.cart_page.open()
        total = self.cart_page.read_total()
        threshold = Decimal(str(budget_per_item)) * items_count
        self.cart_page.screenshot("cart_total")

        expected_currency = self.search_page.result_currency
        assert expected_currency is None or total.currency == expected_currency, (
            f"Cart total is in {total.currency} but item prices were compared in "
            f"{expected_currency}; the amounts are not comparable"
        )

        expected_ids = {item_id_from_url(url) for url in self._added_urls}
        missing = expected_ids - self.cart_page.read_item_ids()
        assert not missing, f"Items added in this run are missing from the cart: {sorted(missing)}"
        count = self.cart_page.read_items_count()
        assert count is None or count == items_count, (
            f"Cart shows {count} item(s), expected {items_count}"
        )

        self.log.info("Cart total %s %s, threshold %s", total.amount, total.currency, threshold)
        assert total.amount <= threshold, (
            f"Cart total {total.amount} {total.currency} exceeds threshold {threshold} "
            f"({budget_per_item} x {items_count})"
        )
