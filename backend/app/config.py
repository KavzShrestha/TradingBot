"""Application settings and environment loading.

Implements CLAUDE.md Hard Rule #1: the app must refuse to start unless
`PAPER_TRADING=true`, and must refuse any base URL on the live-endpoint
denylist below. See `Settings.validate_paper_trading_safe()` and
`get_settings()`, which enforces the guard on every call.
"""

from __future__ import annotations

import os
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

_ENV_FILE = Path(".env")

# Known real-money/production API base URLs for common brokers/exchanges.
#
# This list is NOT exhaustive. When wiring up a new broker/exchange
# integration, add its live base URL here *before* pointing anything at its
# paper/sandbox counterpart, so the startup guard below can catch a
# misconfigured DATA_BASE_URL.
LIVE_ENDPOINT_DENYLIST: frozenset[str] = frozenset(
    {
        "https://api.alpaca.markets",  # Alpaca live trading
        "https://api.binance.com",  # Binance live spot/futures
        "https://api.binance.us",  # Binance.US live
        "https://api.exchange.coinbase.com",  # Coinbase Exchange live
        "https://api.coinbase.com",  # Coinbase live
        "https://api.kraken.com",  # Kraken live
        "https://api.ibkr.com",  # Interactive Brokers live gateway
    }
)


def _is_live_endpoint(base_url: str) -> bool:
    """Return True if `base_url` matches, or is a sub-path of, a denylisted URL."""
    normalized = base_url.strip().rstrip("/").lower()
    for denied in LIVE_ENDPOINT_DENYLIST:
        denied_normalized = denied.rstrip("/").lower()
        if normalized == denied_normalized or normalized.startswith(denied_normalized + "/"):
            return True
    return False


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
    data_base_url: str = "https://paper-api.alpaca.markets"
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
            data_base_url=os.getenv("DATA_BASE_URL", "https://paper-api.alpaca.markets"),
            starting_capital=Decimal(os.getenv("STARTING_CAPITAL", "100000")),
            slippage_bps=Decimal(os.getenv("SLIPPAGE_BPS", "5")),
            commission_per_trade=Decimal(os.getenv("COMMISSION_PER_TRADE", "1.00")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./paper.db"),
        )

    def validate_paper_trading_safe(self) -> None:
        """Enforce CLAUDE.md Hard Rule #1.

        Raises:
            RuntimeError: if PAPER_TRADING is not enabled, or if `data_base_url`
                is a real-money/production endpoint on `LIVE_ENDPOINT_DENYLIST`.
        """
        if not self.paper_trading:
            raise RuntimeError(
                "Refusing to start: PAPER_TRADING is not enabled (got "
                f"paper_trading={self.paper_trading!r}). Set PAPER_TRADING=true "
                "in the environment or .env file. This application must never "
                "place real-money orders."
            )
        if _is_live_endpoint(self.data_base_url):
            raise RuntimeError(
                f"Refusing to start: DATA_BASE_URL '{self.data_base_url}' is a "
                "live/production trading endpoint on the denylist in "
                "app/config.py. Point DATA_BASE_URL at a paper/sandbox URL or "
                "the internal simulator."
            )


@lru_cache
def get_settings() -> Settings:
    """Return a cached, validated Settings instance for the process lifetime.

    Enforces the PAPER_TRADING guard and live-endpoint denylist on every
    (first) call, so any code path that calls `get_settings()` -- including
    app startup -- refuses to run with an unsafe configuration.
    """
    settings = Settings.from_env()
    settings.validate_paper_trading_safe()
    return settings
