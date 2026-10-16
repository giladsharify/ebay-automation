"""Authentication. Falls back to guest mode if the site blocks automated login."""
from __future__ import annotations

import allure
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pages.base_page import BasePage


class LoginPage(BasePage):
    USERNAME_INPUT = "#userid"
    CONTINUE_BUTTON = "#signin-continue-btn"
    PASSWORD_INPUT = "#pass"
    SIGN_IN_BUTTON = "#sgnBt"
    STEP_TIMEOUT_MS = 8000

    @allure.step("Login")
    def login(self, username: str | None, password: str | None) -> bool:
        """Return True if logged in, False if continuing as guest."""
        if not username or not password:
            self.log.info("No credentials supplied - continuing as guest")
            return False

        self.goto(f"{self.settings.base_url}/signin")
        try:
            self.page.locator(self.USERNAME_INPUT).fill(username, timeout=self.STEP_TIMEOUT_MS)
            self.page.locator(self.CONTINUE_BUTTON).click(timeout=self.STEP_TIMEOUT_MS)
            self.page.locator(self.PASSWORD_INPUT).wait_for(state="visible", timeout=self.STEP_TIMEOUT_MS)
            self.page.locator(self.PASSWORD_INPUT).fill(password)
            self.page.locator(self.SIGN_IN_BUTTON).click()
            self.page.wait_for_url(lambda url: "signin" not in url, timeout=self.STEP_TIMEOUT_MS)
            return True
        except PlaywrightTimeout:
            self.log.warning("Login blocked (CAPTCHA / bot detection?) - continuing as guest")
            self.screenshot("login_blocked")
            return False