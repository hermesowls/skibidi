# CoinGecko v3 Simple Price API

## Endpoint
```
GET https://api.coingecko.com/api/v3/simple/price?ids={id}&vs_currencies=usd&include_24hr_change=true
```

## Query Parameters
- `ids`: Comma-separated list of CoinGecko coin IDs (e.g. `bitcoin`, `ethereum`, `solana`).
  - **Note**: these are NOT ticker symbols. Use CoinGecko's `/coins/list` endpoint to map symbols to IDs.
- `vs_currencies`: Target fiat/crypto (e.g. `usd`, `eur`, `btc`).
- `include_24hr_change`: `true` to include 24-hour percentage change.

## Required Headers
None required, but a `User-Agent: Mozilla/5.0` is recommended.

## Key Response Fields
- `{id}.usd` — current price in USD
- `{id}.usd_24h_change` — 24-hour percentage change as a float (e.g. `0.87` for +0.87%)

## Gotchas
- Free tier rate limit is approximately 10-50 requests per minute.
- CoinGecko IDs are case-sensitive. `bitcoin` works, `Bitcoin` does not.
- Invalid IDs return an empty object, not an error.
- 429 errors indicate rate limiting; add a small `time.sleep(1)` between requests.
