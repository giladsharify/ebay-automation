"""Central configuration: YAML profile (TEST_ENV) + environment-variable overrides."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"


@dataclass(frozen=True)
class Settings:
    env: str
    base_url: str
    cart_url: str
    browser: str
    headless: bool
    slow_mo_ms: int
    default_timeout_ms: int
    locale: str
    random_seed: int
    artifacts_dir: Path
    username: str | None = None
    password: str | None = None


def _as_bool(value: object) -> bool:
    """Convert a configuration value to a boolean flag."""
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    """Load settings from the selected YAML profile and environment overrides."""
    load_dotenv(ROOT / ".env")
    env = os.getenv("TEST_ENV", "dev")
    profile_path = PROFILES_DIR / f"{env}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Unknown TEST_ENV '{env}': {profile_path} not found")
    cfg = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}

    return Settings(
        env=env,
        base_url=os.getenv("BASE_URL", cfg["base_url"]),
        cart_url=os.getenv("CART_URL", cfg["cart_url"]),
        browser=os.getenv("BROWSER", cfg["browser"]),
        headless=_as_bool(os.getenv("HEADLESS", cfg["headless"])),
        slow_mo_ms=int(os.getenv("SLOW_MO_MS", cfg["slow_mo_ms"])),
        default_timeout_ms=int(os.getenv("DEFAULT_TIMEOUT_MS", cfg["default_timeout_ms"])),
        locale=os.getenv("LOCALE", cfg["locale"]),
        random_seed=int(os.getenv("RANDOM_SEED", cfg["random_seed"])),
        artifacts_dir=ROOT / "artifacts",
        username=os.getenv("EBAY_USERNAME"),
        password=os.getenv("EBAY_PASSWORD"),
    )
