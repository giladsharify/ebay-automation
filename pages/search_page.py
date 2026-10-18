"""Search results page: search, price filter, card parsing and paging."""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeout

import allure

from pages.base_page import BasePage
from utils.price_parser import Money, parse_money


class SearchPage(BasePage):
    NO_RESULTS_TEXT = "No exact matches found"
    CARDS_XPATH = "//ul[contains(@class,'srp-results')]/li[contains(@class,'s-item') or contains(@class,'s-card')]"
    CARD_PRICE_XPATH = ".//*[contains(@class,'s-item__price') or contains(@class,'s-card__price')]"
    CARD_LINK_XPATH = ".//a[contains(@href,'/itm/')]"
    NEXT_PAGE_XPATH = "//a[contains(@class,'pagination__next')]"

    result_currency: str | None = None

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
        self.assert_not_blocked()

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

    def _read_cards(self) -> list[tuple[str, Money]]:
        """Return (item URL without query string, price) for every priced card on this page."""
        cards = self.page.locator(f"xpath={self.CARDS_XPATH}")
        result = []
        for i in range(cards.count()):
            card = cards.nth(i)
            price_loc = card.locator(f"xpath={self.CARD_PRICE_XPATH}")
            link_loc = card.locator(f"xpath={self.CARD_LINK_XPATH}")
            if price_loc.count() == 0 or link_loc.count() == 0:
                continue
            money = parse_money(price_loc.first.text_content())
            href = (link_loc.first.get_attribute("href") or "").split("?")[0]
            if money is not None and href:
                result.append((href, money))
        return result

    def _pick_currency(self, cards: list[tuple[str, Money]]) -> str | None:
        """Use the configured currency, else the one most cards on the page are shown in."""
        if self.settings.currency:
            return self.settings.currency
        counts = Counter(money.currency for _, money in cards if money.currency)
        return counts.most_common(1)[0][0] if counts else None

    def collect_item_urls(self, max_price: float, limit: int) -> list[str]:
        """Collect up to `limit` unique item URLs priced <= max_price, following paging.

        Only cards in a single currency are compared with max_price; the currency used
        is kept in `result_currency` so the cart can be checked in the same currency.
        """
        urls: list[str] = []
        seen: set[str] = set()
        visited_pages: set[str] = set()
        ceiling = Decimal(str(max_price))
        self.result_currency = None
        while len(urls) < limit:
            visited_pages.add(self.page.url)
            cards = self._read_cards()
            if self.result_currency is None:
                self.result_currency = self._pick_currency(cards)
                self.log.info("Comparing prices in currency: %s", self.result_currency)
            for href, money in cards:
                if money.currency != self.result_currency:
                    self.log.info("Skipping %s: price in %s, not %s", href, money.currency, self.result_currency)
                    continue
                if money.amount > ceiling or href in seen:
                    continue
                seen.add(href)
                urls.append(href)
                if len(urls) >= limit:
                    break
            if len(urls) >= limit or not self._go_next_page(visited_pages):
                break
        self.log.info("Collected %d item(s)", len(urls))
        return urls

    def _first_card_href(self) -> str | None:
        """Return the link of the first result card, used to detect that results changed."""
        links = self.page.locator(f"xpath=({self.CARDS_XPATH}{self.CARD_LINK_XPATH[1:]})[1]")
        return links.first.get_attribute("href") if links.count() else None

    def _go_next_page(self, visited_pages: set[str]) -> bool:
        """Go to the next results page; False when there is none or it would revisit a page."""
        nxt = self.page.locator(f"xpath={self.NEXT_PAGE_XPATH}")
        if nxt.count() == 0 or nxt.first.get_attribute("aria-disabled") == "true":
            return False
        href = nxt.first.get_attribute("href")
        if href and urljoin(self.page.url, href) in visited_pages:
            self.log.warning("Next link points to an already visited page; stopping paging.")
            return False
        previous_url, previous_first = self.page.url, self._first_card_href()
        nxt.first.click()
        # cards from the old page still match the locator, so wait for the URL to change first
        try:
            self.page.wait_for_url(lambda url: url != previous_url)
        except PlaywrightTimeout:
            if self._first_card_href() == previous_first:
                self.log.warning("Clicking Next changed neither the URL nor the results; stopping paging.")
                return False
        if self.page.url != previous_url and self.page.url in visited_pages:
            self.log.warning("Next led back to an already visited page; stopping paging.")
            return False
        self.page.wait_for_selector(f"xpath={self.CARDS_XPATH}")
        self.log.info("Moved to next results page: %s", self.page.url)
        return True
