# Official source context

For API Support or any questions email: support@unusualwhales.com

Documentation for the official [UnusualWhales](https://unusualwhales.com) api

## Startup Tier
Building a product on our data? Get started immediately with our self-serve Startup tier at $750/mo — 500 req/min, 80K daily requests, 90-day lookback, and commercial use included. Annual plan available at $7,500/yr (2 months free) with 1,000 req/min and 10 concurrent requests for market-open bursts. [Start building →](https://unusualwhales.com/checkout?plan=enterprise_startup&interval=monthly)

Need Kafka streaming? Our Startup + Kafka tier at $3,000/mo adds real-time Kafka cluster access. Annual plan available at $30,000/yr (2 months free) with the same 1,000 req/min burst allowance. [Start building →](https://unusualwhales.com/checkout?plan=enterprise_startup_kafka&interval=monthly)

## Enterprise/Professional Subscribers
For custom enterprise pricing, redistribution licenses, or bespoke solutions, email [oskar@unusualwhales.com, enterprise@unusualwhales.com or nastja.petrovic@unusualwhales.com](mailto:oskar@unusualwhales.com?cc=enterprise@unusualwhales.com,nastja.petrovic@unusualwhales.com).

## Changelog

# 2026.09.12
- Added a new websocket channel [`ta_1d_live:{TICKER}`](https://api.unusualwhales.com/docs/operations/PublicApi.SocketController.ta_1d_live). The channel streams technical-analysis indicator values (moving averages, RSI, MACD, Bollinger bands, ADX, Aroon, ATR, CCI, MFI, OBV, stochastics and Williams %R) computed on daily candles for one ticker. During regular trading hours it resends the day that is still forming as the price moves, so the newest message for a `date` replaces the ones before it. An indicator reads as `null` until enough daily history exists to compute it. The `1d` in the name is the candle interval and `live` means the values track the open session.

# 2026.09.04
- Added new websocket channels [`quotes` and `quotes:{TICKER}`](https://api.unusualwhales.com/docs/operations/PublicApi.SocketController.quotes). They stream the live best bid and ask - for every ticker at once, or for a single ticker - and are the live counterpart of [`/stock/:ticker/quote`](https://api.unusualwhales.com/docs/operations/PublicApi.StockQuoteController.show).

# 2026.09.01
- Added a global [`greeks`](https://api.unusualwhales.com/docs/operations/PublicApi.SocketController.greeks) websocket channel. It streams the same per-contract option greeks as `greeks:<TICKER>`, but for every underlying at once. This is a high volume firehose - prefer the per-ticker channel unless you need the full tape.

# 2026.08.30
- MCP now advertises build guidance: `instructions` on initialize; builder prompts `build_dashboard_app`, `build_confluence_alert`, `build_trading_bot`, `build_data_stream`, `start_from_example`, and `setup_api_project`; tools `get_build_recipe` and `get_api_examples` (scripts from [https://github.com/unusual-whales/api-examples](https://github.com/unusual-whales/api-examples)); and `resources/list` / `resources/templates/list` / `resources/read` for playbooks and example files.

# 2026.08.28
- Added a new websocket channel [`risk_reversal_skew`](https://api.unusualwhales.com/docs/operations/PublicApi.SocketController.risk_reversal_skew). The channel streams live 25- and 10-delta risk reversal skew (put implied volatility minus call implied volatility) per expiry across every ticker, the live counterpart of [`/stock/:ticker/historical-risk-reversal-skew`](https://api.unusualwhales.com/docs/operations/PublicApi.TickerController.historical_risk_reversal_skew). The channel is global only; there is no per-ticker variant.

# 2026.08.22
- Updated [`/stock/:ticker/gex-levels`](https://api.unusualwhales.com/docs/operations/PublicApi.TickerController.gex_levels) to derive its levels from spot directionalized volume — instead of a cumulative total over the static open-interest snapshot.
- Added `date`, `time`, `source`, and `nearby_flips` to the [`/stock/:ticker/gex-levels`](https://api.unusualwhales.com/docs/operations/PublicApi.TickerController.gex_levels) response. `nearby_flips` lists the five zero-gamma crossings nearest spot, ordered by distance from it. `time` is when the underlying exposure snapshot was calculated.

# 2026.08.21
- Added new websocket channels [`interpolated_iv` and `interpolated_iv:TICKER`](https://api.unusualwhales.com/docs/operations/PublicApi.SocketController.interpolated_iv). The channels stream interpolated implied volatility and expected moves at fixed horizons (1-365 trading days), the live counterpart of [`/stock/:ticker/interpolated-iv`](https://api.unusualwhales.com/docs/operations/PublicApi.TickerController.interpolated_iv).
- Added new websocket channels [`iv_term_structure` and `iv_term_structure:TICKER`](https://api.unusualwhales.com/docs/operations/PublicApi.SocketController.iv_term_structure). The channels stream ATM implied volatility and expected moves per real option expiry — the raw entries behind `interpolated_iv` — the live counterpart of [`/stock/:ticker/volatility/term-structure`](https://api.unusualwhales.com/docs/operations/PublicApi.TickerController.implied_volatility_term_structure).

# 2026.04.30
Added a new advanced-tier endpoint group. All routes below require API Advanced, Enterprise Startup, Enterprise Startup + Kafka, or Enterprise tier.

### Company fundamentals
- Added [`/companies/:ticker/profile`](https://api.unusualwhales.com/docs/operations/PublicApi.CompaniesController.profile) for sector, industry, market cap, P/E, EPS, dividend yield, analyst targets, 52-week range, moving averages, and the full analyst rating breakdown.
- Added [`/companies/:ticker/dividends`](https://api.unusualwhales.com/docs/operations/PublicApi.CompaniesController.dividends) for historical dividend events.
- Added [`/companies/:ticker/splits`](https://api.unusualwhales.com/docs/operations/PublicApi.CompaniesController.splits) for historical stock-split events.
- Added [`/companies/:ticker/earnings-estimates`](https://api.unusualwhales.com/docs/operations/PublicApi.CompaniesController.earnings_estimates) for forward analyst earnings and revenue estimates by quarter and year.
- Added [`/companies/:ticker/transcripts/:quarter`](https://api.unusualwhales.com/docs/operations/PublicApi.CompaniesController.transcript) for earnings-call transcripts with speakers, statements, and per-statement sentiment.
- Added [`/companies/listings`](https://api.unusualwhales.com/docs/operations/PublicApi.IntelController.listings) for the master list of US-traded securities (active or delisted).

### Macro
- Added [`/commodities/:name`](https://api.unusualwhales.com/docs/operations/PublicApi.CommoditiesController.show) for long-running price series across WTI, Brent, natural gas, copper, aluminum, wheat, corn, cotton, sugar, coffee, and the global commodities index.
- Added [`/economy/:indicator`](https://api.unusualwhales.com/docs/operations/PublicApi.EconomyController.show) for US economic indicator series (GDP, GDP per capita, treasury yield, fed funds rate, CPI, inflation, retail sales, durables, unemployment, payrolls).

### Forex
- Added [`/forex/rate`](https://api.unusualwhales.com/docs/operations/PublicApi.ForexController.rate) for live FX spot rates with bid and ask.
- Added [`/forex/intraday`](https://api.unusualwhales.com/docs/operations/PublicApi.ForexController.intraday) for 1min through 60min FX OHLC bars.
- Added [`/forex/history`](https://api.unusualwhales.com/docs/operations/PublicApi.ForexController.history) for daily, weekly, and monthly FX OHLC bars.

### Digital currencies
- Added [`/digital-currencies/intraday`](https://api.unusualwhales.com/docs/operations/PublicApi.DigitalCurrenciesController.intraday) for intraday OHLC bars priced against a fiat market.
- Added [`/digital-currencies/history`](https://api.unusualwhales.com/docs/operations/PublicApi.DigitalCurrenciesController.history) for daily, weekly, and monthly OHLC bars.

### Market intel and analytics
- Added [`/market/movers`](https://api.unusualwhales.com/docs/operations/PublicApi.IntelController.movers) for pre-ranked top gainers, top losers, and most actively traded US tickers.
- Added [`/calendar/ipo`](https://api.unusualwhales.com/docs/operations/PublicApi.IntelController.ipo_calendar) for upcoming IPOs over the next 3 months.
- Added [`/analytics/window`](https://api.unusualwhales.com/docs/operations/PublicApi.IntelController.analytics_window) for fixed-window statistical analytics across baskets of tickers (mean, stddev, correlation, drawdown, autocorrelation, covariance, and more).
- Added [`/analytics/sliding`](https://api.unusualwhales.com/docs/operations/PublicApi.IntelController.analytics_sliding) for sliding-window statistical analytics.

### Congressional unusual trades (scope `unusual-trades`)
- Added [`/congress/unusual-trades`](https://api.unusualwhales.com/docs/operations/PublicApi.UnusualTradesController.recent) for unusual congressional trades filtered by reason tag (committee_conflict, first_person_to_trade, low_marketcap, unusual_industry, unusually_large_trade, fec_donation_conflict).
- Added [`/congress/unusual-trades/by-tickers`](https://api.unusualwhales.com/docs/operations/PublicApi.UnusualTradesController.by_tickers) with ticker, transaction type, date range, and politician filters.
- Added [`/congress/unusual-trades/chart-data`](https://api.unusualwhales.com/docs/operations/PublicApi.UnusualTradesController.chart_data) returning trade points with SPY benchmark closes.
- Added [`/congress/unusual-trades/stats`](https://api.unusualwhales.com/docs/operations/PublicApi.UnusualTradesController.stats) for aggregate overview statistics.

### Private markets (scope `private-markets`)
- Added [`/private-markets/companies`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.companies) for the full Nasdaq Private Markets company list with sector and name filters.
- Added [`/private-markets/companies/:npm_ticker`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.company_profile) for the company profile with latest price, total funding, and investor count.
- Added [`/private-markets/companies/:npm_ticker/funding`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.funding) for funding round history.
- Added [`/private-markets/companies/:npm_ticker/investors`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.investors) for disclosed investors.
- Added [`/private-markets/companies/:npm_ticker/management`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.management) for disclosed leadership.
- Added [`/private-markets/companies/:npm_ticker/pricing`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.pricing) for historical implied per-share pricing.
- Added [`/private-markets/investors`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.top_investors) for top investors ranked by distinct company count.
- Added [`/private-markets/investors/:name`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.investor_profile) for an investor's portfolio.
- Added [`/private-markets/search`](https://api.unusualwhales.com/docs/operations/PublicApi.PrivateMarketsController.search) for substring search across companies and investors.

### MCP
- Added 5 premium MCP catalogs covering the new endpoints: `uw_companies_extras`, `uw_macro`, `uw_forex`, `uw_digital_currencies`, `uw_intel`. Plus `uw_unusual_trades` and `uw_private_markets` for the scope-gated catalogs above.
- Premium MCP catalogs and individual premium commands (`uw_stock.ownership`, `uw_flow.full_tape`, `uw_politicians`) are now hidden by default. Operators opt in via `UW_ENABLE_PREMIUM_TOOLS=true` (all on) or `UW_PREMIUM_TOOLS=uw_companies_extras,uw_macro,...` (per-tool allowlist supporting `<catalog_id>` or `<catalog_id>.<command>` form).

# 2026.04.29
- Added MCP tool `get_short_volume_ratio_by_exchange` for [`/shorts/:ticker/volumes-by-exchange`](https://api.unusualwhales.com/docs/operations/PublicApi.ShortController.short_volume_by_exchange) data.
- Added MCP tool `get_short_volume_ratio_by_ticker` for [`/shorts/:ticker/volume-and-ratio`](https://api.unusualwhales.com/docs/operations/PublicApi.ShortController.short_volume_and_ratio) data.
- Added MCP tool `get_short_screener` for [`/short_screener`](https://api.unusualwhales.com/docs/operations/PublicApi.ShortController.short_screener)
- Added MCP tool `get_short_data_by_ticker` for [`/shorts/:ticker/data`](https://api.unusualwhales.com/docs/operations/PublicApi.ShortController.short_data)

# 2026.04.14
- Enhanced MCP [`/api/mcp`](https://api.unusualwhales.com/docs) `tools/call` validation to reject unsupported arguments, missing required arguments, and invalid enum values before tool execution.
- MCP tool errors now include retry guidance telling clients to inspect `tools/list` `inputSchema` and retry with supported arguments.

# 2026.03.02
- Added authenticated MCP endpoint [`/api/mcp`](https://api.unusualwhales.com/docs) to expose existing AI tools to API subscribers using the same `Authorization: Bearer <API_TOKEN>` flow.
- Supports MCP `initialize`, `tools/list`, and `tools/call` methods backed by the existing internal tool registry and execution pipeline.

# 2026.01.20
- Updated interest-float endpoint with new version and deprecated old version
- [`/shorts/:ticker/interest-float/v2`](https://api.unusualwhales.com/docs#/operations/PublicApi.ShortController.short_interest_and_float_v2)
- Added interest-float search screener endpoint
- [`/short_screener`](https://api.unusualwhales.com/docs#/operations/PublicApi.ShortController.short_screener)

# 2025.09.23

- Added new websocket channels [`lit_trades`](https://api.unusualwhales.com/docs#/operations/PublicApi.SocketController.lit_trades) and [`off_lit_trades`](https://api.unusualwhales.com/docs#/operations/PublicApi.SocketController.off_lit_trades) to stream live lit (exchange-based) and off-lit (dark pool) trades respectively.

# 2025.09.22

- Added `newer_than` and `older_than` time filtering parameters to [`/alerts`](https://api.unusualwhales.com/docs#/operations/PublicApi.AlertsController.alerts) endpoint with 14-day maximum lookback period for custom alerts queries

# 2025.08.20

- Added [`/market/top-net-impact`](https://api.unusualwhales.com/docs#/operations/PublicApi.MarketController.top_net_impact) endpoint to get the top tickers by net premium (split between bullish and bearish). Supports filtering by `issue_types[]`, `date`, and `limit` (default 20, max 100).

# 2025.06.18

- Added [`/market/:sector/sector-tide`](https://api.unusualwhales.com/docs#/operations/PublicApi.MarketController.sec_indst) endpoint to get the market tide for a specific sector

# 2025.06.02

- Added [`/stock/:ticker/interpolated-iv`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.interpolated_iv) endpoint to get the interpolated iv for various days


# 2025.05.29

- Added [`/option-contract/:id/volume-profile`](https://api.unusualwhales.com/docs#/operations/PublicApi.OptionContractController.volume_profile) endpoint to get the volume profile of an option contract (volume by fill price)

# 2025.05.23

- Added [`/option-contract/:id/intraday`](https://api.unusualwhales.com/docs#/operations/PublicApi.OptionContractController.intraday) endpoint to get the volume, premium & OHLC for a contract in 1min ticks for a given trading day

# 2025.05.07

- Added `prev_close_price` field to [`/stock/:ticker/stock-state`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.last_stock_state) endpoint to provide the previous close price.

# 2025.04.30

- Enhanced [`/option-trades/full-tape/{date}`](https://api.unusualwhales.com/docs#/operations/PublicApi.OptionTradeController.full_tape) to allow users with `websocket` scope to access the last two trading days of data

# 2025.04.23

- Added [`/net-flow/expiry`](https://api.unusualwhales.com/docs#/operations/PublicApi.NetFlowController.expiry) endpoint to track net premium flow by tide type, moneyness, and expiration categories. This powers charts like those found on the [zero-DTE dashboard](https://unusualwhales.com/zero-dte)

# 2025.04.08

- Enhanced [`/market/correlations`](https://api.unusualwhales.com/docs#/operations/PublicApi.MarketController.correlations) endpoint with new date filtering options: `start_date` and `end_date` parameters to specify custom date ranges, complementing the existing `interval` parameter

# 2025.03.23
- Updated [`/stock/{ticker}/net-prem-ticks`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.net_prem_ticks) endpoint to
include `call_volume`, `put_volume`, `call_volume_bid_side`,  `put_volume_bid_side`, `call_volume_ask_side`,  `put_volume_ask_side` & `net_delta`.

# 2025.03.10

- Added [`/news/headlines`](https://api.unusualwhales.com/docs#/operations/PublicApi.NewsController.headlines) endpoint to access financial news headlines with filtering capabilities
- Added Shorts API endpoints:
  - [`/shorts/:ticker/data`](https://api.unusualwhales.com/docs#/operations/PublicApi.ShortController.short_data)
  - [`/shorts/:ticker/volumes-by-exchange`](https://api.unusualwhales.com/docs#/operations/PublicApi.ShortController.short_volume_by_exchange)
  - [`/shorts/:ticker/ftds`](https://api.unusualwhales.com/docs#/operations/PublicApi.ShortController.failures_to_deliver)
  - [`/shorts/:ticker/interest-float`](https://api.unusualwhales.com/docs#/operations/PublicApi.ShortController.short_interest_and_float)
  - [`/shorts/:ticker/volume-and-ratio`](https://api.unusualwhales.com/docs#/operations/PublicApi.ShortController.short_volume_and_ratio)

# 2025.02.19

- The endpoint [`/stock/:ticker/spot-exposures/:expiry/strike`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.spot_exposures_by_strike_expiry) has been deprecated and been replaced by [`/stock/:ticker/spot-exposures/expiry-strike`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.spot_exposures_by_strike_expiry_v2)

To migrate over replace all your `/api/stock/:ticker/spot-exposures/:expiry/strike` calls with `/api/stock/:ticker/spot-exposures/expiry-strike?expirations[]=expiry`

# 2025.02.13
- The endpoint `/congress/recent-reports` has been removed as it returns the same data as `/congress/recent-trades`.

# 2025.02.05
- Enhanced [`/market/fda-calendar`](https://api.unusualwhales.com/docs#/operations/PublicApi.MarketController.fda_calendar) with better FDA data, additional fields (notes, outcomes, sources), and filtering by company metrics

# 2025.02.03
- Updated dark pool/off lit endpoints to allow filtering for size, premium & consolidated volume

# 2025.01.22
- Added [`gex_strike_expiry:<TICKER>`](https://api.unusualwhales.com/docs#/operations/PublicApi.SocketController.gex) channel to the websocket
- Added `call_option_symbol` & `put_option_symbol` to [`/stock/{ticker}/greeks`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.greeks)

# 2025.01.16
- Added [`/stock/:ticker/spot-exposures/:expiry/strike`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.spot_exposures_by_strike_expiry)

# 2024.12.11
- Added [`/alerts/configuration`](https://api.unusualwhales.com/docs#/operations/PublicApi.AlertsController.configs)
- Added [`/alerts`](https://api.unusualwhales.com/docs#/operations/PublicApi.AlertsController.alerts)

This allows one to grab all the alerts that have been triggerd for any alert that one has configured. With an existing unusualwhales account you can view and configure alerts directly on the [website](https://unusualwhales.com/custom-alerts)

# 2024.12.02
- Added [`/stock/:ticker/oi-per-strike`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.oi_per_strike)
- Added [`/stock/:ticker/oi-per-expiry`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.oi_per_expiry)

# 2024.11.19
- Improved all earnings endpoint

# 2024.11.09
- Added `perc_of_total` & `perc_of_share_value` to [`/institution/:name/holdings`](https://api.unusualwhales.com/docs#/operations/PublicApi.InstitutionController.holdings)

# 2024.10.30
- Added [`/stock/:ticker/nope`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.nope)

# 2024.10.28
- Added [`/group-flow/:flow_group/greek-flow`](https://api.unusualwhales.com/docs#/operations/PublicApi.GroupFlowController.greek_flow)
- Added [`/group-flow/:flow_group/greek-flow/:expiry`](https://api.unusualwhales.com/docs#/operations/PublicApi.GroupFlowController.greek_flow_expiry)
- Added [`/stock/:ticker/greek-flow`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.greek_flow)
- Added [`/stock/:ticker/greek-flow/:epxiry`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.greek_flow_expiry)

# 2024.10.16
- Added etf inflow & outflow endpoint [`/etfs/:ticker/in_outflow`](PublicApi.EtfController.in_outflow)

# 2024.10.15
- Added institutional latest filings endpoint [`/institution/latest_filings`](PublicApi.InstitutionController.latest_filings)
- Added institutional ownership endpoint [`/institution/:ticker/ownership`](PublicApi.InstitutionController.ownership)

# 2024.10.14
- Added 2 new fields: `days_of_oi_increases` & `days_of_vol_greater_than_oi` to [`/market/oi-change`](PublicApi.MarketController.oi_change)
```
days_of_oi_increases: The number of consecutive days that the open interest has increased for this contract. If on any day the open interest decreases or does not change the count will reset.

days_of_vol_greater_than_oi: The number of consecutive days that the volume has been greater than the open interest for this contract. If on any day the volume is less than or equal to the open interest the count will reset.
```

<br/>

# 2024.10.10
- Added institutional activity endpoint [`/institution/:name/activity`](PublicApi.InstitutionController.activity)

# 2024.10.09
- Added institutional list endpoint [`institutions`](PublicApi.InstitutionController.list)
- Added institutional holdings endpoint [`/institution/:name/holdings`](PublicApi.InstitutionController.holdings)
- Added institutional sector exposure endpoint [`/institution/:name/sectors`](PublicApi.InstitutionController.sectors)

# 2024.08.01
- Added new flow per strike intraday endpoint [`/stock/:ticker/flow-per-strike-intraday`](PublicApi.TickerController.flow_per_strike_intraday)

# 2024.07.11
- Added new correlation endpoint [`/market/correlations?tickers=SPY,QQQ,JPM,BAC`](PublicApi.MarketController.correlations)

# 2024.05.30
- Added the ability to filter [`/darkpool/:ticker`](PublicApi.DarkPoolController.darkpool_ticker) by timestamps through the two new query parameters `older_than` and `newer_than`

# 2024.05.21
- Added directionalized volume fields to [`/stock/:ticker/spot-exposures`](PublicApi.TickerController.spot_exposures_one_minute) and [`/stock/:ticker/spot-exposures/strike`](PublicApi.TickerController.spot_exposures_by_strike)

# 2024.05.17
- Added the channels `gex:TICKER` & `gex_strike:TICKER` to the [websocket](https://api.unusualwhales.com/docs#/operations/PublicApi.SocketController.channels)

# 2024.05.07
- Added the ability to filter [`/option-trades/flow-alerts`](PublicApi.OptionTradeController.flow_alerts) by timestamps through the two new query parameters `older_than` and `newer_than`

# 2024.05.06
- Added endpoint [`/stock/:ticker/stock-state`](PublicApi.TickerController.last_stock_state) to retrieve the last stock price & volume
- Added endpoint [`/stock/:ticker/volatility/realized`](PublicApi.TickerController.realized_volatility) to retrieve a stock's realized volatility

# 2024.05.03
- The data returned by /stock/:ticker/option-contracts has been limited to 500 results

# 2024.05.02
- Added endpoint [`/market/:ticker/etf-tide`](PublicApi.MarketController.etf_tide)

# 2024.05.01
- Added endpoint [`/stock/:ticker/spot-exposures/strike`](PublicApi.TickerController.spot_exposures_by_strike)
- Added new channel [`price:TICKER`](https://api.unusualwhales.com/docs#/operations/PublicApi.SocketController.channels) to the websocket. The channel will push live price updates for the given ticker.

# 2024.04.25
- Added endpoint [`/stock/:ticker/greek-exposure/strike`](PublicApi.TickerController.greek_exposure_by_strike)
- Added endpoint [`/stock/:ticker/greek-exposure/expiry`](PublicApi.TickerController.greek_exposure_by_expiry)
- Added endpoint [`/stock/:ticker/greek-exposure/strike-expiry`](PublicApi.TickerController.greek_exposure_by_strike_expiry)

# 2024.03.28
- Fixed field name volatility -> risk_reversal for endpoint [`/stock/:ticker/historical_risk_reversal_skew`](PublicApi.TickerController.historical_risk_reversal_skew)

# 2024.03.26
- Added endpoint [`/stock/:ticker/greeks`](PublicApi.TickerController.greeks)
- Added endpoint [`/stock/:ticker/historical_risk_reversal_skew`](PublicApi.TickerController.historical_risk_reversal_skew)

# 2024.03.23
- BREAKING CHANGE:
Previously `/option-contract/:id/flow` would return the data as a json list. This has been now changed so that the endpoint
returns the data in the format `{"data": [], "date": "2024-03-22"}`. Secondly, the endpoint will now only return data for
a single trading day.

# 2024.03.06
- Added endpoint [`/option-trades/flow-alerts`](PublicApi.OptionTradeController.flow_alerts)
- Added flow-alerts streaming to the WebSocket.

# 2024.03.04
- Added endpoint [`/stock/:ticker/max-pain`](https://api.unusualwhales.com/docs#/operations/PublicApi.TickerController.max_pain)

# 2024.02.16
- Added new endpoint section [`Seasonality`](https://api.unusualwhales.com/docs#/operations/PublicApi.SeasonalityController.market_seasonality) with new endpoints:
    - [`/seasonality/market`](https://api.unusualwhales.com/docs#/operations/PublicApi.SeasonalityController.market_seasonality)
    - [`/seasonality/:month/performers`](https://api.unusualwhales.com/docs#/operations/PublicApi.SeasonalityController.month_performers)
    - [`/seasonality/:ticker/monthly`](https://api.unusualwhales.com/docs#/operations/PublicApi.SeasonalityController.monthly)
    - [`/seasonality/:ticker/year-month`](https://api.unusualwhales.com/docs#/operations/PublicApi.SeasonalityController.year_month)

# 2024.02.07
- Added endpoints [`/stock/:ticker/expiry-breakdown`](https://api.unusualwhales.com/docs#/operations/PublicApi.OptionContractController.expiry_breakdown) & [`/stock/:ticker/option-contracts`](https://api.unusualwhales.com/docs#/operations/PublicApi.OptionContractController.option_contracts). These 2 endpoints allow access to the data located here: [https://unusualwhales.com/stock/AAPL/option-chains](https://unusualwhales.com/stock/AAPL/option-chains)


## Servers and security schemes
```json
{
  "servers": [
    {
      "url": "https://api.unusualwhales.com",
      "variables": {}
    }
  ],
  "security": [
    {
      "authorization": []
    }
  ],
  "schemes": {
    "authorization": {
      "scheme": "bearer",
      "type": "http"
    }
  }
}
```
