from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.data.models import Bar, Tick, Timeframe

TS = datetime(2024, 1, 2, 14, 30, tzinfo=UTC)


def make_bar(**over: Any) -> Bar:
    fields: dict[str, Any] = dict(
        symbol="SPY",
        timestamp=TS,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("99"),
        close=Decimal("104"),
        volume=Decimal("1000"),
        timeframe=Timeframe.HOUR_1,
    )
    fields.update(over)
    return Bar(**fields)


def test_valid_bar() -> None:
    bar = make_bar()
    assert bar.close == Decimal("104")
    assert bar.timestamp.utcoffset() == timedelta(0)


def test_timeframes_exist() -> None:
    assert Timeframe("1Hour") is Timeframe.HOUR_1
    assert Timeframe("1Day") is Timeframe.DAY_1


def test_bar_is_frozen() -> None:
    with pytest.raises(ValidationError):
        make_bar().close = Decimal("1")  # type: ignore[misc]


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(ValidationError):
        make_bar(timestamp=datetime(2024, 1, 2, 14, 30))
    with pytest.raises(ValidationError):
        Tick(symbol="SPY", timestamp=datetime(2024, 1, 2), price=Decimal(1), size=Decimal(1))


def test_non_utc_converted_to_utc() -> None:
    est = timezone(timedelta(hours=-5))
    bar = make_bar(timestamp=datetime(2024, 1, 2, 9, 30, tzinfo=est))
    assert bar.timestamp == TS
    assert bar.timestamp.tzinfo is UTC


def test_high_below_low_rejected() -> None:
    with pytest.raises(ValidationError):
        make_bar(high=Decimal("98"), low=Decimal("99"), open=Decimal("98"), close=Decimal("98"))


@pytest.mark.parametrize("field", ["open", "close"])
@pytest.mark.parametrize("value", [Decimal("98"), Decimal("106")])
def test_open_close_outside_range_rejected(field: str, value: Decimal) -> None:
    with pytest.raises(ValidationError):
        make_bar(**{field: value})


def test_negative_volume_rejected() -> None:
    with pytest.raises(ValidationError):
        make_bar(volume=Decimal("-1"))


def test_zero_volume_allowed() -> None:
    assert make_bar(volume=Decimal("0")).volume == 0


def test_float_price_rejected() -> None:
    with pytest.raises(ValidationError):
        make_bar(open=100.5)


def test_non_positive_price_and_nan_rejected() -> None:
    with pytest.raises(ValidationError):
        make_bar(low=Decimal("0"))
    with pytest.raises(ValidationError):
        make_bar(high=Decimal("NaN"))


def test_unknown_timeframe_and_empty_symbol_rejected() -> None:
    with pytest.raises(ValidationError):
        make_bar(timeframe="3Fortnight")
    with pytest.raises(ValidationError):
        make_bar(symbol="")


def test_valid_tick_and_frozen() -> None:
    tick = Tick(symbol="SPY", timestamp=TS, price=Decimal("100.25"), size=Decimal("10"))
    assert tick.price == Decimal("100.25")
    with pytest.raises(ValidationError):
        tick.price = Decimal("1")  # type: ignore[misc]


def test_tick_invalid_values() -> None:
    with pytest.raises(ValidationError):
        Tick(symbol="SPY", timestamp=TS, price=Decimal("-1"), size=Decimal("1"))
    with pytest.raises(ValidationError):
        Tick(symbol="SPY", timestamp=TS, price=Decimal("1"), size=Decimal("-1"))
