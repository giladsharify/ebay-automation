import pytest

from utils import data_loader
from utils.data_loader import SearchScenario, load_data, load_scenarios

pytestmark = pytest.mark.unit

# fixture data lives in the test, so editing data/search_scenarios.* never breaks unit tests
RECORD = {"id": "sample_under_50", "query": "sample query", "max_price": 50, "limit": 3}
FILES = {
    "scenarios.json": '[{"id": "sample_under_50", "query": "sample query", "max_price": 50, "limit": 3}]',
    "scenarios.yaml": "- {id: sample_under_50, query: sample query, max_price: 50, limit: 3}\n",
    "scenarios.csv": "id,query,max_price,limit,budget_per_item\nsample_under_50,sample query,50,3,\n",
}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point the loader at a temporary data directory with one scenario per format."""
    for name, content in FILES.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    monkeypatch.setattr(data_loader, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.mark.parametrize("filename", sorted(FILES))
def test_every_format_loads_to_the_same_typed_scenario(data_dir, filename):
    """Verify JSON, YAML and CSV produce identical, correctly typed scenarios."""
    [scenario] = load_scenarios(filename)

    assert scenario == SearchScenario.from_record(RECORD)
    assert isinstance(scenario.limit, int) and isinstance(scenario.max_price, float)


def test_unsupported_format_is_rejected(data_dir):
    """Verify an unknown file type fails loudly instead of returning nothing."""
    (data_dir / "scenarios.txt").write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported data file type"):
        load_data("scenarios.txt")


def test_project_json_and_csv_scenarios_stay_in_sync():
    """Verify the shipped JSON and CSV files describe the same scenarios, whatever they are."""
    assert load_scenarios("search_scenarios.json") == load_scenarios("search_scenarios.csv")


def test_budget_defaults_to_max_price_and_can_be_overridden():
    """Verify the cart budget falls back to the search price ceiling."""
    base = {"id": "x", "query": "q", "max_price": "50"}

    assert SearchScenario.from_record(base).budget == 50.0
    assert SearchScenario.from_record({**base, "budget_per_item": "30"}).budget == 30.0
