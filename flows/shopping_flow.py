"""Orchestrates page objects into the four business functions required by the exercise."""
from __future__ import annotations

import random

import allure
from playwright.sync_api import Page

from config.settings import Settings
from pages.cart_page import CartPage
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
        self._cart_subtotal_before_add: float | None = None

    def login(self) -> None:
        """Attempt login with the credentials configured for this run."""
        self.login_page.login(self.settings.username, self.settings.password)

    def search_items_by_name_under_price(self, query: str, max_price: float, limit: int = 5) -> list[str]:
        """Search by query and return up to limit item URLs within the price ceiling."""
        self.search_page.search(query, max_price)
        return self.search_page.collect_item_urls(max_price, limit)

    def add_items_to_cart(self, urls: list[str]) -> None:
        """Capture the starting cart subtotal, then add each item in a separate tab."""
        baseline_tab = self.page.context.new_page()
        try:
            baseline_cart = CartPage(baseline_tab, self.settings)
            baseline_cart.open()
            self._cart_subtotal_before_add = baseline_cart.read_total()
            self.log.info(
                "Cart subtotal before this run's additions: %.2f",
                self._cart_subtotal_before_add,
            )
        finally:
            baseline_tab.close()

        for index, url in enumerate(urls, start=1):
            item_tab = self.page.context.new_page()
            try:
                item_page = ItemPage(item_tab, self.settings)
                item_page.open(url)
                item_page.add_to_cart(self.rng)
                item_page.screenshot(f"item_{index}_added")
                self.log.info("Added item %d/%d: %s", index, len(urls), url)
            finally:
                item_tab.close()
                self.search_page.bring_to_front()

    @allure.step("Assert cart total <= {budget_per_item} * {items_count}")
    def assert_cart_total_not_exceeds(self, budget_per_item: float, items_count: int) -> None:
        """Assert this run's cart subtotal increase stays within the computed budget."""
        if self._cart_subtotal_before_add is None:
            raise AssertionError(
                "Cart baseline was not captured; call add_items_to_cart before asserting the total."
            )
        self.cart_page.open()
        total = self.cart_page.read_total()
        run_subtotal = total - self._cart_subtotal_before_add
        threshold = budget_per_item * items_count
        self.cart_page.screenshot("cart_total")
        assert run_subtotal >= 0, (
            f"Cart subtotal decreased from {self._cart_subtotal_before_add} to {total}; "
            "cannot isolate this run's additions"
        )
        assert run_subtotal <= threshold, (
            f"This run's cart subtotal increase {run_subtotal} exceeds threshold {threshold} "
            f"(before={self._cart_subtotal_before_add}, after={total})"
        )
