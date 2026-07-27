---
name: trading-strategy-lifecycle
description: Use when evolving trading ideas into paper portfolios.
version: 1.0.0
author: Skibidi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, research, backtesting, paper-trading, unusual-whales, gex, vex]
---

# Trading Strategy Lifecycle

Use this when Amar wants trading strategies to evolve from exploratory research into validated, isolated paper-trading portfolios.

This skill coordinates the class of work that spans correlation research, backtesting, paper-trader handoff, and post-trade learning.

## Core Pipeline

```text
Explore data patterns
→ formulate strategy hypothesis
→ define entry/confirmation/exit/risk rules
→ backtest on historical data
→ decide reject/research/paper-test
→ delegate validated strategy to isolated paper portfolio
→ log results and outcomes
→ feed performance back into research
```

## Role Separation

1. **Correlation Lab** discovers useful patterns in Unusual Whales/Kian, GEX, VEX, Graphify, sector breadth, price/volume, and realized trade outcomes.
2. **Backtester** validates those ideas historically with realistic assumptions.
3. **Paper Trader** receives only validated strategies after explicit approval, using isolated portfolios.
4. **Strategy Logger** records rationale, signal source, confirmations, order state, and outcomes for learning.

## User-Specific Whale-Flow Rule

For notable-flow whale monitoring:

1. Initial watchlist admission is triggered by **initial contract volume** from notable whale flow.
2. Subsequent checks are conviction confirmations, not new entry criteria.
3. Next-session OI carryover/fade checks must wait until market open on the next trading day.
4. Same-day checks can monitor follow-through ask-side pressure, bid-side sell/exit pressure, and contract price behavior.

## Promotion Criteria

Do not promote a strategy to paper trading from a neat-looking chart or single correlation. Require:

1. Defined entry, confirmation, exit, invalidation, and position-sizing rules.
2. Historical test against a baseline.
3. Costs/slippage/spread/liquidity assumptions.
4. Out-of-sample or walk-forward evidence when possible.
5. Regime/ticker/bucket sensitivity analysis.
6. Clear `REJECT`, `RESEARCH_MORE`, `PAPER_TEST_SMALL`, or `PAPER_TEST_FULL` decision.

## Paper Handoff Contract

Only after validation and explicit approval, create or use an isolated portfolio named for the strategy family/version, e.g.:

```text
UW_OI_CARRYOVER_V1_PORTFOLIO
GEX_PIN_DISTANCE_V1_PORTFOLIO
VEX_EXPANSION_CONTINUATION_V1_PORTFOLIO
```

Every handoff must include:

- Strategy ID/version.
- Thesis and data source.
- Entry/exit/risk rules.
- Expected edge from backtest.
- Max allocation.
- Order/action constraints.
- Logging requirements.

## References

See `references/research-validation-pipeline.md` for the structured handoff between exploration, backtesting, paper trading, and learning.
