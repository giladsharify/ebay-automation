"""eBay home page: recover once from the generic error page, then search via the UI."""
from __future__ import annotations

import allure
from playwright.sync_api import Locator, TimeoutError as PlaywrightTimeout

from pages.base_page import BasePage


class HomePage(BasePage):
    SHIPPING_PROMPT = "Are you shipping to"

    @property
    def search_input(self) -> Locator:
        """Return the homepage search input locator."""
        return self.page.get_by_placeholder("Search for anything")

    @property
    def search_button(self) -> Locator:
        """Return the homepage search button locator."""
        return self.page.get_by_role("button", name="Search", exact=True)

    def _confirm_shipping_destination_if_present(self) -> None:
        """Confirm the shipping destination prompt when it appears."""
        prompt = self.page.get_by_text(self.SHIPPING_PROMPT, exact=False)
        try:
            prompt.wait_for(state="visible", timeout=5000)
        except PlaywrightTimeout:
            return

        self.page.get_by_role("button", name="Confirm", exact=True).click()
        self.log.info("Confirmed the shipping destination prompt.")

    @allure.step("Open home page")
    def open(self) -> None:
        """Open eBay, handle optional interstitials, and wait for the search input."""
        self.goto(self.settings.base_url)
        self._wait_for_browser_check()
        self.assert_not_blocked()
        self._confirm_shipping_destination_if_present()
        self.search_input.wait_for(state="visible")

    @allure.step("Search for '{query}' from the home page")
    def search(self, query: str) -> None:
        """Submit a product query through the homepage search form."""
        self.search_input.fill(query)
        self.search_button.click()
        self.page.wait_for_load_state("domcontentloaded")