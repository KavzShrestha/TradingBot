import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.data.alpaca import AlpacaBarsClient, AlpacaDataError
from app.data.models import Timeframe

START = datetime(2024, 1, 1, tzinfo=UTC)
END = datetime(2024, 2, 1, tzinfo=UTC)

Handler = Callable[[httpx.Request], httpx.Response]


def bar_json(t: str) -> dict[str, Any]:
    return dict(t=t, o=10.5, h=12.25, l=10.1, c=11.0, v=1000, n=5, vw=11)


def ok(payload: dict[str, Any]) -> httpx.Response:
    # Floats in the body exercise Decimal parsing.
    return httpx.Response(200, content=json.dumps(payload).encode())


def make(
    handler: Handler, sleeps: list[float] | None = None, max_retries: int = 5
) -> AlpacaBarsClient:
    log = sleeps if sleeps is not None else []
    return AlpacaBarsClient(
        "k",
        "s",
        max_retries=max_retries,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=log.append,
    )


def test_maps_to_bar_and_request_shape() -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return ok(dict(bars=[bar_json("2024-01-02T05:00:00Z")], next_page_token=None))

    bars = make(handler).get_bars("SPY", Timeframe.DAY_1, START, END)
    assert len(bars) == 1
    b = bars[0]
    assert (b.symbol, b.timeframe) == ("SPY", Timeframe.DAY_1)
    assert b.timestamp == datetime(2024, 1, 2, 5, tzinfo=UTC)
    assert b.open == Decimal("10.5") and b.high == Decimal("12.25")
    req = seen[0]
    assert req.url.host == "data.alpaca.markets" and req.url.path == "/v2/stocks/SPY/bars"
    assert req.url.params["feed"] == "iex" and req.url.params["timeframe"] == "1Day"
    assert req.headers["APCA-API-KEY-ID"] == "k"


def test_follows_pagination() -> None:
    tokens: list[str | None] = []

    def handler(req: httpx.Request) -> httpx.Response:
        tok = req.url.params.get("page_token")
        tokens.append(tok)
        if tok is None:
            return ok(dict(bars=[bar_json("2024-01-02T14:00:00Z")], next_page_token="abc"))
        return ok(dict(bars=[bar_json("2024-01-02T15:00:00Z")], next_page_token=None))

    bars = make(handler).get_bars("SPY", Timeframe.HOUR_1, START, END)
    assert tokens == [None, "abc"]
    assert [b.timestamp.hour for b in bars] == [14, 15]


def test_retries_429_then_succeeds_with_backoff() -> None:
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429)
        return ok(dict(bars=[], next_page_token=None))

    sleeps: list[float] = []
    assert make(handler, sleeps).get_bars("SPY", Timeframe.DAY_1, START, END) == []
    assert calls["n"] == 3 and sleeps == [0.5, 1.0]


def test_retries_transport_error_and_gives_up() -> None:
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("boom")

    with pytest.raises(AlpacaDataError):
        make(handler, max_retries=2).get_bars("SPY", Timeframe.DAY_1, START, END)
    assert calls["n"] == 3


def test_exhausted_retries_on_503() -> None:
    with pytest.raises(AlpacaDataError, match="503"):
        make(lambda r: httpx.Response(503), max_retries=1).get_bars(
            "SPY", Timeframe.DAY_1, START, END
        )


def test_non_retryable_error_fails_fast() -> None:
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(403, text="forbidden")

    with pytest.raises(AlpacaDataError, match="403"):
        make(handler).get_bars("SPY", Timeframe.DAY_1, START, END)
    assert calls["n"] == 1


def test_rejects_live_base_url() -> None:
    with pytest.raises(ValueError, match="live"):
        AlpacaBarsClient("k", "s", base_url="https://api.alpaca.markets")


def test_rejects_bad_timeframe_and_naive_dates() -> None:
    c = make(lambda r: ok(dict(bars=[])))
    with pytest.raises(ValueError, match="timeframe"):
        c.get_bars("SPY", Timeframe.MIN_1, START, END)
    with pytest.raises(ValueError, match="timezone"):
        c.get_bars("SPY", Timeframe.DAY_1, datetime(2024, 1, 1), END)


def test_adjustment_is_passed_through_and_invalid_values_are_rejected() -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return ok(dict(bars=[], next_page_token=None))

    client = AlpacaBarsClient(
        "k",
        "s",
        adjustment="all",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert client.get_bars("SPY", Timeframe.DAY_1, START, END) == []
    assert seen[0].url.params["adjustment"] == "all"
    assert seen[0].url.params["feed"] == "iex"

    with pytest.raises(ValueError, match="adjustment"):
        AlpacaBarsClient("k", "s", adjustment="invalid")
