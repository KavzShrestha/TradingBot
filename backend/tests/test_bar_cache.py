from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.data.cache import BarCache
from app.data.models import Bar, Timeframe

D0 = datetime(2024, 1, 1, tzinfo=UTC)
NOW = datetime(2030, 1, 1, tzinfo=UTC)
TF = Timeframe.DAY_1


def day(n: int) -> datetime:
    return D0 + timedelta(days=n)


def bar(n: int, symbol: str = "SPY", close: str = "10.10") -> Bar:
    return Bar(
        symbol=symbol,
        timestamp=day(n),
        open=Decimal("10.05"),
        high=Decimal("10.20"),
        low=Decimal("10.00"),
        close=Decimal(close),
        volume=Decimal("1000"),
        timeframe=TF,
    )


class FakeFetcher:
    """Serves one bar per day (except those in `skip`) and logs every call."""

    def __init__(self, skip: frozenset[int] = frozenset()) -> None:
        self.calls: list[tuple[str, Timeframe, datetime, datetime]] = []
        self.skip = skip

    def __call__(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Bar]:
        self.calls.append((symbol, timeframe, start, end))
        return [
            bar(n, symbol) for n in range(400) if start <= day(n) <= end and n not in self.skip
        ]


@pytest.fixture
def cache(tmp_path: Path) -> BarCache:
    return BarCache(tmp_path, clock=lambda: NOW)


def test_miss_then_hit_calls_fetcher_once(cache: BarCache) -> None:
    f = FakeFetcher()
    first = cache.get_bars("SPY", TF, day(0), day(9), f)
    second = cache.get_bars("SPY", TF, day(0), day(9), f)
    assert len(f.calls) == 1
    assert first == second
    assert [b.timestamp for b in first] == [day(n) for n in range(10)]


def test_fetches_only_missing_ranges(cache: BarCache) -> None:
    f = FakeFetcher()
    cache.get_bars("SPY", TF, day(5), day(9), f)
    f.calls.clear()
    bars = cache.get_bars("SPY", TF, day(0), day(14), f)
    assert [(c[2], c[3]) for c in f.calls] == [(day(0), day(5)), (day(9), day(14))]
    assert [b.timestamp for b in bars] == [day(n) for n in range(15)]


def test_upserts_are_idempotent(cache: BarCache) -> None:
    f = FakeFetcher()
    cache.get_bars("SPY", TF, day(0), day(9), f)
    cache.get_bars("SPY", TF, day(5), day(14), f)
    bars = cache.get_bars("SPY", TF, day(0), day(14), f)
    assert len(bars) == 15
    assert len({b.timestamp for b in bars}) == 15


def test_empty_ranges_are_not_refetched(cache: BarCache) -> None:
    f = FakeFetcher(skip=frozenset({2, 3}))
    bars = cache.get_bars("SPY", TF, day(0), day(5), f)
    cache.get_bars("SPY", TF, day(0), day(5), f)
    assert len(f.calls) == 1
    assert [b.timestamp for b in bars] == [day(n) for n in (0, 1, 4, 5)]


def test_keyed_by_symbol_and_timeframe(cache: BarCache) -> None:
    f = FakeFetcher()
    cache.get_bars("SPY", TF, day(0), day(3), f)
    cache.get_bars("QQQ", TF, day(0), day(3), f)
    assert len(f.calls) == 2
    assert all(b.symbol == "QQQ" for b in cache.get_bars("QQQ", TF, day(0), day(3), f))


def test_decimal_round_trip_and_utc(cache: BarCache) -> None:
    def fetcher(s: str, tf: Timeframe, a: datetime, b: datetime) -> list[Bar]:
        return [bar(1, close="10.1000000001")]

    cache.get_bars("SPY", TF, day(0), day(2), fetcher)
    (got,) = cache.get_bars("SPY", TF, day(0), day(2), fetcher)
    assert got.close == Decimal("10.1000000001")
    assert isinstance(got.close, Decimal)
    assert got.timestamp == day(1)
    assert got.timestamp.utcoffset() == timedelta(0)


def test_output_sorted_when_fetcher_returns_unsorted(cache: BarCache) -> None:
    def fetcher(s: str, tf: Timeframe, a: datetime, b: datetime) -> list[Bar]:
        return [bar(3), bar(1), bar(2)]

    bars = cache.get_bars("SPY", TF, day(0), day(4), fetcher)
    assert [b.timestamp for b in bars] == [day(1), day(2), day(3)]


def test_persists_across_instances(tmp_path: Path) -> None:
    f = FakeFetcher()
    c1 = BarCache(tmp_path, clock=lambda: NOW)
    c1.get_bars("SPY", TF, day(0), day(4), f)
    c1.close()
    c2 = BarCache(tmp_path, clock=lambda: NOW)
    assert len(c2.get_bars("SPY", TF, day(0), day(4), f)) == 5
    assert len(f.calls) == 1


def test_future_range_not_marked_covered(tmp_path: Path) -> None:
    cache = BarCache(tmp_path, clock=lambda: day(5))
    f = FakeFetcher()
    cache.get_bars("SPY", TF, day(0), day(9), f)
    f.calls.clear()
    cache.get_bars("SPY", TF, day(0), day(9), f)
    assert [(c[2], c[3]) for c in f.calls] == [(day(5), day(9))]


def test_non_utc_inputs_are_normalized(cache: BarCache) -> None:
    tz = timezone(timedelta(hours=5))
    f = FakeFetcher()
    cache.get_bars("SPY", TF, day(0).astimezone(tz), day(3).astimezone(tz), f)
    assert f.calls[0][2].utcoffset() == timedelta(0)


def test_rejects_naive_and_inverted_ranges(cache: BarCache) -> None:
    f = FakeFetcher()
    with pytest.raises(ValueError, match="timezone-aware"):
        cache.get_bars("SPY", TF, datetime(2024, 1, 1), day(3), f)
    with pytest.raises(ValueError, match="end"):
        cache.get_bars("SPY", TF, day(3), day(1), f)


def test_rejects_out_of_range_fetcher_bars(cache: BarCache) -> None:
    def fetcher(s: str, tf: Timeframe, a: datetime, b: datetime) -> list[Bar]:
        return [bar(50)]

    with pytest.raises(ValueError, match="outside"):
        cache.get_bars("SPY", TF, day(0), day(3), fetcher)
