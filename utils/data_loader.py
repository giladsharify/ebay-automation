"""Load external test data (JSON / YAML / CSV) for data-driven tests."""
from __future__ import annotations

import csv
import json
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
