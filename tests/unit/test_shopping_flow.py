import pytest

from flows.shopping_flow import ShoppingFlow

# arbitrary search inputs: the page/flow logic must not depend on any specific product
QUERY = "sample query"
MAX_PRICE = 220


class SearchPageStub:
    def __init__(self):
        """Initialize a stub that records search and collection arguments."""
        self.search_args = None
        self.collect_args = None

    def search(self, query, max_price):
        """Record the query and price limit sent by the shopping flow."""
        self.search_args = (query, max_price)

    def collect_item_urls(self, max_price, limit):
        """Record collection arguments and return one sample item URL."""
        self.collect_args = (max_price, limit)
        return ["https://example.test/item/1"]


@pytest.mark.unit
def test_search_flow_applies_price_filter_and_limit():
    """Verify the flow passes the query, maximum price, and URL limit correctly."""
    flow = ShoppingFlow.__new__(ShoppingFlow)
    flow.search_page = SearchPageStub()

    urls = flow.search_items_by_name_under_price(QUERY, MAX_PRICE, limit=5)

    assert flow.search_page.search_args == (QUERY, MAX_PRICE)
    assert flow.search_page.collect_args == (MAX_PRICE, 5)
    assert urls == ["https://example.test/item/1"]