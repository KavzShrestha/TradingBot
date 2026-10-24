"""On-disk SQLite cache for historical bars so backtests don't re-download data.

Bars are keyed by (symbol, timeframe, timestamp). Because a closed-market period
legitimately returns no bars, the cache also records which time ranges have already
been fetched ("coverage"); only uncovered sub-ranges are passed to the injected fetcher.
Prices are stored as `Decimal` strings so they round-trip exactly.

Bars are stamped with their open time, so a bar is only final once
`timestamp + timeframe duration <= now`. Coverage is clamped to the last fully closed bar
(`now - duration`) and bars after that point (the still-forming bar) are neither stored
nor marked covered; they are re-fetched on the next call.

Limitation: whatever the fetcher returns for a closed range is permanently treated as
covered. If the fetcher truncates its result (e.g. a page limit), the missing bars are
never re-fetched; fetchers must return the complete range.

`BarCache` is a context manager; use `with BarCache(...) as cache:` to close the connection.

The default location `data/cache/` is gitignored.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from app.data.models import Bar, Timeframe

DEFAULT_CACHE_DIR = Path("data/cache")
DB_FILENAME = "bars.sqlite"

Fetcher = Callable[[str, Timeframe, datetime, datetime], list[Bar]]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts TEXT NOT NULL,
    open TEXT NOT NULL,
    high TEXT NOT NULL,
    low TEXT NOT NULL,
    close TEXT NOT NULL,
    volume TEXT NOT NULL,
    PRIMARY KEY (symbol, timeframe, ts)
);
CREATE TABLE IF NOT EXISTS coverage (
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_ts TEXT NOT NULL,
    end_ts TEXT NOT NULL,
    PRIMARY KEY (symbol, timeframe, start_ts)
);
"""

_DURATION = {
    Timeframe.MIN_1: timedelta(minutes=1),
    Timeframe.MIN_5: timedelta(minutes=5),
    Timeframe.MIN_15: timedelta(minutes=15),
    Timeframe.HOUR_1: timedelta(hours=1),
    Timeframe.DAY_1: timedelta(days=1),
}

_TS_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


def _ts(value: datetime) -> str:
    """Fixed-width UTC string, so lexicographic order equals chronological order."""
    return value.astimezone(UTC).strftime(_TS_FORMAT)


def _parse(value: str) -> datetime:
    return datetime.strptime(value, _TS_FORMAT).replace(tzinfo=UTC)


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BarCache:
    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        directory = Path(cache_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._conn = sqlite3.connect(directory / DB_FILENAME)
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> BarCache:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        fetcher: Fetcher,
    ) -> list[Bar]:
        """Return bars in [start, end] ascending, fetching only uncached ranges."""
        _require_aware("start", start)
        _require_aware("end", end)
        if end < start:
            raise ValueError("end must be >= start")
        start, end = start.astimezone(UTC), end.astimezone(UTC)

        for gap_start, gap_end in self._missing(symbol, timeframe, start, end):
            fetched = fetcher(symbol, timeframe, gap_start, gap_end)
            self._store(symbol, timeframe, gap_start, gap_end, fetched)
        return self._read(symbol, timeframe, start, end)

    def _overlapping(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[tuple[datetime, datetime]]:
        rows = self._conn.execute(
            "SELECT start_ts, end_ts FROM coverage WHERE symbol=? AND timeframe=? "
            "AND end_ts>=? AND start_ts<=? ORDER BY start_ts",
            (symbol, timeframe.value, _ts(start), _ts(end)),
        ).fetchall()
        return [(_parse(s), _parse(e)) for s, e in rows]

    def _missing(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[tuple[datetime, datetime]]:
        """Closed sub-ranges of [start, end] not yet covered (boundaries may be re-fetched)."""
        gaps: list[tuple[datetime, datetime]] = []
        cursor: datetime | None = None
        for cov_start, cov_end in self._overlapping(symbol, timeframe, start, end):
            if cursor is None and cov_start > start:
                gaps.append((start, cov_start))
            elif cursor is not None and cov_start > cursor:
                gaps.append((cursor, cov_start))
            cursor = cov_end if cursor is None else max(cursor, cov_end)
        if cursor is None:
            return [(start, end)]
        if cursor < end:
            gaps.append((cursor, end))
        return gaps

    def _store(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        bars: list[Bar],
    ) -> None:
        for bar in bars:
            if bar.symbol != symbol or bar.timeframe != timeframe:
                raise ValueError("fetcher returned a bar for a different symbol/timeframe")
            if not start <= bar.timestamp <= end:
                raise ValueError("fetcher returned a bar outside the requested range")
        last_closed_open = self._clock().astimezone(UTC) - _DURATION[timeframe]
        covered_end = min(end, last_closed_open)
        bars = [b for b in bars if b.timestamp <= covered_end]
        with self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?,?,?,?)",
                [
                    (
                        symbol,
                        timeframe.value,
                        _ts(b.timestamp),
                        str(b.open),
                        str(b.high),
                        str(b.low),
                        str(b.close),
                        str(b.volume),
                    )
                    for b in bars
                ],
            )
            if covered_end >= start:
                self._merge_coverage(symbol, timeframe, start, covered_end)

    def _merge_coverage(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> None:
        overlapping = self._overlapping(symbol, timeframe, start, end)
        lo = min([start, *(s for s, _ in overlapping)])
        hi = max([end, *(e for _, e in overlapping)])
        self._conn.execute(
            "DELETE FROM coverage WHERE symbol=? AND timeframe=? AND end_ts>=? AND start_ts<=?",
            (symbol, timeframe.value, _ts(start), _ts(end)),
        )
        self._conn.execute(
            "INSERT INTO coverage VALUES (?,?,?,?)",
            (symbol, timeframe.value, _ts(lo), _ts(hi)),
        )

    def _read(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Bar]:
        rows = self._conn.execute(
            "SELECT ts, open, high, low, close, volume FROM bars "
            "WHERE symbol=? AND timeframe=? AND ts>=? AND ts<=? ORDER BY ts",
            (symbol, timeframe.value, _ts(start), _ts(end)),
        ).fetchall()
        return [
            Bar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=_parse(ts),
                open=Decimal(o),
                high=Decimal(h),
                low=Decimal(lo),
                close=Decimal(c),
                volume=Decimal(v),
            )
            for ts, o, h, lo, c, v in rows
        ]
