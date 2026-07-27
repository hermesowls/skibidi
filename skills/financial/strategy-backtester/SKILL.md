---
name: strategy-backtester
description: Use when validating trading strategies on history.
version: 1.0.0
author: Skibidi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, backtesting, options, stocks, validation, paper-trading]
    related_skills: [autonomous-trader, paper-trader, unusual-whales, skylit-ai]
---

# Strategy Backtester

## Overview

Use this skill to turn a defined trading idea into a historical simulation that can be scored before it ever touches paper trading. The backtester is the validation gate between exploratory research and live paper portfolios.

The goal is not to produce a perfect fantasy P/L curve. The goal is to answer: **Did this rule-set have repeatable edge after realistic costs, slippage, expiry behavior, risk controls, and invalidation rules?**

Every tested strategy must produce an auditable artifact: inputs, assumptions, trades, equity curve, metrics, failure cases, and a pass/fail recommendation for paper-trader delegation.

## When to Use

Use this skill when Amar asks to:

1. Backtest an Unusual Whales, Kian, GEX, VEX, stock, or options strategy.
2. Validate a new rule set discovered by correlation/pattern research.
3. Compare strategy variants before picking one for paper trading.
4. Estimate win rate, expectancy, drawdown, Sharpe/Sortino, max loss, holding period, and stop/target behavior.
5. Decide whether a strategy graduates to an isolated paper-trader portfolio.

Do not use this skill for live execution. Execution belongs to `paper-trader` / `autonomous-trader` after explicit permission and portfolio assignment.

## Strategy Intake Contract

Every backtest starts with a structured strategy definition. If the user gave only a rough idea, convert it into this schema before testing.

```json
{
  "strategy_id": "uw_oi_carryover_v1",
  "strategy_name": "UW OI Carryover Confirmation",
  "asset_class": "options|stocks|mixed",
  "universe": ["tickers or filter rules"],
  "data_sources": ["unusual_whales", "skylit_gex", "skylit_vex", "yfinance", "alpaca", "polygon", "local_cache"],
  "entry_trigger": "initial condition that creates a trade candidate",
  "confirmation_rules": ["conditions that must occur before entry or size-up"],
  "exit_rules": ["take profit", "stop loss", "time stop", "whale exit", "OI fade"],
  "position_sizing": "fixed dollars, % equity, volatility-adjusted, premium-risk cap",
  "holding_period": "intraday|1d|2-5d|until expiry|custom",
  "cost_model": {
    "commission": 0,
    "slippage_bps": 10,
    "options_spread_penalty_pct": 5
  },
  "risk_limits": {
    "max_position_pct": 15,
    "max_daily_loss_pct": 3,
    "max_drawdown_pct": 20
  },
  "promotion_thresholds": {
    "min_trades": 30,
    "min_expectancy": 0.05,
    "min_profit_factor": 1.25,
    "max_drawdown_pct": 20
  }
}
```

## Required Data Handling

1. **Source-first**: Use actual historical source data when available. For Unusual Whales strategies, prefer cached/live UW historical flow, option-contract historical, intraday contract flow, and OI data. For GEX/VEX, use Skylit exports/screenshots/data if available; otherwise state exactly what proxy is being used.
2. **No mock performance**: Never fabricate returns, fills, OI, or option prices. If data is missing, disclose the gap and use a conservative proxy only if explicitly labeled.
3. **Timestamp alignment**: Align signals, fills, and exits to the data available at that time. Do not let future OI/price data leak into entry decisions.
4. **Options realism**: Account for DTE, bid/ask spread, liquidity, theta decay, contract multiplier, assignment/expiry behavior, and open interest update timing.
5. **One strategy per run**: Keep a single backtest run focused. Compare variants only after each variant has its own metrics.

## Backtest Workflow

### 1. Define the hypothesis

State the hypothesis in one sentence.

Example: `When a high-volume UW contract has next-session OI carryover and same-direction ask-side follow-through, holding 1-3 sessions has positive expectancy.`

Completion criterion: hypothesis includes signal, confirmation, direction, holding period, and expected edge.

### 2. Build the dataset

Collect or load every required field:

**Stocks**: OHLCV, adjusted close, corporate action handling, sector/ETF context.

**Options**: contract symbol, type, strike, expiry, DTE, bid/ask/mid/close, volume, OI, ask/bid side premium, IV if available.

**Flow**: notable alerts, initial volume trigger, premium, side, repeated hits, Vol>OI, next-day OI carryover.

**GEX/VEX**: dealer pin zones, volatility expansion nodes, support/resistance nodes, regime metadata.

Completion criterion: data coverage report lists row counts, date range, missing fields, and any proxy assumptions.

### 3. Simulate without lookahead

For each day/session:

1. Generate candidates from information available up to that timestamp.
2. Apply confirmation rules only after they would have been observable.
3. Enter using realistic fill logic.
4. Manage target, stop, time stop, whale exit, and invalidation rules.
5. Record every trade decision.

Completion criterion: every simulated trade has entry timestamp, exit timestamp, entry reason, exit reason, size, gross P/L, net P/L, and max adverse/favorable excursion.

### 4. Score the strategy

Required metrics:

**Trade Count**: total completed trades.
**Win Rate**: winners / total.
**Average Win / Loss**: net returns after costs.
**Expectancy**: average net return per trade.
**Profit Factor**: gross wins / gross losses.
**Max Drawdown**: peak-to-trough equity decline.
**Sharpe / Sortino**: if enough observations exist.
**Exposure**: percent of time in market.
**Average Holding Period**: by trade and by strategy.
**Tail Risk**: worst trade, worst day, worst week.
**Sensitivity**: performance by DTE bucket, volume bucket, OI carryover bucket, regime, ticker, side.

Completion criterion: produce a markdown report and machine-readable JSON summary.

### 5. Decide promotion

Classify result:

**REJECT**: no edge, insufficient data, unstable, or severe drawdown.
**RESEARCH_MORE**: promising but sample too small or needs better feature separation.
**PAPER_TEST_SMALL**: clears minimum thresholds but needs live validation.
**PAPER_TEST_FULL**: strong sample, robust across buckets, realistic fills pass.

Promotion to paper trading must create an isolated portfolio, a strategy ID, risk caps, and logging fields. Do not place paper trades without explicit user approval.

## Output Contract

Every backtest report should include:

```markdown
## Strategy Backtest Report

**Strategy ID**: ...
**Hypothesis**: ...
**Asset Class**: ...
**Date Range**: ...
**Data Sources**: ...
**Sample Size**: ...
**Assumptions**: ...

## Results

**Net Return**: ...
**Win Rate**: ...
**Expectancy**: ...
**Profit Factor**: ...
**Max Drawdown**: ...
**Best/Worst Bucket**: ...

## Edge Diagnosis

**What Worked**: ...
**What Failed**: ...
**Where It Works Best**: ...
**Where It Breaks**: ...

## Recommendation

**Decision**: REJECT | RESEARCH_MORE | PAPER_TEST_SMALL | PAPER_TEST_FULL
**Reason**: ...
**Paper Portfolio Proposal**: ...
```

Machine-readable output should be saved as JSON with at least:

```json
{
  "strategy_id": "...",
  "decision": "PAPER_TEST_SMALL",
  "metrics": {},
  "trades_path": "...",
  "report_path": "...",
  "data_coverage": {},
  "promotion_plan": {}
}
```

## Integration With Other Strategy Skills

**Input from `strategy-correlation-lab`**: Candidate hypotheses, discovered features, feature thresholds, and regime filters.

**Output to `paper-trader`**: Only strategies that pass thresholds and receive explicit user permission.

**Output to `autonomous-trader`**: Strategy IDs, portfolio names, risk budgets, logging fields, and live-monitoring conditions.

**Output to `unusual-whales`**: Validated Kian/UW pattern rules such as OI carryover thresholds, ask-side continuation, or exit pressure signals.

**Output to `skylit-ai`**: Validated GEX/VEX node behaviors and time horizons.

## Logging Requirements

Every run must log to `~/.hermes/trading_logs/strategy_events.jsonl` and SQLite via `strategy_logger.py` when available.

Required event types:

**backtest_start**
**backtest_data_coverage**
**backtest_trade_simulated**
**backtest_result**
**backtest_recommendation**
**paper_promotion_proposed**

Do not log credentials or raw API keys.

## Common Pitfalls

1. **Lookahead bias**: Never use next-day OI to enter a same-day trade. Next-day OI can confirm or invalidate after market open the following trading day.
2. **Survivorship bias**: Do not only test winners or current popular tickers.
3. **Ignoring options liquidity**: A strategy that wins on mid-price but cannot fill near mid may fail live.
4. **Overfitting**: If a strategy only works with hyper-specific thresholds, mark it `RESEARCH_MORE` unless out-of-sample performance confirms it.
5. **Premium-only bias**: High premium is context, not always edge. Volume, OI carryover, side, regime, and price response matter.
6. **Paper execution leakage**: Backtesting does not authorize live or paper orders.

## Verification Checklist

- [ ] Strategy definition is explicit and machine-readable.
- [ ] Historical data source and coverage are reported.
- [ ] No lookahead leakage in signal timing.
- [ ] Costs/slippage/spread assumptions are included.
- [ ] Trades ledger exists.
- [ ] Metrics JSON exists.
- [ ] Markdown report exists.
- [ ] Recommendation is one of `REJECT`, `RESEARCH_MORE`, `PAPER_TEST_SMALL`, `PAPER_TEST_FULL`.
- [ ] If promoted, paper-trader handoff is proposed but not executed without explicit approval.
