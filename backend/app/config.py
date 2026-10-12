"""Paths and reference data. Everything overridable by env var (handy for tests)."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DELIVERIES_DIR = Path(os.getenv("HUB_DELIVERIES_DIR", REPO_ROOT / "data" / "deliveries"))
RATES_FILE = Path(os.getenv("HUB_RATES_FILE", REPO_ROOT / "data" / "exchange_rates.json"))
DB_PATH = Path(os.getenv("HUB_DB_PATH", REPO_ROOT / "backend" / "campaign_hub.db"))
# Built frontend (npm run build). If present, FastAPI serves it, so the app runs with Python alone.
FRONTEND_DIST = Path(os.getenv("HUB_FRONTEND_DIST", REPO_ROOT / "frontend" / "dist"))

# Platform ids double as filename prefixes: <platform>_<week-start>[_resend].<ext>
PLATFORMS = ("meta_ads", "google_ads", "linkedin_ads")


def load_rates(path: Path = RATES_FILE) -> dict[str, Decimal]:
    """Fixed finance-team rates: 1 unit of currency = N USD."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {code.upper(): Decimal(str(rate)) for code, rate in data["rates"].items()}
