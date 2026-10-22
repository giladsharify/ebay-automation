"""Cart page: read the displayed subtotal and the items in the cart."""
from __future__ import annotations

import re
from decimal import Decimal

import allure
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pages.base_page import BasePage
from utils.price_parser import Money, parse_money


def item_id_from_url(url: str) -> str | None:
    """Extract the numeric eBay item id from an /itm/ URL."""
    match = CartPage.ITEM_ID_PATTERN.search(url)
    return match.group(1) if match else None


class CartPage(BasePage):
    SUBTOTAL_KEYWORD = "subtotal"
    # CSS: class + descendant + substring attribute match in one short selector. Scoped to
    # cart line titles only, so the "recommended items" strip is not counted. The same
    # string also runs inside evaluate_all, where a CSS selector is the natural fit.
    ITEM_LINKS = ".item-title a[href*='/itm/']"
    ITEM_ID_PATTERN = re.compile(r"/itm/(?:[^/?#]+/)?(\d+)")
    ITEMS_COUNT_PATTERN = re.compile(r"^items\s*\((\d+)\)", re.IGNORECASE)
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

    def _lines(self) -> list[str]:
        """Return the non-empty visible text lines of the page."""
        # CSS "body": the whole visible text is needed; a tag selector is the simplest form
        return [ln.strip() for ln in self.page.locator("body").inner_text().splitlines() if ln.strip()]

    def read_total(self) -> Money:
        """Read the displayed subtotal, returning zero only for an explicitly empty cart."""
        self.assert_not_blocked()
        # Screenshot first, so a failure still leaves evidence of what the cart looked like
        self.screenshot("cart_page")
        try:
            self.page.get_by_text(self.SUBTOTAL_KEYWORD, exact=False).first.wait_for(
                state="visible"
            )
        except PlaywrightTimeout:
            body_text = self.page.locator("body").inner_text().lower()  # CSS tag: whole page text
            if any(phrase in body_text for phrase in self.EMPTY_CART_PHRASES):
                return Money(Decimal("0"), None)
            raise AssertionError("Cart page showed neither a subtotal nor an empty-cart message")

        lines = self._lines()
        for i, line in enumerate(lines):
            if self.SUBTOTAL_KEYWORD in line.lower():
                # the price is on the same line or one of the next two lines
                for candidate in lines[i : i + 3]:
                    money = parse_money(candidate)
                    if money is not None and money.currency is not None:
                        return money
        raise AssertionError("Could not find a subtotal price in the cart page")

    def read_item_ids(self) -> set[str]:
        """Return the eBay item ids of all items linked in the cart."""
        hrefs = self.page.locator(self.ITEM_LINKS).evaluate_all("els => els.map(e => e.href)")
        return {item_id for item_id in map(item_id_from_url, hrefs) if item_id}

    def read_items_count(self) -> int | None:
        """Return N from the order summary's "Items (N)" line, or None if absent."""
        for line in self._lines():
            match = self.ITEMS_COUNT_PATTERN.match(line)
            if match:
                return int(match.group(1))
        return None
