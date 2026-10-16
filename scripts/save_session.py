"""Open a visible browser, let a HUMAN complete any verification, then save the session."""
from playwright.sync_api import sync_playwright

from config.settings import load_settings


def main() -> None:
    """Launch a visible browser and save the manually verified session state."""
    s = load_settings()
    out = s.artifacts_dir / "auth" / "state.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context(locale=s.locale)
        page = ctx.new_page()
        page.goto(s.base_url)
        input("Complete any verification in the browser, then press Enter here...")
        ctx.storage_state(path=str(out))
        browser.close()
    print(f"Saved session to {out}")


if __name__ == "__main__":
    main()