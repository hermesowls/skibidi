# Complete operation catalog

237 HTTP operations under 236 paths; 214 REST and 23 websocket documentation entries. MCP wrappers are separate.

Every operation appears exactly once below, grouped by its first tag. All tags remain in inventory. Category references retain full resolved operations including response schemas; examples originate in the spec and are NOT live results.

## Futures

Full definitions: [categories/futures.md](categories/futures.md)

- `GET /api/futures/contracts` — Futures Contracts
- `GET /api/futures/display_factors` — Futures Display Factors
- `GET /api/futures/display_factors/{security_id}` — Futures Display Factor
- `GET /api/futures/flow` — Futures Flow
- `GET /api/futures/{contract}/candles` — Futures Candles (OHLCV)
- `GET /api/futures/{contract}/stats` — Futures Session Stats
- `GET /api/futures/{contract}/trades` — Futures Trades (Time & Sales)
## Gex/Greeks

Full definitions: [categories/gex-greeks.md](categories/gex-greeks.md)

- `GET /api/stock/{ticker}/gex-levels` — GEX Levels
- `GET /api/stock/{ticker}/greek-exposure` — Greek Exposure
- `GET /api/stock/{ticker}/greek-exposure/expiry` — Greek Exposure By Expiry
- `GET /api/stock/{ticker}/greek-exposure/strike` — Greek Exposure By Strike
- `GET /api/stock/{ticker}/greek-exposure/strike-expiry` — Greek Exposure By Strike And Expiry
- `GET /api/stock/{ticker}/greek-flow` — Greek flow
- `GET /api/stock/{ticker}/greek-flow/{expiry}` — Greek flow by expiry
- `GET /api/stock/{ticker}/spot-exposures` — Spot GEX exposures per 1min
- `GET /api/stock/{ticker}/spot-exposures/expiry-strike` — Spot GEX exposures by strike & expiry
- `GET /api/stock/{ticker}/spot-exposures/strike` — Spot GEX exposures by strike
- `GET /api/stock/{ticker}/spot-exposures/{expiry}/strike` — Spot GEX exposures by strike & expiry (Deprecated)
## alerts

Full definitions: [categories/alerts.md](categories/alerts.md)

- `GET /api/alerts` — Alerts
- `GET /api/alerts/configuration` — Alert configurations
- `GET /api/alerts/filters` — Alert filters
- `GET /api/alerts/query/grammar` — Query grammar
- `POST /api/alerts/configuration` — Create alert configuration
## commodities

Full definitions: [categories/commodities.md](categories/commodities.md)

- `GET /api/commodities/{name}` — Commodity Series
## companies

Full definitions: [categories/companies.md](categories/companies.md)

- `GET /api/companies/{ticker}/dividends` — Company Dividends
- `GET /api/companies/{ticker}/earnings-estimates` — Forward Earnings Estimates
- `GET /api/companies/{ticker}/profile` — Company Profile
- `GET /api/companies/{ticker}/splits` — Company Stock Splits
- `GET /api/companies/{ticker}/transcripts/{quarter}` — Earnings Call Transcript
## congress

Full definitions: [categories/congress.md](categories/congress.md)

- `GET /api/congress/congress-trader` — Recent Reports By Trader
- `GET /api/congress/late-reports` — Recent Late Reports
- `GET /api/congress/politicians` — List of Politicians with Trade Data
- `GET /api/congress/recent-trades` — Recent Congress Trades
## crypto

Full definitions: [categories/crypto.md](categories/crypto.md)

- `GET /api/crypto/candles/{interval}` — Get Crypto API OHLC Candles.
- `GET /api/crypto/list_tokens` — Get a list of tokens.
- `GET /api/crypto/token/{token}` — Get token metadata.
- `GET /api/crypto/trades` — Get a list of trades.
- `GET /api/crypto/whale-transactions` — Crypto Whale Transactions
- `GET /api/crypto/whales/recent` — Recent Crypto Whale Trades
- `GET /api/crypto/{pair}/ohlc/{candle_size}` — Crypto OHLC Candles
- `GET /api/crypto/{pair}/state` — Crypto Pair State
## darkpool

Full definitions: [categories/darkpool.md](categories/darkpool.md)

- `GET /api/darkpool/recent` — Recent Darkpool Trades
- `GET /api/darkpool/{ticker}` — Ticker Darkpool Trades
- `GET /api/darkpool/{ticker}/price-levels` — Darkpool Price Levels
## digital_currencies

Full definitions: [categories/digital-currencies.md](categories/digital-currencies.md)

- `GET /api/digital-currencies/history` — Digital Currency Historical Series
- `GET /api/digital-currencies/intraday` — Digital Currency Intraday Series
## earnings

Full definitions: [categories/earnings.md](categories/earnings.md)

- `GET /api/earnings/afterhours` — Afterhours
- `GET /api/earnings/premarket` — Premarket
- `GET /api/earnings/{ticker}` — Historical Ticker Earnings
## economy

Full definitions: [categories/economy.md](categories/economy.md)

- `GET /api/economy/{indicator}` — Economic Indicator
## etfs

Full definitions: [categories/etfs.md](categories/etfs.md)

- `GET /api/etfs/{ticker}/exposure` — Exposure
- `GET /api/etfs/{ticker}/holdings` — Holdings
- `GET /api/etfs/{ticker}/in-outflow` — Inflow & Outflow
- `GET /api/etfs/{ticker}/info` — Information
- `GET /api/etfs/{ticker}/weights` — Sector & Country weights
## forex

Full definitions: [categories/forex.md](categories/forex.md)

- `GET /api/forex/history` — FX Historical Series
- `GET /api/forex/intraday` — FX Intraday Series
- `GET /api/forex/rate` — FX Spot Rate
## group_flow

Full definitions: [categories/group-flow.md](categories/group-flow.md)

- `GET /api/group-flow/{flow_group}/greek-flow` — Greek flow
- `GET /api/group-flow/{flow_group}/greek-flow/{expiry}` — Greek flow by expiry
## insiders

Full definitions: [categories/insiders.md](categories/insiders.md)

- `GET /api/insider/transactions` — Transactions
- `GET /api/insider/{sector}/sector-flow` — Sector Flow
- `GET /api/insider/{ticker}` — Insiders
- `GET /api/insider/{ticker}/ticker-flow` — Ticker Flow
## institution

Full definitions: [categories/institution.md](categories/institution.md)

- `GET /api/institution/{name}/activity` — Institutional Activity (Deprecated)
- `GET /api/institution/{name}/activity/v2` — Institutional Activity
- `GET /api/institution/{name}/holdings` — Institutional Holdings
- `GET /api/institution/{name}/sectors` — Sector Exposure
- `GET /api/institution/{ticker}/ownership` — Institutional Ownership
- `GET /api/institutions` — List of Institutions
- `GET /api/institutions/latest_filings` — Latest Filings
## intel

Full definitions: [categories/intel.md](categories/intel.md)

- `GET /api/analytics/sliding` — Sliding-Window Analytics
- `GET /api/analytics/window` — Fixed-Window Analytics
- `GET /api/calendar/ipo` — IPO Calendar
- `GET /api/companies/listings` — Active or Delisted Securities
- `GET /api/market/movers` — Top Movers
## lit-flow

Full definitions: [categories/lit-flow.md](categories/lit-flow.md)

- `GET /api/lit-flow/recent` — Recent Lit Flow Trades
- `GET /api/lit-flow/{ticker}` — Ticker Lit Flow Trades
## market

Full definitions: [categories/market.md](categories/market.md)

- `GET /api/market/correlations` — Correlations
- `GET /api/market/daily-report` — Daily Market Report
- `GET /api/market/economic-calendar` — Economic calendar
- `GET /api/market/fda-calendar` — FDA Calendar
- `GET /api/market/insider-buy-sells` — Total Insider Buy & Sells
- `GET /api/market/market-tide` — Market Tide
- `GET /api/market/oi-change` — OI Change
- `GET /api/market/sector-etfs` — Sector Etfs
- `GET /api/market/top-net-impact` — Top Net Impact
- `GET /api/market/total-options-volume` — Total Options Volume
- `GET /api/market/{sector}/sector-tide` — Sector Tide
- `GET /api/market/{ticker}/etf-tide` — ETF Tide
- `GET /api/net-flow/expiry` — Net Flow Expiry
## news

Full definitions: [categories/news.md](categories/news.md)

- `GET /api/news/headlines` — News Headlines
## option-contract

Full definitions: [categories/option-contract.md](categories/option-contract.md)

- `GET /api/option-contract/{id}/flow` — Flow Data
- `GET /api/option-contract/{id}/historic` — Historic Data
- `GET /api/option-contract/{id}/intraday` — Intraday Data
- `GET /api/option-contract/{id}/volume-profile` — Volume Profile
- `GET /api/stock/{ticker}/expiry-breakdown` — Expiry Breakdown
- `GET /api/stock/{ticker}/option-contracts` — Option contracts
- `GET /api/stock/{ticker}/option-stance` — Option Trade-Stance Ranking
## option-trade

Full definitions: [categories/option-trade.md](categories/option-trade.md)

- `GET /api/option-trades` — Option Trades
- `GET /api/option-trades/exchange-breakdown/{date}` — Exchange & Trade Code Breakdown
- `GET /api/option-trades/flow-alerts` — Flow Alerts
- `GET /api/option-trades/flow-alerts/{id}` — Flow Alert by ID
- `GET /api/option-trades/full-tape/{date}` — Full Tape
- `GET /api/option-trades/multi-leg` — Multi-Leg Option Trades
- `GET /api/option-trades/multi-leg/{id}/legs` — Multi-Leg Trade Legs
- `GET /api/option-trades/optionable-tickers` — Optionable Tickers
## options-pulse

Full definitions: [categories/options-pulse.md](categories/options-pulse.md)

- `GET /api/options-pulse/sectors` — Options Pulse by Sector/Industry
- `GET /api/options-pulse/top` — Options Pulse Scanner
- `GET /api/options-pulse/total` — Market-wide Options Pulse
- `GET /api/stock/{ticker}/options-pulse` — Options Pulse for a ticker
## politician_portfolios

Full definitions: [categories/politician-portfolios.md](categories/politician-portfolios.md)

- `GET /api/politician-portfolios/disclosures` — Annual Disclosures List
- `GET /api/politician-portfolios/holders/{ticker}` — Politician Portfolio Holders by Ticker
- `GET /api/politician-portfolios/people` — Politicians List
- `GET /api/politician-portfolios/recent_trades` — Politician Trades
- `GET /api/politician-portfolios/{politician_id}` — Politician Portfolios
## politics

Full definitions: [categories/politics.md](categories/politics.md)

- `GET /api/politics/fec/candidates` — Candidates with company-linked contributions
- `GET /api/politics/fec/companies` — Companies with political activity
- `GET /api/politics/fec/company/{ticker}/lobbying` — Company lobbying totals and issues
- `GET /api/politics/fec/company/{ticker}/people` — People associated with a company
- `GET /api/politics/fec/contributions` — Company political contributions
- `GET /api/politics/politician/trades` — Politician's trades
## potus

Full definitions: [categories/potus.md](categories/potus.md)

- `GET /api/potus/posts` — President's Posts
- `GET /api/potus/schedule` — President's Schedule
## predictions

Full definitions: [categories/predictions.md](categories/predictions.md)

- `GET /api/predictions/insiders` — Prediction Market Insiders
- `GET /api/predictions/market/{asset_id}` — Prediction Market Details
- `GET /api/predictions/market/{asset_id}/liquidity` — Prediction Market Liquidity
- `GET /api/predictions/market/{asset_id}/positions` — Prediction Market Positions
- `GET /api/predictions/search-users` — Search Prediction Market Users
- `GET /api/predictions/smart-money` — Prediction Smart Money
- `GET /api/predictions/unusual` — Unusual Prediction Markets
- `GET /api/predictions/user/{user_id}` — Prediction Market User
- `GET /api/predictions/whales` — Prediction Market Whales
## private_markets

Full definitions: [categories/private-markets.md](categories/private-markets.md)

- `GET /api/private-markets/companies` — List Private Markets Companies
- `GET /api/private-markets/companies/{npm_ticker}` — Private Markets Company Profile
- `GET /api/private-markets/companies/{npm_ticker}/funding` — Private Markets Funding Rounds
- `GET /api/private-markets/companies/{npm_ticker}/investors` — Private Markets Investors for Company
- `GET /api/private-markets/companies/{npm_ticker}/management` — Private Markets Management
- `GET /api/private-markets/companies/{npm_ticker}/pricing` — Private Markets Pricing History
- `GET /api/private-markets/investors` — Top Private Markets Investors
- `GET /api/private-markets/investors/{name}` — Private Markets Investor Profile
- `GET /api/private-markets/search` — Search Private Markets
## screener

Full definitions: [categories/screener.md](categories/screener.md)

- `GET /api/option-activity/unusual` — Unusual Options Activity
- `GET /api/screener/analysts` — Analyst Rating
- `GET /api/screener/option-contracts` — Hottest Chains
- `GET /api/screener/stocks` — Stock Screener
- `GET /api/screener/stocks/dsl` — Stock screener query language
## seasonality

Full definitions: [categories/seasonality.md](categories/seasonality.md)

- `GET /api/seasonality/market` — Market Seasonality
- `GET /api/seasonality/{month}/performers` — Month Performers
- `GET /api/seasonality/{ticker}/monthly` — Average return per month
- `GET /api/seasonality/{ticker}/year-month` — Price change per month per year
## short

Full definitions: [categories/short.md](categories/short.md)

- `GET /api/short_screener` — Short Screener
- `GET /api/shorts/{ticker}/data` — Short Data
- `GET /api/shorts/{ticker}/ftds` — Failures to Deliver
- `GET /api/shorts/{ticker}/interest-float` — V1 Short Interest and Float (Deprecated)
- `GET /api/shorts/{ticker}/interest-float/v2` — V2 Short Interest and Float
- `GET /api/shorts/{ticker}/volume-and-ratio` — Short Volume and Ratio
- `GET /api/shorts/{ticker}/volumes-by-exchange` — Short Volume By Exchange
## stock

Full definitions: [categories/stock.md](categories/stock.md)

- `GET /api/stock/{sector}/tickers` — Companies in Sector
- `GET /api/stock/{ticker}/atm-chains` — ATM Chains
- `GET /api/stock/{ticker}/balance-sheets` — Balance Sheets
- `GET /api/stock/{ticker}/cash-flows` — Cash Flow Statements
- `GET /api/stock/{ticker}/earnings` — Earnings History
- `GET /api/stock/{ticker}/financials` — Full Financials
- `GET /api/stock/{ticker}/flow-alerts` — Flow Alerts
- `GET /api/stock/{ticker}/flow-per-expiry` — Flow per expiry
- `GET /api/stock/{ticker}/flow-per-strike` — Flow per strike
- `GET /api/stock/{ticker}/flow-per-strike-intraday` — Flow per strike intraday
- `GET /api/stock/{ticker}/flow-recent` — Recent flows
- `GET /api/stock/{ticker}/fundamental-breakdown` — Fundamental Breakdown
- `GET /api/stock/{ticker}/greeks` — Greeks
- `GET /api/stock/{ticker}/historical-risk-reversal-skew` — Historical Risk Reversal Skew
- `GET /api/stock/{ticker}/income-statements` — Income Statements
- `GET /api/stock/{ticker}/info` — Information
- `GET /api/stock/{ticker}/insider-buy-sells` — Insider buy & sells
- `GET /api/stock/{ticker}/interpolated-iv` — Interpolated IV
- `GET /api/stock/{ticker}/iv-rank` — IV Rank
- `GET /api/stock/{ticker}/max-pain` — Max Pain
- `GET /api/stock/{ticker}/net-prem-ticks` — Call/Put Net/Vol Ticks
- `GET /api/stock/{ticker}/nope` — Nope
- `GET /api/stock/{ticker}/ohlc/{candle_size}` — OHLC
- `GET /api/stock/{ticker}/oi-change` — OI Change
- `GET /api/stock/{ticker}/oi-per-expiry` — OI per Expiry
- `GET /api/stock/{ticker}/oi-per-strike` — OI per Strike
- `GET /api/stock/{ticker}/option-chains` — Option Chains
- `GET /api/stock/{ticker}/option/stock-price-levels` — Option Price Levels
- `GET /api/stock/{ticker}/option/volume-oi-expiry` — Volume & OI per Expiry
- `GET /api/stock/{ticker}/options-volume` — Options Volume
- `GET /api/stock/{ticker}/ownership` — Ownership
- `GET /api/stock/{ticker}/quote` — Stock Quote
- `GET /api/stock/{ticker}/stock-state` — Stock State
- `GET /api/stock/{ticker}/stock-volume-price-levels` — Off/Lit Price Levels
- `GET /api/stock/{ticker}/technical-indicator/{function}` — Technical Indicator
- `GET /api/stock/{ticker}/unusualness` — Volume Unusualness
- `GET /api/stock/{ticker}/volatility/realized` — Realized Volatility
- `GET /api/stock/{ticker}/volatility/stats` — Volatility Statistics
- `GET /api/stock/{ticker}/volatility/term-structure` — Implied Volatility Term Structure
## stock-directory

Full definitions: [categories/stock-directory.md](categories/stock-directory.md)

- `GET /api/stock-directory/ticker-exchanges` — Ticker Exchange Mapping
## unusual_trades

Full definitions: [categories/unusual-trades.md](categories/unusual-trades.md)

- `GET /api/congress/unusual-trades` — Unusual Congressional Trades
- `GET /api/congress/unusual-trades/by-tickers` — Unusual Trades by Ticker
- `GET /api/congress/unusual-trades/chart-data` — Unusual Trades Chart Data
- `GET /api/congress/unusual-trades/stats` — Unusual Trades Aggregate Stats
## volatility

Full definitions: [categories/volatility.md](categories/volatility.md)

- `GET /api/stock/{ticker}/interpolated-iv/distribution` — Interpolated IV Distribution
- `GET /api/stock/{ticker}/volatility/anomaly` — Volatility Anomaly Score
- `GET /api/stock/{ticker}/volatility/character` — Volatility Character
- `GET /api/stock/{ticker}/volatility/option-sentiment` — Options Positioning Sentiment
- `GET /api/stock/{ticker}/volatility/realized/windows` — Realized Volatility Windows
- `GET /api/stock/{ticker}/volatility/term-structure/distribution` — Implied Volatility Term Structure Distribution
- `GET /api/stock/{ticker}/volatility/variance-risk-premium` — Variance Risk Premium
- `GET /api/stock/{ticker}/volatility/variance-risk-premium/windows` — Variance Risk Premium Windows
- `GET /api/volatility/anomaly/top` — Top Volatility Anomalies
- `GET /api/volatility/character/top` — Top Volatility Character
- `GET /api/volatility/option-sentiment/top` — Top Options Positioning Sentiment
- `GET /api/volatility/vix-term-structure` — VIX Term Structure
## websocket

Full definitions: [categories/websocket.md](categories/websocket.md)

- `GET /api/socket` — WebSocket channels
- `GET /api/socket/contract_screener` — Contract screener
- `GET /api/socket/custom_alerts` — Custom alerts
- `GET /api/socket/flow_alerts` — Flow alerts
- `GET /api/socket/gex` — GEX
- `GET /api/socket/greek_flow` — Greek flow
- `GET /api/socket/greek_flow_expiry` — Greek flow by expiry
- `GET /api/socket/greeks` — Greeks
- `GET /api/socket/interpolated_iv` — Interpolated IV
- `GET /api/socket/interval_flow` — Ticker Interval flow
- `GET /api/socket/iv_term_structure` — IV term structure
- `GET /api/socket/lit_trades` — Lit trades
- `GET /api/socket/market_tide` — Market tide
- `GET /api/socket/net_flow` — Net flow
- `GET /api/socket/news` — News
- `GET /api/socket/off_lit_trades` — Off-lit trades
- `GET /api/socket/option_trades` — Option trades
- `GET /api/socket/periscope` — Periscope
- `GET /api/socket/price` — Price
- `GET /api/socket/quotes` — Stock quotes
- `GET /api/socket/risk_reversal_skew` — Risk reversal skew
- `GET /api/socket/ta_1d_live` — Technical analysis indicators
- `GET /api/socket/trading_halts` — Trading halts
