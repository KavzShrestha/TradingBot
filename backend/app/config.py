"""Application settings and environment loading.

NOTE: the PAPER_TRADING safety guard (refusing to start unless
PAPER_TRADING=true) and the live-endpoint denylist described in CLAUDE.md are
implemented in task M0-02, not here. This module only loads and types the
configuration values from the environment / .env file.
"""

from __future__ import annotations

import os
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

_ENV_FILE = Path(".env")


def _load_dotenv(path: Path = _ENV_FILE) -> None:
    """Populate os.environ from a simple KEY=VALUE .env file.

    Minimal, dependency-free .env loader (no external package needed for a
    handful of KEY=VALUE lines). Existing environment variables always win.
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


class Settings(BaseModel):
    """Typed application configuration.

    Field names mirror the keys in `.env.example` (lowercased).
    """

    paper_trading: bool = True
    data_provider: str = "alpaca"
    data_api_key: str = ""
    data_api_secret: str = ""
    starting_capital: Decimal = Decimal("100000")
    slippage_bps: Decimal = Decimal("5")
    commission_per_trade: Decimal = Decimal("1.00")
    database_url: str = "sqlite:///./paper.db"

    @classmethod
    def from_env(cls) -> Settings:
        """Build Settings from process environment variables (loading .env first)."""
        _load_dotenv()
        return cls(
            paper_trading=os.getenv("PAPER_TRADING", "true").strip().lower() == "true",
            data_provider=os.getenv("DATA_PROVIDER", "alpaca"),
            data_api_key=os.getenv("DATA_API_KEY", ""),
            data_api_secret=os.getenv("DATA_API_SECRET", ""),
            starting_capital=Decimal(os.getenv("STARTING_CAPITAL", "100000")),
            slippage_bps=Decimal(os.getenv("SLIPPAGE_BPS", "5")),
            commission_per_trade=Decimal(os.getenv("COMMISSION_PER_TRADE", "1.00")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./paper.db"),
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance for the process lifetime."""
    return Settings.from_env()
