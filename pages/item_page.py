"""Single item page: pick random available variants and add to cart."""
from __future__ import annotations

import random
import re

import allure
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pages.base_page import BasePage


class ItemPage(BasePage):
    NATIVE_SELECTS = "select[id^='msku-sel'], select.x-msku__select-box"
    LISTBOX_BUTTONS = "button[aria-haspopup='listbox']"
    LISTBOX_OPTIONS = "[role='option']:visible"
    ADD_TO_CART_BUTTON = (
        "xpath=//span[normalize-space()='Add to cart']"
        "/ancestor::*[self::a or self::button][1]"
    )
    CART_COUNT_SELECTOR = "a.gh-flyout__target[href*='cart']"
    VARIANT_PANEL = ".x-msku-evo"
    ADDED_CONFIRMATION = re.compile(r"added to (your )?cart", re.IGNORECASE)
    SELECT_ERROR = re.compile(r"please (select|choose)", re.IGNORECASE)
    CART_COUNT_PATTERN = re.compile(r"contains\s+(\d+)\s+items?\b", re.IGNORECASE)

    PLACEHOLDER_VALUES = {"", "-1"}
    UNAVAILABLE_WORDS = ("out of stock", "sold out", "unavailable")

    @allure.step("Open item {url}")
    def open(self, url: str) -> None:
        """Open an item listing and check for access challenges."""
        self.goto(url)
        self.assert_not_blocked()

    # ------------------------------------------------------------------ variants
    def _select_native_dropdowns(self, rng: random.Random) -> int:
        """Choose a random available value from each visible native variant dropdown."""
        selects = self.page.locator(self.NATIVE_SELECTS)
        chosen = 0
        for i in range(selects.count()):
            select = selects.nth(i)
            if not select.is_visible():
                continue
            values = select.locator("option:not([disabled])").evaluate_all(
                "els => els.map(e => e.value)"
            )
            available = [v for v in values if v not in self.PLACEHOLDER_VALUES]
            if available:
                select.select_option(rng.choice(available))
                chosen += 1
        return chosen

    def _select_custom_listboxes(self, rng: random.Random) -> int:
        """Choose a random available value from each visible custom variant listbox."""
        buttons = self.page.locator(self.LISTBOX_BUTTONS)
        chosen = 0
        for i in range(buttons.count()):
            button = buttons.nth(i)
            if not button.is_visible():
                continue
            button.click()
            options = self.page.locator(self.LISTBOX_OPTIONS)
            try:
                options.first.wait_for(state="visible", timeout=3000)
            except PlaywrightTimeout:
                continue
            valid = []
            for option in options.all():
                text = option.inner_text().strip().lower()
                disabled = option.get_attribute("aria-disabled") == "true"
                is_placeholder = text.startswith("select") or text.startswith("- select")
                unavailable = any(w in text for w in self.UNAVAILABLE_WORDS)
                if text and not disabled and not is_placeholder and not unavailable:
                    valid.append(option)
            if valid:
                pick = rng.choice(valid)
                self.log.info("Variant chosen: %s", pick.inner_text().strip())
                pick.click()
                chosen += 1
            else:
                self.page.keyboard.press("Escape")
        return chosen

    @allure.step("Select random variants")
    def select_random_variants(self, rng: random.Random) -> int:
        """Select available variants and return the number of groups selected."""
        total = self._select_native_dropdowns(rng) + self._select_custom_listboxes(rng)
        self.log.info("Variant groups selected: %d", total)
        return total

    # ---------------------------------------------------------------- add to cart
    def _dump_buybox(self, name: str) -> None:
        """Save the HTML around the Add-to-cart button, to help fix locators."""
        try:
            html = (
                self.page.locator(self.ADD_TO_CART_BUTTON)
                .first.locator("xpath=ancestor::*[8]")
                .evaluate("e => e.outerHTML")
            )
            path = self.settings.artifacts_dir / "debug" / f"{name}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html[:80000], encoding="utf-8")
            self.log.info("Buy-box HTML saved: %s", path)
        except Exception as exc:  # debug helper must never hide the real failure
            self.log.warning("Could not dump buy box: %s", exc)

    def _read_cart_count(self) -> int | None:
        """Parse the current item count from the cart link's accessible label."""
        cart_link = self.page.locator(self.CART_COUNT_SELECTOR)
        if cart_link.count() == 0:
            return None
        label = cart_link.first.get_attribute("aria-label") or ""
        match = self.CART_COUNT_PATTERN.search(label)
        return int(match.group(1)) if match else None

    def _wait_for_cart_count_increase(self, previous_count: int | None) -> bool:
        """Wait briefly for the cart badge count to exceed its previous value."""
        if previous_count is None:
            return False
        try:
            self.page.wait_for_function(
                """(previousCount) => {
                    const cartLink = document.querySelector("a.gh-flyout__target[href*='cart']");
                    const label = cartLink?.getAttribute("aria-label") || "";
                    const match = label.match(/contains\\s+(\\d+)\\s+items?/i);
                    return match !== null && Number(match[1]) > previousCount;
                }""",
                arg=previous_count,
                timeout=5000,
            )
            return True
        except PlaywrightTimeout:
            return False

    def _has_visible_variant_error(self) -> bool:
        """Return whether a variant-selection validation message is visible in its panel."""
        panel = self.page.locator(self.VARIANT_PANEL)
        if panel.count() == 0:
            return False
        errors = panel.get_by_text(self.SELECT_ERROR)
        return any(errors.nth(index).is_visible() for index in range(errors.count()))

    @allure.step("Add item to cart")
    def add_to_cart(self, rng: random.Random) -> None:
        """Add this item and verify success by confirmation text or cart-count increase."""
        item_id = self.page.url.split("?")[0].rstrip("/").split("/")[-1]
        previous_cart_count = self._read_cart_count()
        self.select_random_variants(rng)
        self.page.locator(self.ADD_TO_CART_BUTTON).first.click()
        self.assert_not_blocked()

        try:
            self.page.get_by_text(self.ADDED_CONFIRMATION).first.wait_for(
                state="visible", timeout=3000
            )
            self.log.info("Add-to-cart confirmation appeared for item %s.", item_id)
            return
        except PlaywrightTimeout:
            if self._wait_for_cart_count_increase(previous_cart_count):
                self.log.info("Cart count increased after adding item %s.", item_id)
                return

            self.screenshot(f"add_to_cart_not_confirmed_{item_id}")
            self._dump_buybox(f"buybox_{item_id}")
            needs_variant = self._has_visible_variant_error()
            reason = (
                "a visible variant validation message appeared"
                if needs_variant
                else "no confirmation appeared and the cart count did not increase"
            )
            raise AssertionError(f"Add to cart failed: {reason}. See artifacts/screenshots and artifacts/debug")