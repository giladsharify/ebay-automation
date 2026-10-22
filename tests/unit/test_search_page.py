from unittest.mock import MagicMock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pages.base_page import BotChallengeError
from pages.search_page import SearchPage

# arbitrary search inputs: the page/flow logic must not depend on any specific product
QUERY = "sample query"
MAX_PRICE = 220


@pytest.mark.unit
def test_search_waits_for_browser_check_after_navigation():
    """Verify search waits for browser checks before inspecting results."""
    events = []
    page = MagicMock()
    settings = MagicMock(base_url="https://example.test", default_timeout_ms=1000)
    search = SearchPage(page, settings)
    search.goto = lambda url: events.append("goto")
    search._wait_for_browser_check = lambda: events.append("browser_check")
    search.assert_not_blocked = lambda: events.append("not_blocked")
    search.screenshot = lambda name: None
    page.wait_for_selector.side_effect = lambda *args, **kwargs: events.append("results")

    search.search(QUERY, max_price=MAX_PRICE)

    assert events == ["goto", "browser_check", "not_blocked", "results"]


@pytest.mark.unit
def test_search_accepts_explicit_no_results_page():
    """Verify a clear no-results page is treated as a valid empty search."""
    page = MagicMock()
    page.wait_for_selector.side_effect = PlaywrightTimeout("no result cards")
    page.get_by_text.return_value.count.return_value = 1
    settings = MagicMock(base_url="https://example.test", default_timeout_ms=1000)
    search = SearchPage(page, settings)
    search.goto = lambda url: None
    search._wait_for_browser_check = lambda: None
    search.assert_not_blocked = lambda: None
    search.screenshot = lambda name: None

    search.search(QUERY, max_price=MAX_PRICE)

    page.get_by_text.assert_called_with("No exact matches found", exact=False)


@pytest.mark.unit
def test_search_propagates_access_challenge_without_retrying_homepage():
    """Verify search propagates access challenges without attempting a bypass."""
    page = MagicMock()
    settings = MagicMock(base_url="https://example.test", default_timeout_ms=1000)
    search = SearchPage(page, settings)
    search.goto = lambda url: None
    search._wait_for_browser_check = lambda: None
    search.assert_not_blocked = MagicMock(
        side_effect=BotChallengeError("access challenge")
    )

    with pytest.raises(BotChallengeError, match="access challenge"):
        search.search(QUERY, max_price=MAX_PRICE)
