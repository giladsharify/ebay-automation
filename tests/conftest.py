"""Fixtures: settings, browser, per-test context (always traced) and page."""
from __future__ import annotations

import re

import allure
import pytest
from playwright.sync_api import sync_playwright

from config.settings import load_settings
from flows.shopping_flow import ShoppingFlow


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store each pytest phase report on its test item for fixture teardown."""
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())


def _safe(name: str) -> str:
    """Convert a test name into a filesystem-safe artifact name."""
    return re.sub(r"[^\w\-]+", "_", name)


@pytest.fixture(scope="session")
def settings():
    """Provide the application settings for the test session."""
    return load_settings()


@pytest.fixture(scope="session")
def browser(settings):
    """Launch and share the configured Playwright browser for the test session."""
    with sync_playwright() as pw:
        browser = getattr(pw, settings.browser).launch(
            headless=settings.headless, slow_mo=settings.slow_mo_ms
        )
        yield browser
        browser.close()


@pytest.fixture
def context(browser, settings, request):
    """Create a traced browser context and attach its trace after the test."""
    state = settings.artifacts_dir / "auth" / "state.json"
    ctx = browser.new_context(
        locale=settings.locale,
        viewport={"width": 1440, "height": 900},
        storage_state=str(state) if state.exists() else None,
    )
    ctx.set_default_timeout(settings.default_timeout_ms)
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield ctx
    trace_path = settings.artifacts_dir / "traces" / f"{_safe(request.node.name)}.zip"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    ctx.tracing.stop(path=str(trace_path))
    allure.attach.file(str(trace_path), name="trace", extension="zip")
    ctx.close()


@pytest.fixture
def page(context, settings, request):
    """Create a page and attach a screenshot when the test call fails."""
    page = context.new_page()
    yield page
    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        allure.attach(
            page.screenshot(full_page=True),
            name="failure_screenshot",
            attachment_type=allure.attachment_type.PNG,
        )


@pytest.fixture
def shopping(page, settings) -> ShoppingFlow:
    """Provide the shopping flow bound to the current test page."""
    return ShoppingFlow(page, settings)
