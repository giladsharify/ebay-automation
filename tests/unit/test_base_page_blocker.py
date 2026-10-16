from unittest.mock import MagicMock

import pytest

from pages.base_page import BasePage, BotChallengeError


@pytest.mark.unit
def test_access_challenge_is_reported_without_clicking_through(monkeypatch):
    """Verify access challenges are captured and raised without being bypassed."""
    page = MagicMock()
    page.url = "https://www.ebay.com/"
    body = MagicMock()
    body.inner_text.return_value = "Checking your browser before you access eBay"
    page.locator.return_value = body
    settings = type("Settings", (), {"artifacts_dir": __import__("pathlib").Path("artifacts")})()
    base = BasePage(page, settings)
    monkeypatch.setattr(base, "screenshot", MagicMock())

    with pytest.raises(BotChallengeError, match="human-verification or access-challenge"):
        base.assert_not_blocked()

    base.screenshot.assert_called_once_with("bot_challenge")
    page.locator.assert_called_once_with("body")
