import pytest

from utils.data_loader import SearchScenario, load_scenarios


@pytest.mark.unit
@pytest.mark.parametrize("filename", ["search_scenarios.json", "search_scenarios.csv"])
def test_json_and_csv_scenarios_load_to_the_same_typed_values(filename):
    """Verify every data format produces identical, correctly typed scenarios."""
    scenarios = load_scenarios(filename)

    assert scenarios[0] == SearchScenario(id="shoes_under_220", query="shoes", max_price=220.0, limit=5)
    assert isinstance(scenarios[0].limit, int)


@pytest.mark.unit
def test_budget_defaults_to_max_price_and_can_be_overridden():
    """Verify the cart budget falls back to the search price ceiling."""
    base = {"id": "x", "query": "q", "max_price": "50"}

    assert SearchScenario.from_record(base).budget == 50.0
    assert SearchScenario.from_record({**base, "budget_per_item": "30"}).budget == 30.0
