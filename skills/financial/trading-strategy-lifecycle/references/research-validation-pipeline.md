# Research → Backtest → Paper Trade Handoff

## Correct Sequence

```text
Explore pattern
→ define hypothesis
→ define strategy rules
→ backtest historically
→ decide reject/research/paper-test
→ paper trade in isolated portfolio
→ track outcomes
→ feed results back into exploration
```

## Candidate Pattern Requirements

A strategy candidate should include:

- Strategy family: UW/Kian, GEX, VEX, Graphify, sector breadth, or hybrid.
- Observation unit: ticker-day, contract-day, intraday window, or portfolio trade.
- Feature list and target horizon.
- Baseline comparison.
- Leakage controls.
- Sample size and market-regime segmentation.
- Entry, confirmation, exit, invalidation, and risk rules.
- Why it is worth backtesting.

## Backtester Input Contract

```json
{
  "candidate_strategy_id": "uw_oi_carryover_v1",
  "hypothesis": "High initial contract volume followed by next-day OI carryover improves 1-3 day option returns.",
  "asset_class": "options",
  "entry_rules": ["Initial contract volume exceeds strategy threshold"],
  "confirmation_rules": ["Next trading day OI carryover after market open"],
  "exit_rules": ["OI fade", "bid-side exit pressure", "target/stop reached"],
  "risk_rules": ["max allocation", "liquidity/spread filters"],
  "data_sources": ["Unusual Whales", "Skylit GEX/VEX", "price history", "strategy logs"],
  "recommended_backtest_windows": ["bull", "bear", "high-vol", "low-vol"],
  "known_pitfalls": ["avoid same-day OI confirmation", "avoid lookahead leakage"]
}
```

## Paper Trader Handoff Contract

```json
{
  "strategy_id": "uw_oi_carryover_v1",
  "portfolio": "UW_OI_CARRYOVER_V1_PORTFOLIO",
  "decision": "PAPER_TEST_SMALL",
  "max_allocation": 250,
  "entry_rules": [],
  "exit_rules": [],
  "logging_required": true,
  "requires_user_approval_before_live_or_paper_order": true
}
```

## Learning Loop

Paper-trading outcomes should be logged with signal source, ticker, strategy/mode, thesis, conviction, target/stop logic, order ID, status, and outcome. The correlation lab should periodically mine these outcomes to find which confirmations actually improved expectancy.
