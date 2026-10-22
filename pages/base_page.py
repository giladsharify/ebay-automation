"""Common behaviour shared by all page objects (SRP: generic browser helpers only)."""
from __future__ import annotations

import re
from pathlib import Path

import allure
from playwright.sync_api import Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeout

from config.settings import Settings
from utils.logger import get_logger

class BotChallengeError(AssertionError):
    """Raised when the site shows a human-verification page instead of the expected content."""

class BasePage:
    def __init__(self, page: Page, settings: Settings):
        """Initialize shared browser helpers with a Playwright page and settings."""
        self.page = page
        self.settings = settings
        self.log = get_logger(self.__class__.__name__)

    def goto(self, url: str) -> None:
        """Navigate to a URL and report interrupted access-challenge navigation."""
        self.log.info("Navigating to %s", url)
        try:
            self.page.goto(url, wait_until="domcontentloaded")
        except PlaywrightError as exc:
            if "ERR_ABORTED" in str(exc):
                if self._is_access_blocked():
                    self.screenshot("bot_challenge")
                    self.log.warning("Navigation was aborted on an eBay access-challenge page.")
                    raise BotChallengeError(
                        "eBay presented an access challenge; see artifacts/screenshots/bot_challenge.png"
                    ) from exc
                self.screenshot("navigation_aborted")
            raise

    def bring_to_front(self) -> None:
        """Bring this page to the foreground of its browser context."""
        self.page.bring_to_front()

    def screenshot(self, name: str) -> Path:
        """Save a full-page screenshot under artifacts/screenshots and attach it to Allure."""
        safe = re.sub(r"[^\w\-]+", "_", name)
        path = self.settings.artifacts_dir / "screenshots" / f"{safe}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path), full_page=True)
        allure.attach.file(str(path), name=safe, attachment_type=allure.attachment_type.PNG)
        self.log.info("Screenshot saved: %s", path)
        return path

    BLOCK_PHRASES = (
        "verify yourself",
        "pardon our interruption",
        "checking your browser",
        "robot or human",
    )

    BROWSER_CHECK_TEXT = "Checking your browser before you access eBay"

    def _wait_for_browser_check(self) -> None:
        """Wait up to 30 seconds for a detected browser-check message to disappear."""
        browser_check = self.page.get_by_text(self.BROWSER_CHECK_TEXT, exact=False)
        try:
            browser_check.wait_for(state="visible", timeout=1000)
        except PlaywrightTimeout:
            return

        try:
            browser_check.wait_for(state="hidden", timeout=30000)
            self.log.info("Browser check completed; continuing.")
        except PlaywrightTimeout:
            self.log.warning("Browser check message remained visible after 30 seconds.")

    def _is_access_blocked(self) -> bool:
        """Return whether the current page appears to be an eBay access challenge."""
        url = self.page.url.lower()
        body = self.page.locator("body").inner_text().lower()  # CSS tag: whole page text
        has_challenge_text = any(phrase in body for phrase in self.BLOCK_PHRASES)
        has_challenge_url = any(key in url for key in ("captcha", "challenge", "splashui"))
        if has_challenge_text or has_challenge_url:
            return True
        has_homepage_challenge = self.page.locator(
            # CSS: Playwright's :has-text() matches the label on either a link or a button in
            # one selector; the XPath equivalent needs normalize-space() on two node types.
            "a:has-text('Go to homepage'), button:has-text('Go to homepage')"
        ).count() > 0
        return has_homepage_challenge

    def assert_not_blocked(self) -> None:
        """Capture evidence and raise when eBay displays an access challenge."""
        if self._is_access_blocked():
            self.screenshot("bot_challenge")
            self.log.warning("eBay access challenge detected; not attempting to bypass it.")
            raise BotChallengeError(
                "eBay showed a human-verification or access-challenge page. "
                "See artifacts/screenshots/bot_challenge.png"
            )
