"""Offline browser tests: real XPath locators and paging against local HTML (no eBay)."""
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import sync_playwright

from pages.search_page import SearchPage

pytestmark = pytest.mark.component

BASE = "https://fake-ebay.test"


def _results_page(cards: list[tuple[str, str]], next_href: str | None) -> str:
    """Render a minimal search-results page with eBay-like markup."""
    items = "".join(
        f'<li class="s-item"><a href="{BASE}/itm/{item_id}?hash=x">item {item_id}</a>'
        f'<span class="s-item__price">{price}</span></li>'
        for item_id, price in cards
    )
    nav = f'<a class="pagination__next" href="{next_href}">Next</a>' if next_href else ""
    return f'<html><body><ul class="srp-results">{items}</ul>{nav}</body></html>'


PAGES = {
    # page 1 is mostly ILS; the "$" card is in another currency and must be skipped
    "/p1": _results_page(
        [("1", "ILS 10.00"), ("2", "ILS 500.00"), ("3", "$5.00"), ("1", "ILS 10.00"), ("8", "ILS 30.00")],
        "/p2",
    ),
    "/p2": _results_page([("4", "ILS 20.00 to ILS 300.00"), ("5", "ILS 150.00"), ("6", "ILS 5.00")], "/p3"),
    "/p3": _results_page([("7", "ILS 1.00")], None),
    # a broken pager whose Next link points back to the first page
    "/loop1": _results_page([("9", "ILS 1.00")], "/loop2"),
    "/loop2": _results_page([("10", "ILS 1.00")], "/loop1"),
}


@pytest.fixture(scope="module")
def browser_page():
    """Serve the fake results pages from a headless browser without network access."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(5000)
        page.route(
            f"{BASE}/**",
            lambda route: route.fulfill(
                content_type="text/html", body=PAGES[route.request.url.removeprefix(BASE)]
            ),
        )
        yield page
        browser.close()


def _search_page(page, start: str = "/p1", currency: str | None = None) -> SearchPage:
    """Open a start page and wrap it in the real SearchPage object."""
    page.goto(f"{BASE}{start}")
    return SearchPage(page, MagicMock(currency=currency))


def test_collects_across_pages_until_limit(browser_page):
    """Skips expensive, duplicate and other-currency cards, strips query strings, follows Next."""
    search = _search_page(browser_page)

    urls = search.collect_item_urls(max_price=200, limit=5)

    assert urls == [f"{BASE}/itm/{i}" for i in ("1", "8", "4", "5", "6")]
    assert search.result_currency == "ILS"
    assert browser_page.url.endswith("/p2")


def test_configured_currency_overrides_page_majority(browser_page):
    """Uses the configured currency when one is set."""
    search = _search_page(browser_page, currency="USD")

    assert search.collect_item_urls(max_price=200, limit=5) == [f"{BASE}/itm/3"]
    assert search.result_currency == "USD"


def test_returns_partial_result_when_pages_run_out(browser_page):
    """Returns what was found when the last page has no Next link."""
    urls = _search_page(browser_page).collect_item_urls(max_price=200, limit=10)

    assert len(urls) == 6
    assert browser_page.url.endswith("/p3")


def test_returns_empty_list_when_nothing_matches(browser_page):
    """Zero matching items is a valid result."""
    assert _search_page(browser_page).collect_item_urls(max_price=0.5, limit=5) == []


def test_stops_when_next_leads_back_to_a_visited_page(browser_page):
    """A pager that loops does not cause an endless loop."""
    urls = _search_page(browser_page, start="/loop1").collect_item_urls(max_price=200, limit=5)

    assert urls == [f"{BASE}/itm/9", f"{BASE}/itm/10"]
