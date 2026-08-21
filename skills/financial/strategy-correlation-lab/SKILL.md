---
name: strategy-correlation-lab
description: Use when mining market data for strategy patterns.
version: 1.0.0
author: Skibidi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, statistics, correlation, feature-engineering, research, alpha]
    related_skills: [strategy-backtester, autonomous-trader, unusual-whales, skylit-ai, graphify-trading]
---

# Strategy Correlation Lab

## Overview

Use this skill to explore market, options-flow, GEX, VEX, sector, and sympathy-graph data for meaningful patterns that can become better trading strategies.

This is the research engine before the backtester. It should constantly ask: **Which measurable features strengthen conviction, weaken conviction, or identify whale exits earlier?**

The output is not a trade. The output is a testable hypothesis, feature set, correlation/statistical evidence, and a structured strategy proposal that can be handed to `strategy-backtester`.

## When to Use

Use this skill when Amar asks to:

1. Look for patterns in Unusual Whales flow, Kian candidates, whale watchlist behavior, OI carryover, ask/bid pressure, volume, or premium.
2. Strengthen GEX/VEX strategies with historical relationships between dealer nodes, volatility nodes, price behavior, and outcomes.
3. Explore whether certain conditions improve conviction or predict failure.
4. Build new strategy ideas from data rather than intuition alone.
5. Compare features, regimes, sectors, tickers, expiries, DTE buckets, flow types, and graph/sympathy connections.
6. Produce candidate rules to send into the backtester.

Do not use this skill to claim profitability. Profitability claims require `strategy-backtester` validation.

## Research Principles

1. **Pattern discovery before strategy validation**: This skill discovers hypotheses. The backtester validates them.
2. **Measurable features only**: Convert narrative ideas into fields that can be calculated.
3. **No correlation worship**: Correlation is a clue, not proof. Require out-of-sample or backtest validation before promotion.
4. **Avoid leakage**: If a feature would not have been known at decision time, label it as confirmation/outcome data rather than an entry feature.
5. **Track failures**: Losing patterns are valuable because they define invalidation rules.
6. **Constant evolution**: Each run should propose what to test next, what to retire, and what to promote.

## Data Domains

### Unusual Whales / Kian Features

Candidate features:

**Initial Volume**: first trigger for watchlist admission.
**Volume / OI Ratio**: freshness of positioning.
**Next-Day OI Carryover**: whether volume persisted into open interest after next market open.
**Ask-Side Premium**: buyer urgency.
**Bid-Side Premium**: sell pressure or exit pressure.
**Repeated Alerts**: repeated whale hits on same contract/ticker.
**DTE Bucket**: 0DTE, 1-7DTE, 8-30DTE, 31-90DTE, LEAPS.
**Strike Moneyness**: ITM/ATM/OTM distance.
**Contract Price Behavior**: holding above intraday average, breaking below average, decay rate.
**Underlying Response**: stock follow-through after flow.
**Whale Exit Signal**: bid-side dominance, OI fade, contract price collapse.

### GEX Features

Candidate features:

**Dealer Pin Distance**: price distance from highest gamma node.
**Gamma Polarity**: positive/negative dealer environment.
**0DTE Node Strength**: intraday pin/scalp relevance.
**Node Migration**: changes in pin level across morning/midday/close.
**VIX / Vol Regime**: whether GEX behavior is stable or unstable.
**Price Rejection / Acceptance**: whether price respects or breaks the node.

### VEX Features

Candidate features:

**Volatility Expansion Node**: target or magnet level.
**Distance to VEX Node**: how far underlying is from projected move.
**Time Horizon**: 1-week swing behavior.
**Vol Regime**: IV/rV expansion or compression.
**Node Confluence**: overlap with support/resistance, UW flow, or sector breadth.
**Failure Mode**: VEX signal fails when breadth/regime contradicts or volatility compresses.

### Graphify / Sympathy Features

Candidate features:

**Supply-Chain Link Strength**: supplier/customer/peer relationship score.
**Sector ETF Confirmation**: related ETF moving with target.
**Sympathy Lag**: time between primary whale target and secondary mover.
**Cluster Flow**: multiple connected tickers receiving flow.
**Contagion Direction**: whether flow in one name predicts move in related names.

## Statistical Methods

Use methods appropriate to sample size and data quality.

**Exploratory**: groupby bucket stats, pivot tables, rolling averages, heatmaps, scatter plots, box plots.

**Correlation**: Pearson for linear relationships, Spearman for monotonic rank relationships, point-biserial for binary outcomes, Cramer's V for categorical relationships.

**Signal Quality**: information coefficient, precision/recall, lift vs baseline, hit rate by bucket, odds ratio.

**Feature Importance**: logistic regression coefficients, random forest/permutation importance, SHAP when available, mutual information.

**Time Series**: lag correlation, forward returns by horizon, regime segmentation, rolling stability.

**Robustness**: train/test split by date, walk-forward validation, bootstrap confidence intervals, false discovery controls.

## Required Workflow

### 1. Define the research question

Good examples:

**UW**: `Does next-day OI carryover after high initial volume improve 1-3 day option return expectancy?`

**GEX**: `Do 0DTE GEX pin nodes work better when VIX is falling and breadth is positive?`

**VEX**: `Do VEX expansion nodes predict swing continuation when UW flow aligns with the same direction?`

Completion criterion: the question names data source, feature, outcome, time horizon, and expected relationship.

### 2. Build the feature table

Create one row per observation using a stable unit:

**UW unit**: contract-day or ticker-contract-day.
**GEX unit**: ticker/index-day or intraday node window.
**VEX unit**: ticker-week or signal-date horizon.
**Graphify unit**: primary-secondary ticker pair by date.

Required columns:

**observation_id**
**timestamp / date**
**ticker / contract**
**strategy_family**: UW | KIAN | GEX | VEX | GRAPHIFY | MIXED
**features**
**outcome_horizon**
**outcome_return**
**outcome_label**: win | loss | flat | exit_warning | confirmed
**data_available_at_decision_time**: true/false

Completion criterion: row count, date range, missingness, and leakage status are reported.

### 3. Explore relationships

For each candidate feature:

1. Show distribution and missingness.
2. Compare outcome by feature buckets.
3. Measure lift versus baseline.
4. Test statistical significance only when sample size supports it.
5. Identify confounders: ticker, sector, date, regime, DTE, moneyness, liquidity.

Completion criterion: every proposed pattern has baseline comparison and sample size.

### 4. Convert pattern into strategy hypothesis

A useful pattern must become a rule:

```json
{
  "hypothesis_id": "uw_volume_oi_ask_followthrough_v1",
  "strategy_family": "UW_KIAN",
  "pattern_summary": "High initial contract volume with next-day OI carryover and same-direction ask-side follow-through outperforms high volume alone.",
  "entry_trigger": "initial contract volume >= threshold from notable whale flow",
  "confirmation_rules": [
    "next trading day OI >= entry OI + max(100, 25% of entry volume)",
    "same-direction ask-side premium exceeds bid-side premium",
    "contract price holds above intraday average"
  ],
  "exit_rules": [
    "bid-side premium dominates ask-side premium",
    "OI fades after next market open",
    "contract price breaks below average by threshold",
    "time stop after N sessions"
  ],
  "expected_edge": "higher win rate / expectancy than volume-only baseline",
  "test_plan": "send to strategy-backtester with 1-3 day holding period and conservative options spread model"
}
```

Completion criterion: the output can be copied directly into `strategy-backtester`.

### 5. Handoff to backtester

Only pass ideas that have:

**Enough observations**: at least rough sample-size sanity.
**Defined features**: all required columns are measurable.
**Defined outcome**: forward return / win-loss label exists.
**No unresolved leakage**: entry vs confirmation timing is clean.
**Specific thresholds**: not vague phrases like “large” unless the threshold is to be optimized in backtest.

## Autonomous Robo-Quant Research Agent

Dedicated research crons:

**Daily Research Radar**: `research-agent-daily-quant-tool-radar` — weekday 5:15 PM Pacific, delivered to Amar's origin chat. Lightweight scan for quant automation, options analytics, event/news trading, backtesting, data APIs, dashboards, observability, and Hermes-compatible tools. Produces executive summary plus one build ticket and one testable hypothesis seed.

**Weekly Deep Research Agent**: `research-agent-robo-quant-improvement` — Sundays 6:00 PM Pacific, delivered to Amar's origin chat. Deep web/public-source research on better robo-quant architecture, Hermes integrations, and strategy hypotheses. Produces executive summary, tool watchlist, architecture recommendation, strategy hypotheses, build queue, and guardrails.

Both agents are research-only: no paper/live execution, no profitability claims without backtest, and recommendations must become build tickets or backtest hypotheses.

## Autonomous Daily Learning Engine

Amar's trading self-improvement loop is implemented through `/Users/admin/.hermes/scripts/trading_learning_engine.py` and cron wrappers:

**Night research**: `trading_learning_night.sh` — event/news/regime context before next trading day.

**Premarket battle plan**: `trading_learning_premarket.sh` — UW mirror, exit checks, market snapshot, and watchlist context.

**Intraday monitor**: `trading_learning_intraday.sh` — no-agent alert loop; silent outside market hours and sends Discord directly only on material whale follow-through, OI carryover, or exit/fade alerts.

**Midday re-rank**: `trading_learning_midday.sh` — re-ranks active hypotheses and labels what is working/fading.

**Power hour**: `trading_learning_power_hour.sh` — closing-flow and risk/fade check.

**Post-close review**: `trading_learning_postclose.sh` — outcome labeling and hypothesis generation.

**Weekly evolution**: `trading_learning_weekly.sh` — weekly pattern/failure report and backtest queue.

Canonical learning DB: `/Users/admin/.hermes/trading_logs/whale_intelligence.sqlite`. Output contexts: `/Users/admin/.hermes/trading_logs/learning_engine_outputs/`. No script in this loop places paper/live trades.

## Output Contract

Every research run should produce:

```markdown
## Strategy Correlation Lab Report

**Research Question**: ...
**Strategy Family**: UW | KIAN | GEX | VEX | GRAPHIFY | MIXED
**Data Sources**: ...
**Observation Unit**: ...
**Date Range**: ...
**Sample Size**: ...
**Leakage Status**: ...

## Pattern Findings

**Baseline Outcome**: ...
**Best Feature Buckets**: ...
**Weak / Dangerous Buckets**: ...
**Correlation / Lift**: ...
**Confounders**: ...

## Strategy Proposal

**Hypothesis ID**: ...
**Entry Trigger**: ...
**Confirmation Rules**: ...
**Exit Rules**: ...
**Expected Edge**: ...
**Backtest Priority**: LOW | MEDIUM | HIGH

## Next Actions

**Send to Backtester**: YES | NO
**Reason**: ...
**Needed Data Improvements**: ...
```

Machine-readable strategy proposals should be saved as JSON so `strategy-backtester` can consume them.

## Evolution Loop

Use this loop continuously:

1. **Observe**: ingest latest strategy logs, whale monitor events, Kian candidates, GEX/VEX nodes, paper-trader results.
2. **Explore**: find feature/outcome patterns and failure clusters.
3. **Hypothesize**: create or modify a strategy definition.
4. **Backtest**: hand off to `strategy-backtester`.
5. **Paper-test**: only after validated and explicitly approved, hand off to `paper-trader` / `autonomous-trader` in an isolated portfolio.
6. **Learn**: compare live paper results against backtest expectations.
7. **Update**: strengthen, weaken, split, or retire strategy rules.

## Logging Requirements

Every correlation run must log to `~/.hermes/trading_logs/strategy_events.jsonl` and SQLite via `strategy_logger.py` when available.

Required event types:

**correlation_research_start**
**feature_table_built**
**pattern_found**
**pattern_rejected**
**strategy_hypothesis_created**
**backtest_handoff_proposed**
**research_run_completed**

Do not log credentials or raw API keys.

## Common Pitfalls

1. **Mistaking a story for a feature**: “whale confidence” must become measurable fields like ask premium ratio, OI carryover, repeated alerts, and contract price hold.
2. **Same-day OI mistake**: OI carryover cannot be confirmed before next trading day market open.
3. **Overfitting tiny samples**: If sample size is small, propose a test but mark confidence low.
4. **Ignoring base rate**: A feature is useful only if it improves over baseline.
5. **Not separating trigger from confirmation**: Initial volume can put a contract on radar; later OI/flow/price behavior confirms or invalidates conviction.
6. **Skipping handoff discipline**: Do not send vague strategy ideas to paper trading. They must pass through backtesting first.

## Verification Checklist

- [ ] Research question is explicit.
- [ ] Feature table unit is defined.
- [ ] Data availability / leakage status is stated.
- [ ] Baseline outcome is measured.
- [ ] Pattern has sample size and lift/correlation evidence.
- [ ] Confounders are considered.
- [ ] Strategy proposal has entry, confirmation, exit, sizing/risk notes.
- [ ] Handoff decision to backtester is explicit.
- [ ] No paper trading is triggered directly from exploratory research.
