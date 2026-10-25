"""Alpaca historical bars adapter (free plan, IEX feed).

Read-only: only `GET /v2/stocks/<symbol>/bars` on the market-data host is ever called.
No order/trading endpoint is used. Config (see `.env.example`): `DATA_API_KEY`,
`DATA_API_SECRET`, `MARKET_DATA_URL` (default `https://data.alpaca.markets`).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.config import _is_live_endpoint
from app.data.models import Bar, Timeframe

DEFAULT_BASE_URL = "https://data.alpaca.markets"
FEED = "iex"
PAGE_LIMIT = 10_000
SUPPORTED_TIMEFRAMES = frozenset({Timeframe.DAY_1, Timeframe.HOUR_1})
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
SUPPORTED_ADJUSTMENTS = frozenset({"raw", "split", "dividend", "all"})


class AlpacaDataError(RuntimeError):
    """Raised when the market-data API cannot satisfy a request."""


class AlpacaBarsClient:
    """Fetch Alpaca bars; adjustment defaults to ``raw`` and feed is fixed to IEX."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        max_retries: int = 5,
        backoff_seconds: float = 0.5,
        max_backoff_seconds: float = 30.0,
        adjustment: str = "raw",
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if _is_live_endpoint(base_url):
            raise ValueError(f"Refusing live/production endpoint: {base_url}")
        if adjustment not in SUPPORTED_ADJUSTMENTS:
            raise ValueError(
                f"unsupported adjustment {adjustment!r}; use raw, split, dividend, or all"
            )
        self._base_url = base_url.rstrip("/")
        self._adjustment = adjustment
        self._headers = {"APCA-API-KEY-ID": api_key, "APCA-API-SECRET-KEY": api_secret}
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._max_backoff = max_backoff_seconds
        self._client = client or httpx.Client(timeout=30.0)
        self._sleep = sleep

    def get_bars(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Bar]:
        """Fetch bars in [start, end], following pagination. Datetimes must be tz-aware."""
        if timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"unsupported timeframe {timeframe!r}; use 1Day or 1Hour")
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        params: dict[str, str | int] = {
            "timeframe": timeframe.value,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "feed": FEED,
            "adjustment": self._adjustment,
            "limit": PAGE_LIMIT,
        }
        bars: list[Bar] = []
        while True:
            payload = self._request(f"/v2/stocks/{symbol}/bars", params)
            for raw in payload.get("bars") or []:
                bars.append(_to_bar(symbol, timeframe, raw))
            token = payload.get("next_page_token")
            if not token:
                return bars
            params["page_token"] = token

    def _request(self, path: str, params: dict[str, str | int]) -> dict[str, Any]:
        url = self._base_url + path
        for attempt in range(self._max_retries + 1):
            last = attempt == self._max_retries
            try:
                resp = self._client.get(url, params=params, headers=self._headers)
            except httpx.TransportError as exc:
                if last:
                    raise AlpacaDataError(f"transport error: {exc}") from exc
            else:
                if resp.status_code == 200:
                    payload: dict[str, Any] = json.loads(resp.content, parse_float=Decimal)
                    return payload
                if resp.status_code not in _RETRY_STATUSES:
                    raise AlpacaDataError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                if last:
                    raise AlpacaDataError(f"HTTP {resp.status_code} after {attempt + 1} attempts")
            self._sleep(min(self._backoff * 2**attempt, self._max_backoff))
        raise AssertionError("unreachable")  # pragma: no cover


def _to_bar(symbol: str, timeframe: Timeframe, raw: dict[str, Any]) -> Bar:
    return Bar(
        symbol=symbol,
        timestamp=datetime.fromisoformat(raw["t"]),
        open=raw["o"],
        high=raw["h"],
        low=raw["l"],
        close=raw["c"],
        volume=raw["v"],
        timeframe=timeframe,
    )
