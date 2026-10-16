# eBay E2E Automation (Playwright + Python)

## Prerequisites
- Python 3.10+
- `pip install -r requirements.txt`
- `playwright install chromium`

## Run
```bash
pytest -m unit                         # fast, deterministic checks (no browser)
pytest -m e2e -k shoes -s              # headed E2E demo against production
TEST_ENV=ci pytest -m unit              # CI: unit tests only
allure serve reports/allure-results     # view the Allure report (needs Allure CLI)
```
A JUnit XML report is always written to `reports/junit.xml`.

## Test Environment
Production eBay (`https://www.ebay.com`) is the selected environment for
demonstrating the complete search-to-cart flow because it has live listings.
The `dev` profile and `.env.example` use production URLs. Use a dedicated test
account and verify that the configured query has active listings under its
price limit before the demo. Keep the test headed for the recommended manual
run. eBay may still present an access challenge; if so, the E2E test records a
screenshot and explicitly skips, as CAPTCHA solving is outside the exercise.

Sandbox is optional, not the default demo environment. It is isolated from
production and often has no matching inventory. To demonstrate the complete
flow there, first create active Sandbox listings with prices below the scenario
limits, then run with a Sandbox buyer account and both URLs overridden:

```bash
BASE_URL=https://www.sandbox.ebay.com \
CART_URL=https://cart.sandbox.ebay.com \
pytest -m e2e -k shoes -s
```

If a search returns zero URLs, the test skips before add-to-cart and subtotal
assertion. That run only demonstrates the no-results behavior; it must not be
presented as a successful demonstration of the complete E2E flow. CI runs the
unit suite only because third-party inventory and access challenges make live
E2E unsuitable as a deterministic CI check.

## Architecture
- `pages/` - Page Objects (one class per page, all locators inside them)
- `flows/shopping_flow.py` - the four required functions, composed from page objects
- `utils/` - price parser, data loader, logger
- `config/` - settings + YAML profiles (`TEST_ENV`), env-var overrides
- `data/` - external test data (JSON)
- `tests/` - unit tests and parametrized e2e tests; `conftest.py` holds fixtures (trace + screenshots)

## Assumptions & limitations
- Login is optional: if `EBAY_USERNAME` or `EBAY_PASSWORD` is absent, the flow
  continues as a guest. Set both values locally when the scenario must verify
  authentication. Never commit real credentials.
- The E2E suite interacts with a third-party site. Production inventory,
  selectors, and responses can change or make a run intermittent. When eBay
  presents a CAPTCHA/access challenge, the test logs and screenshots it, then
  reports an explicit skip; the challenge is not bypassed because solving it is
  outside the exercise scope. A passing run is not guaranteed by the test code
  alone.
- Production listings and prices can change between runs. Check that matching
  listings are currently available and below the configured limits before the
  demo; a CAPTCHA/access challenge results in a documented skip, not a pass.
- Before adding items, the flow records the existing cart subtotal in a
  temporary tab. The final assertion compares only the subtotal increase from
  this run with `budget_per_item * items_count`; it does not delete existing
  cart items. Use a dedicated account and avoid concurrent cart changes while
  the test runs.
- Playwright traces, screenshots, and saved authentication state are written
  under `artifacts/`, which is ignored by Git. Treat saved session state as a
  credential and do not share it.
- Search and item-page selectors are site-DOM dependent and may need updates
  when eBay changes its markup.
