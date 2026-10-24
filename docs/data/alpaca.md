# Alpaca historical bars adapter

`backend/app/data/alpaca.py` — `AlpacaBarsClient.get_bars(symbol, timeframe, start, end)`
returns normalized `Bar` objects for `1Day` and `1Hour` (free plan, `feed=iex`,
`adjustment=raw`). It follows `next_page_token` pagination and retries 429/5xx/transport
errors with bounded exponential backoff (default 5 retries, 0.5s base, 30s cap).

Read-only: only `GET /v2/stocks/<symbol>/bars` on the market-data host is used.
Config (`.env`): `DATA_API_KEY`, `DATA_API_SECRET`, `MARKET_DATA_URL`
(default `https://data.alpaca.markets`). The URL is checked against
`LIVE_ENDPOINT_DENYLIST` both in the client and at startup. Bar timestamps are bar
start times in UTC; prices are parsed straight to `Decimal`.

Out of scope: caching, streaming, gap detection. IEX volume is a subset of consolidated volume.
