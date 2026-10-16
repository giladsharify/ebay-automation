from unittest.mock import MagicMock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pages.home_page import HomePage


@pytest.mark.unit
def test_confirms_shipping_destination_when_prompt_is_visible():
    """Verify the shipping destination prompt is confirmed when present."""
    page = MagicMock()
    prompt = MagicMock()
    confirm = MagicMock()
    page.get_by_text.return_value = prompt
    page.get_by_role.return_value = confirm
    home = HomePage(page, MagicMock())

    home._confirm_shipping_destination_if_present()

    prompt.wait_for.assert_called_once_with(state="visible", timeout=5000)
    confirm.click.assert_called_once_with()


@pytest.mark.unit
def test_continues_when_shipping_destination_prompt_is_absent():
    """Verify homepage setup continues when no shipping prompt appears."""
    page = MagicMock()
    prompt = MagicMock()
    prompt.wait_for.side_effect = PlaywrightTimeout("prompt not visible")
    page.get_by_text.return_value = prompt
    home = HomePage(page, MagicMock())

    home._confirm_shipping_destination_if_present()

    page.get_by_role.assert_not_called()


@pytest.mark.unit
def test_waits_for_browser_check_to_disappear():
    """Verify a detected browser-check message gets the full 30-second wait."""
    page = MagicMock()
    browser_check = MagicMock()
    page.get_by_text.return_value = browser_check
    home = HomePage(page, MagicMock())

    home._wait_for_browser_check()

    assert browser_check.wait_for.call_args_list[0].kwargs == {
        "state": "visible",
        "timeout": 1000,
    }
    assert browser_check.wait_for.call_args_list[1].kwargs == {
        "state": "hidden",
        "timeout": 30000,
    }


@pytest.mark.unit
def test_does_not_wait_thirty_seconds_when_browser_check_is_absent():
    """Verify the long browser-check wait is skipped when the message is absent."""
    page = MagicMock()
    browser_check = MagicMock()
    browser_check.wait_for.side_effect = PlaywrightTimeout("not visible")
    page.get_by_text.return_value = browser_check
    home = HomePage(page, MagicMock())

    home._wait_for_browser_check()

    browser_check.wait_for.assert_called_once_with(state="visible", timeout=1000)


@pytest.mark.unit
def test_home_page_waits_for_browser_check_before_search():
    """Verify homepage setup resolves interstitials before waiting for search."""
    events = []
    page = MagicMock()
    page.get_by_placeholder.return_value.wait_for.side_effect = (
        lambda **kwargs: events.append("search")
    )
    home = HomePage(page, MagicMock(base_url="https://example.test"))
    home.goto = lambda url: events.append("goto")
    home.screenshot = lambda name: None
    home._wait_for_browser_check = lambda: events.append("browser_check")
    home.assert_not_blocked = lambda: events.append("not_blocked")
    home._confirm_shipping_destination_if_present = lambda: events.append("shipping")

    home.open()

    assert events == ["goto", "browser_check", "not_blocked", "shipping", "search"]