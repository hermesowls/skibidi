---
name: autonomous-trader
description: Autonomous trading strategy evaluator, isolated strategy sub-portfolios, continuous optimization engine, and position tracker.
---

# Autonomous Strategy & Isolated Sub-Portfolios Skill

Use this skill whenever requested via **Telegram**, **iMessage**, **CLI**, or **TUI** to run strategy evaluations, check sub-portfolio performance comparisons, log trade closes/reflections, or track open positions.

---

## 🔒 CHANNEL PERMISSIONS & RESTRICTIONS

| Platform | Paper Trading & Portfolio Access | Status |
| :--- | :--- | :--- |
| **Telegram** | Full Execution & Portfolio Access | 🟢 **Allowed** |
| **iMessage** | Full Execution & Portfolio Access | 🟢 **Allowed** |
| **CLI / TUI** | Full Execution & Portfolio Access | 🟢 **Allowed** |
| **Discord** | **Restricted** (No trade execution or portfolio controls) | 🔴 **Blocked** |

---

## 💼 ISOLATED STRATEGY SUB-PORTFOLIOS ($1,000 STARTING CAPITAL)

| Portfolio Name | Initial Capital | Target Horizon | Core Engine | Position Sizing |
| :--- | :--- | :--- | :--- | :--- |
| **⚡ GEX 0DTE Intraday Scalp** | $1,000.00 | Intraday Scalp | Pure Skylit 0DTE Gamma Pin Nodes | $150 (15%) |
| **🛡️ VEX 1-Week Swing & UW Overlap** | $1,000.00 | 1-Week Horizon | Skylit VEX Volatility + Unusual Whales Overlap | $250 (25%) |

---

## ⛔ FORMATTING LAWS (TELEGRAM & iMESSAGE)

> [!CAUTION]
> 1. **BAN ON BULLET POINTS (`•`, `-`, `*`)**: Format all output lines with bold label prefixes: `**Total Portfolio Value**: $1,000.00`.
> 2. **BAN ON `<sub>` HTML TAGS**: Use clean markdown italics for disclaimers.

---

## Discord Intelligence Briefing Standard

The Discord briefing script `scripts/discord_briefing.py` must rank the Notable Flow section by **daily whale option positions**, not a generic top-stock list. Use Unusual Whales `/option-trades/flow-alerts` aggregated by ticker with premium, ask-side urgency, repeated alerts, contracts, and Vol>OI hits; if live credentials are unavailable, use the latest local UW flow-alerts cache before falling back.

Educational mode is optional: pass `--explain`, `--educational`, `--explain-condition true`, or set `BRIEFING_EXPLAIN=true`. When enabled, each section includes concise `Why it matters` explanations so the morning briefing becomes instructive for users who do not know terms like risk-on trend, Skylit GEX/VEX nodes, or Graphify sympathy/supply-chain connections.

## 🐋 Whale Position Monitoring Standard

Use `/Users/admin/.hermes/scripts/uw_whale_position_monitor.py` to seed and monitor notable-flow whale contracts after intelligence briefings. **Initial watchlist admission is triggered by initial contract volume from notable whale flow**. Premium, ask-side urgency, Vol>OI, sector/tape context, and contract price behavior are context fields. **Do not keep presenting the same contract as fresh insight**: the monitor must store prior whales, label repeated contracts as `CARRYOVER`, add only newly seen contracts as `NEW`, and move old/non-current contracts into stored or stale monitoring instead of highlighting them. **Subsequent checks are conviction confirmations**, not re-entry criteria: next-session OI carryover, follow-through ask-side flow, bid-side exit pressure, OI deterioration, and conviction changes.

**Seed watchlist**: `python3 /Users/admin/.hermes/scripts/uw_whale_position_monitor.py seed --limit 10`

**Check status**: `python3 /Users/admin/.hermes/scripts/uw_whale_position_monitor.py status`

**Silent alert check**: `python3 /Users/admin/.hermes/scripts/uw_whale_position_monitor.py check --send-discord`

Alerts should fire only for material changes: OI carryover confirmation, follow-through flow, possible whale exit/sell pressure, or OI fade. **All Discord-facing whale alerts must be human-readable first**: show contracts as `EEM $62 Put expiring Sep 18, 2026` before raw IDs, spell out `Open Interest` instead of `OI`, use `Whale-Day Volume` instead of `Entry Volume`, and label persistence scoring as `Position Persistence Score` unless it is truly a trade-entry confidence score. **OI carryover and OI fade must only be evaluated during/after the next trading day's market open** (default gate: 6:35 AM Pacific after the entry date; weekends skipped). Same-day checks may monitor follow-through flow and sell-pressure, but must not treat OI as failed/confirmed before next-session OI has had time to update. If there is no material change, stdout should be empty so recurring monitor jobs stay silent.

## 🧪 Strategy Research / Validation Pipeline

Trading strategies should evolve through this pipeline:

**1. Explore**: `strategy-correlation-lab` mines UW/Kian, GEX, VEX, Graphify, market regime, and paper-result data for measurable patterns.

**2. Propose**: Correlation findings become machine-readable strategy hypotheses with entry triggers, conviction confirmations, exit rules, and risk notes.

**3. Backtest**: `strategy-backtester` validates each strategy on historical data with realistic costs, slippage, options liquidity, and no lookahead bias.

**4. Paper-Test**: Only strategies that pass backtest thresholds and receive explicit user approval graduate into isolated `paper-trader` / `autonomous-trader` portfolios.

**5. Track & Learn**: Paper results are logged by strategy and fed back into the correlation lab for refinement, splitting, or retirement.

## 📚 Strategy Logging Standard

All strategy workflows must log every material event to `~/.hermes/trading_logs/strategy_events.jsonl` and SQLite via `scripts/strategy_logger.py` when available.

**Required event types**: `workflow_start`, `market_regime`, `kian_candidate`, `strategy_entry`, `strategy_close`, `workflow_end`.

**Required fields**: ticker, strategy, portfolio, mode, action, conviction score, target logic, stop logic, signal rationale/synthesis, order id if any, source script, run id, status, and raw decision inputs when available.

Use `python3 skills/financial/autonomous-trader/scripts/strategy_report.py summary` or `latest --limit 20` to audit which strategies are firing and why.

## 🛠️ Execution Commands

```bash
# Compare Sub-Portfolios Performance (ROI, Win Rates, Cash)
python3 skills/financial/autonomous-trader/scripts/autotrader.py portfolios --platform [telegram|imessage|cli]

# Evaluate & Execute GEX 0DTE Strategy
python3 skills/financial/autonomous-trader/scripts/autotrader.py eval --ticker NVDA --mode GEX --platform [telegram|imessage|cli]

# Evaluate & Execute VEX 1-Week Swing Strategy
python3 skills/financial/autonomous-trader/scripts/autotrader.py eval --ticker TSLA --mode VEX --platform [telegram|imessage|cli]

# Close Trade & Update Sub-Portfolio P/L & Optimization Feedback
python3 skills/financial/autonomous-trader/scripts/autotrader.py close --ticker NVDA --outcome WIN --pnl 45.00 --lesson "Gamma scalp profit target reached"
```
