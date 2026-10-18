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
    "/p1": _results_page(
        [("1", "$10.00"), ("2", "$500.00"), ("3", "ILS 99.90"), ("1", "$10.00")], "/p2"
    ),
    "/p2": _results_page([("4", "$20.00 to $300.00"), ("5", "$150.00"), ("6", "$5.00")], "/p3"),
    "/p3": _results_page([("7", "$1.00")], None),
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


def _search_page(page) -> SearchPage:
    """Open page 1 and wrap it in the real SearchPage object."""
    page.goto(f"{BASE}/p1")
    return SearchPage(page, MagicMock())


def test_collects_across_pages_until_limit(browser_page):
    """Skips expensive and duplicate cards, strips query strings, and follows Next."""
    urls = _search_page(browser_page).collect_item_urls(max_price=200, limit=5)

    assert urls == [f"{BASE}/itm/{i}" for i in ("1", "3", "4", "5", "6")]
    assert browser_page.url.endswith("/p2")


def test_returns_partial_result_when_pages_run_out(browser_page):
    """Returns what was found when the last page has no Next link."""
    urls = _search_page(browser_page).collect_item_urls(max_price=200, limit=10)

    assert len(urls) == 6
    assert browser_page.url.endswith("/p3")


def test_returns_empty_list_when_nothing_matches(browser_page):
    """Zero matching items is a valid result."""
    assert _search_page(browser_page).collect_item_urls(max_price=0.5, limit=5) == []
