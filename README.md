# eBay E2E Automation (Playwright + Python)

End-to-end scenario on eBay: search products under a price limit, add them to the
cart, and verify that the cart subtotal does not exceed the budget. Built with the
Page Object Model, OOP, and data-driven test inputs.

**Sample run:** [docs/sample-run/](docs/sample-run/), a passing E2E run with an Allure
report, JUnit XML, and screenshots ([details below](#sample-run)).

## Prerequisites
- Python 3.10+
- Allure CLI to view reports (`brew install allure`, optional)

## Setup
```bash
python -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env                  # optional: profile, URLs, credentials
```

### Save a browser session (recommended before E2E)
eBay often shows a human-verification page to automated browsers. Solve it once by hand
and reuse that session:
```bash
python -m scripts.save_session        # a browser opens: complete any verification, then press Enter
```
This writes `artifacts/auth/state.json`, and every E2E test then loads it automatically.
The file contains session cookies. It is ignored by Git and must not be shared.

## Run
```bash
pytest -m unit                        # fast unit tests, no browser
pytest -m component                   # offline browser tests: XPath locators + paging on local HTML
pytest -m e2e -k shoes -s             # live E2E against www.ebay.com (headed)
TEST_ENV=ci pytest -m "unit or component"   # what CI runs
```

Reports:
```bash
allure serve reports/allure-results   # interactive Allure report
# reports/junit.xml is always written as well
```

## The four required functions
All four are in [flows/shopping_flow.py](flows/shopping_flow.py) (`ShoppingFlow`):

| Exercise function | Implementation |
|---|---|
| Authentication | `login()`: signs in with `EBAY_USERNAME`/`EBAY_PASSWORD`, otherwise continues as guest |
| `searchItemsByNameUnderPrice` | `search_items_by_name_under_price(query, max_price, limit=5)` |
| `addItemsToCart` | `add_items_to_cart(urls)` |
| `assertCartTotalNotExceeds` | `assert_cart_total_not_exceeds(budget_per_item, items_count)` |

## Architecture
```
config/      settings.py + YAML profiles (dev, ci); environment variables override the profile
data/        external test data: search_scenarios.json (+ the same data as .csv)
pages/       Page Objects, one class per page; all locators live here
  base_page.py    shared helpers: navigation, screenshots (also attached to Allure), access-challenge detection
  search_page.py  search with price filter, XPath card parsing, paging
  item_page.py    random variant selection, Add to cart, confirmation check
  cart_page.py    reads the displayed subtotal
  login_page.py   sign-in, falls back to guest
flows/       ShoppingFlow: business-level steps composed from page objects
utils/       price_parser, data_loader (typed SearchScenario), logger (console + file)
tests/
  unit/        page/flow logic with mocks
  component/   real Playwright + real locators against local HTML (paging, price filter, dedup)
  e2e/         data-driven live scenario
scripts/     save_session.py: manual verification + session save
```
- **SRP:** pages know only the DOM, the flow knows only the business steps, and parsing,
  data, and logging are separate utils. Tests just call the flow.
- **Fixtures** ([tests/conftest.py](tests/conftest.py)): one browser per session and a
  fresh context per test with Playwright tracing. On failure, the fixtures attach a screenshot.

## Robustness
- **Search:** the price ceiling is applied through eBay's URL filter (`_udhi`), and each
  card's price is still checked client-side, because sponsored and range-priced cards can
  slip through the filter.
- **XPath locators** match both the old (`s-item`) and new (`s-card`) eBay result-card markup.
- **Paging:** follows "Next" until `limit` items are collected or the pages run out. Waits
  for the URL to change before reading cards, so cards from the previous page are never
  re-read. Returns a partial list, or an empty one, when fewer items exist.
- **Price parsing** ([utils/price_parser.py](utils/price_parser.py)): currency symbols and
  codes, US and EU separators, and ranges such as `$20.00 to $30.00` (the lowest price is used).
- **Variants:** random choice (seeded via `random_seed`, so runs are reproducible) among
  available options in both native `<select>` and custom listbox dropdowns. Placeholder,
  disabled, and out-of-stock options are skipped.
- **Add to cart** succeeds when a confirmation appears or the cart badge count increases.
  On failure, it saves a screenshot and the buy-box HTML.
- **Access challenges** (CAPTCHA) are detected, screenshotted, and reported as an explicit
  skip. They are never bypassed.

## Data-driven and configuration
- Scenarios come from `data/search_scenarios.json`. Any JSON/YAML/CSV file in `data/` can be
  used instead: `SCENARIOS_FILE=search_scenarios.csv pytest -m e2e`.
- Scenario fields: `id`, `query`, `max_price`, `limit`, and an optional `budget_per_item`
  (defaults to `max_price`).
- Profiles: `TEST_ENV=dev|ci` selects `config/profiles/<env>.yaml` (URLs, browser, headless,
  timeouts, locale, seed). Any field can be overridden with an environment variable or `.env`:
  `BASE_URL`, `CART_URL`, `BROWSER`, `HEADLESS`, `SLOW_MO_MS`, `DEFAULT_TIMEOUT_MS`,
  `LOCALE`, `RANDOM_SEED`, `EBAY_USERNAME`, `EBAY_PASSWORD`.

## Reports and evidence
- **Allure:** steps for every page action, screenshots for each added item and the cart,
  the run log, and the Playwright trace.
- **JUnit XML:** `reports/junit.xml`.
- **Artifacts** (`artifacts/`, ignored by Git): `screenshots/`, `traces/` (open with
  `playwright show-trace <zip>`), and `logs/run.log`.

<a id="sample-run"></a>
### Sample run ([docs/sample-run/](docs/sample-run/))
- `allure-report/index.html`: a self-contained Allure report. Download it and open it in a browser.
  - It contains the passing E2E run (`shoes` under 220, 5 items) plus the unit and component suites.
  - The 45 MB trace was left out to keep the repository small.
- `junit-e2e.xml`, `junit-offline.xml`: JUnit reports.
- `screenshots/`: each added item and the final cart (subtotal ILS 325.41 for 5 items,
  against a threshold of 220 × 5).

![Allure overview](docs/sample-run/allure-overview.png)
![Allure E2E test](docs/sample-run/allure-e2e-test.png)

## Assumptions and limitations
- **Login:** optional. Without credentials, or when sign-in is blocked, the flow continues as guest.
- **Currency:**
  - `max_price` and `budget_per_item` are plain numbers with no currency conversion.
  - The search filter uses the site's listing currency, while the cart shows the currency of
    the ship-to location. In the sample run that was Israel, so the cart showed ILS.
  - For a strict comparison, run with a ship-to location whose currency matches the budget.
- **Subtotal** is read exactly as the site displays it, so it can include shipping.
- **Existing cart contents:** before adding items, the flow records the current subtotal.
  The assertion checks only the increase from this run (`after - before <= budget × count`)
  and never deletes the user's items. Avoid changing the cart concurrently during a run.
- **Quantity** is left at 1. A random quantity above 1 would break the invariant that every
  item costs at most `budget_per_item`, which the cart assertion depends on.
- **Negative case:** the assertion failing when the budget is exceeded is covered in
  [tests/unit/test_cart_baseline.py](tests/unit/test_cart_baseline.py).
- **Live-site dependence:** inventory, prices, and DOM can change between runs, so live E2E
  is not part of CI. CI runs the deterministic unit and component suites
  ([.github/workflows/tests.yml](.github/workflows/tests.yml)).
- **Sandbox:** optional. It usually has no inventory. To use it, set `BASE_URL=https://www.sandbox.ebay.com` and `CART_URL=https://cart.sandbox.ebay.com`.

## AI bugs analysis
See [ReadMeAIBugs.md](ReadMeAIBugs.md).
