"""Load external test data (JSON / YAML / CSV) for data-driven tests."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_data(filename: str) -> list[dict[str, Any]]:
    """Load records from a JSON, YAML, or CSV file in the project data directory."""
    path = DATA_DIR / filename
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    if suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    raise ValueError(f"Unsupported data file type: {suffix}")


@dataclass(frozen=True)
class SearchScenario:
    """One search-to-cart scenario; values are coerced so CSV strings work too."""

    id: str
    query: str
    max_price: float
    limit: int = 5
    budget_per_item: float | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> SearchScenario:
        """Build a scenario from a raw data-file record."""
        budget = record.get("budget_per_item")
        return cls(
            id=str(record["id"]),
            query=str(record["query"]),
            max_price=float(record["max_price"]),
            limit=int(record.get("limit") or 5),
            budget_per_item=float(budget) if budget not in (None, "") else None,
        )

    @property
    def budget(self) -> float:
        """Per-item cart budget; defaults to the search price ceiling."""
        return self.budget_per_item if self.budget_per_item is not None else self.max_price


def load_scenarios(filename: str) -> list[SearchScenario]:
    """Load search scenarios from any supported data file."""
    return [SearchScenario.from_record(r) for r in load_data(filename)]
