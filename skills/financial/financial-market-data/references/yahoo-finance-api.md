# Yahoo Finance v8 Chart API

## Endpoint
```
GET https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}?interval=1d&range=5d
```

## Query Parameters
- `TICKER`: Yahoo Finance ticker symbol. Use `^` prefix for indices (e.g. `^GSPC`, `^IXIC`, `^VIX`).
- `interval`: Data point interval. Common values: `1d`, `1wk`, `1mo`.
- `range`: Time window. Common values: `1d`, `5d`, `1mo`, `1y`.

## Required Headers
```
User-Agent: Mozilla/5.0
```
Yahoo may block requests without a browser-like User-Agent.

## Key Response Fields
- `chart.result[0].meta.regularMarketPrice` — current regular market price
- `chart.result[0].meta.previousClose` — previous session's close (can be `null`)
- `chart.result[0].indicators.quote[0].close` — array of historical close prices
- `chart.result[0].timestamp` — array of Unix timestamps for each price point

## Gotchas
- `previousClose` can be `null` in the metadata; fallback to the last non-null `close` in the chart data.
- Index tickers require the `^` prefix (e.g., `^GSPC`, `^IXIC`, `^VIX`, `^T` for -year Treasury note yield).
- The API is unauthenticated but is not officially supported. Use with caution in production.
- Rate limits are not published; cache aggressively if using heavily.
