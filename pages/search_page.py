"""Search results page: search, price filter, card parsing and paging."""
from __future__ import annotations

from urllib.parse import quote_plus
from playwright.sync_api import TimeoutError as PlaywrightTimeout

import allure

from pages.base_page import BasePage, BotChallengeError
from utils.price_parser import parse_price


class SearchPage(BasePage):
    NO_RESULTS_TEXT = "No exact matches found"
    CARDS_XPATH = "//ul[contains(@class,'srp-results')]/li[contains(@class,'s-item') or contains(@class,'s-card')]"
    CARD_PRICE_XPATH = ".//*[contains(@class,'s-item__price') or contains(@class,'s-card__price')]"
    CARD_LINK_XPATH = ".//a[contains(@href,'/itm/')]"
    NEXT_PAGE_XPATH = "//a[contains(@class,'pagination__next')]"

    def _has_no_results(self) -> bool:
        """Return whether the results page explicitly reports no exact matches."""
        return self.page.get_by_text(self.NO_RESULTS_TEXT, exact=False).count() > 0

    @allure.step("Search for '{query}' (max price {max_price})")
    def search(self, query: str, max_price: float | None = None) -> None:
        """Open search results with an optional maximum-price filter and wait for content."""
        url = f"{self.settings.base_url}/sch/i.html?_nkw={quote_plus(query)}"
        if max_price is not None:
            url += f"&_udhi={max_price}"

        self.goto(url)
        self._wait_for_browser_check()
        try:
            self.assert_not_blocked()
        except BotChallengeError:
            raise

        try:
            self.page.wait_for_selector(
                f"xpath={self.CARDS_XPATH}", timeout=self.settings.default_timeout_ms
            )
        except PlaywrightTimeout:
            if self._has_no_results():
                self.log.info("Search returned no matching items.")
                return
            self.screenshot("search_no_results")
            raise AssertionError(
                "Search results did not load - see artifacts/screenshots/search_no_results.png"
            )

    def collect_item_urls(self, max_price: float, limit: int) -> list[str]:
        """Collect up to `limit` unique item URLs priced <= max_price, following paging."""
        urls: list[str] = []
        seen: set[str] = set()
        while len(urls) < limit:
            cards = self.page.locator(f"xpath={self.CARDS_XPATH}")
            for i in range(cards.count()):
                card = cards.nth(i)
                price_loc = card.locator(f"xpath={self.CARD_PRICE_XPATH}")
                link_loc = card.locator(f"xpath={self.CARD_LINK_XPATH}")
                if price_loc.count() == 0 or link_loc.count() == 0:
                    continue
                price = parse_price(price_loc.first.text_content())
                if price is None or price > max_price:
                    continue
                href = (link_loc.first.get_attribute("href") or "").split("?")[0]
                if not href or href in seen:
                    continue
                seen.add(href)
                urls.append(href)
                if len(urls) >= limit:
                    break
            if len(urls) >= limit or not self._go_next_page():
                break
        self.log.info("Collected %d item(s)", len(urls))
        return urls

    def _go_next_page(self) -> bool:
        """Navigate to the next results page when an enabled next link exists."""
        nxt = self.page.locator(f"xpath={self.NEXT_PAGE_XPATH}")
        if nxt.count() == 0 or nxt.first.get_attribute("aria-disabled") == "true":
            return False
        nxt.first.click()
        self.page.wait_for_selector(f"xpath={self.CARDS_XPATH}")
        return True
