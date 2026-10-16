"""Cart page: read the displayed subtotal."""
from __future__ import annotations

import allure
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pages.base_page import BasePage
from utils.price_parser import parse_price


class CartPage(BasePage):
    SUBTOTAL_KEYWORD = "subtotal"
    EMPTY_CART_PHRASES = (
        "your cart is empty",
        "your shopping cart is empty",
        "don't have any items in your cart",
    )

    @allure.step("Open cart")
    def open(self) -> None:
        """Navigate to the configured shopping cart."""
        self.goto(self.settings.cart_url)
        self.page.wait_for_load_state("load")

    def read_total(self) -> float:
        """Read the displayed subtotal, returning zero only for an explicitly empty cart."""
        self.assert_not_blocked() # To check
        # Screenshot first, so a failure still leaves evidence of what the cart looked like
        self.screenshot("cart_page")
        try:
            self.page.get_by_text(self.SUBTOTAL_KEYWORD, exact=False).first.wait_for(
                state="visible"
            )
        except PlaywrightTimeout:
            body_text = self.page.locator("body").inner_text().lower()
            if any(phrase in body_text for phrase in self.EMPTY_CART_PHRASES):
                return 0.0
            raise AssertionError("Cart page showed neither a subtotal nor an empty-cart message")

        lines = [ln.strip() for ln in self.page.locator("body").inner_text().splitlines() if ln.strip()]
        for i, line in enumerate(lines):
            if self.SUBTOTAL_KEYWORD in line.lower():
                # the price is on the same line or one of the next two lines
                for candidate in lines[i : i + 3]:
                    price = parse_price(candidate) if any(c.isdigit() for c in candidate) else None
                    if price is not None and ("$" in candidate or "ILS" in candidate):
                        return price
        raise AssertionError("Could not find a subtotal price in the cart page")