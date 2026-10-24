"""Normalized market-data models shared by adapters, the engine and strategies.

All timestamps are timezone-aware UTC (naive values are rejected, other zones are
converted). Prices are `Decimal`; floats are rejected so binary rounding never
leaks into the ledger.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


class Timeframe(StrEnum):
    MIN_1 = "1Min"
    MIN_5 = "5Min"
    MIN_15 = "15Min"
    HOUR_1 = "1Hour"
    DAY_1 = "1Day"


def _to_utc(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)
    return value


def _reject_float(value: Any) -> Any:
    if isinstance(value, float):
        raise ValueError("use Decimal (or str/int), not float, for prices and sizes")
    return value


UtcDatetime = Annotated[datetime, BeforeValidator(_to_utc)]
Price = Annotated[Decimal, BeforeValidator(_reject_float), Field(gt=0, allow_inf_nan=False)]
Quantity = Annotated[Decimal, BeforeValidator(_reject_float), Field(ge=0, allow_inf_nan=False)]


class Bar(BaseModel):
    """One OHLCV bar, stamped with its start time."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1)
    timestamp: UtcDatetime
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity
    timeframe: Timeframe

    @model_validator(mode="after")
    def _check_ohlc(self) -> Self:
        if self.high < self.low:
            raise ValueError("high must be >= low")
        for name in ("open", "close"):
            if not self.low <= getattr(self, name) <= self.high:
                raise ValueError(f"{name} must be within [low, high]")
        return self


class Tick(BaseModel):
    """A single trade/quote update."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1)
    timestamp: UtcDatetime
    price: Price
    size: Quantity
