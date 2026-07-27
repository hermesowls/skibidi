---
name: trading-dashboard-tracker
description: Use when building trading dashboard tracker UIs.
version: 1.0.0
author: Skibidi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, dashboard, portfolios, workflows, monitoring, ui]
    related_skills: [autonomous-trader, paper-trader, strategy-backtester, strategy-correlation-lab]
---

# Trading Dashboard Tracker

## Overview

Use this skill when building or maintaining a visual dashboard tab for trading automation. The dashboard should make it obvious when agents are running workflows, what portfolios exist, which tickers are active, what P/L looks like, what strategy each position belongs to, and what information a human needs to understand the system quickly.

This skill exists because trading workflows spread across cron jobs, Discord posts, strategy logs, paper-trading journals, whale watchlists, and local portfolio JSON. A human dashboard should unify those into one readable operating view.

## When to Use

Use this skill when Amar asks for:

1. A dashboard tab similar to Graphify for trading.
2. UI elements showing agent workflow activity.
3. Portfolio tracker cards or trading P/L panels.
4. A human-readable view of positions, tickers, strategy rationale, conviction, targets/stops, and status.
5. A whale radar / notable-flow monitor UI.
6. A dashboard connection between strategy research, backtests, paper portfolios, and live tracking.

Do not use this skill to place trades. The dashboard tracker is read-only unless Amar explicitly requests controlled execution UI with safety gates.

## Preferred Dashboard Shape

Build the tracker as a dashboard plugin rather than patching Hermes core.

```text
~/.hermes/plugins/<plugin-name>/
├── plugin.yaml
└── dashboard/
    ├── manifest.json
    ├── plugin_api.py
    └── dist/
        ├── index.js
        └── style.css
```

The dashboard tab should usually be named **Trading Tracker** and placed near Graphify when possible.

## Required UI Sections

### Portfolio Cards

Show each isolated strategy portfolio with:

**Portfolio Name**
**Strategy Family**
**Estimated Value**
**Cash**
**Allocated Capital**
**Realized P/L**
**ROI**
**Open Positions**
**Optimization / Learning Status**

### Open Positions Table

Show every active position with:

**Ticker**
**Portfolio**
**Strategy**
**Mode**
**Conviction Score**
**Allocated Capital**
**Target Logic**
**Stop Logic**
**Status**
**Order ID** when present
**Thesis / Synthesis**
**Timestamp**

The table must explain why the position exists. Numbers alone are not enough.

### Workflow Monitor

Show trading-related workflows and jobs:

**Kian / Unusual Whales workflows**
**Skylit GEX/VEX workflows**
**Whale monitor jobs**
**Discord intelligence briefings**
**Portfolio checks**
**Backtester jobs**
**Correlation lab jobs**
**Paper-execution workflows**

For each workflow, show:

**Name**
**Schedule**
**Enabled / Paused**
**Running / Scheduled / Failed / OK**
**Last Run**
**Next Run**
**Delivery Target**

### Whale Radar

Show notable-flow contracts currently on radar:

**Ticker**
**Contract**
**Option Type**
**Initial Volume**
**Entry OI**
**Last OI**
**Premium Context**
**Side**
**Conviction Score**
**Status**
**Last Checked**

Important: initial volume is the watchlist admission trigger. OI carryover, follow-through flow, and exit pressure are subsequent conviction confirmations, not re-entry criteria.

### Strategy Event Feed

Show the latest material events from the strategy logs:

**Workflow started / ended**
**Candidate detected**
**Whale monitor alert**
**OI carryover confirmation**
**Exit warning**
**Backtest result**
**Paper entry / exit**
**Error / blocker**

Every event should preserve strategy ID, ticker, action, status, and rationale when available.

### Paper Account Snapshot

When available, show Alpaca Paper status and positions. Never expose credentials. Empty or missing credentials should be called out directly, but do not persist credential values anywhere.

## Data Sources

Read-only dashboard APIs should aggregate from:

**Strategy Portfolios**: `~/.hermes/strategy_portfolios_db.json`

**Paper Journal**: `~/.hermes/paper_trading_journal.json`

**Strategy Logs**: `~/.hermes/trading_logs/strategy_events.jsonl`

**Strategy SQLite**: `~/.hermes/trading_logs/strategy_events.sqlite`

**Whale Monitor DB**: `~/.hermes/trading_logs/whale_position_monitor.sqlite`

**Cron Jobs**: `~/.hermes/cron/jobs.json`

**Paper Trader Helper**: `paper-trader` status helper if configured

## Dashboard Plugin Implementation Steps

1. Create `plugin.yaml` so Hermes can enable the user plugin.
2. Create `dashboard/manifest.json` with tab route, label, icon, JS entry, CSS path, and optional backend API path.
3. Create `dashboard/plugin_api.py` with FastAPI routes under `/api/plugins/<name>/`.
4. Create `dashboard/dist/index.js` as a plain IIFE using `window.__HERMES_PLUGIN_SDK__` and `window.__HERMES_PLUGINS__.register(...)`.
5. Create `dashboard/dist/style.css` with dashboard theme variables, not hardcoded visual systems.
6. Enable the plugin with Hermes plugin config/CLI.
7. Rescan or restart dashboard.
8. Verify `/api/dashboard/plugins` includes the plugin.
9. Verify the route renders the custom tab instead of redirecting to Sessions.

## UI Design Rules

1. **Read-only first**: do not add execution controls unless explicitly requested and safety-gated.
2. **Human-first explanation**: include strategy rationale and conviction reasons, not just price/P&L.
3. **Workflow visibility**: show what the agent is running, scheduled to run, or blocked on.
4. **Lifecycle separation**: label prototype/test, direct Discord workflow, formal cron, backtest, correlation lab, and paper-execution workflows separately.
5. **Theme aware**: use dashboard CSS vars such as `--color-card`, `--color-border`, `--color-muted-foreground`, `--color-ring`, and `--radius`.
6. **Low overhead**: poll gently, usually 10-30 seconds. Do not hammer local APIs or trading APIs.
7. **Secrets safe**: never return API keys, tokens, webhooks, or raw credential values from plugin APIs.

## Common Pitfalls

1. **Plugin appears missing but code is fine**: user dashboard plugins must be enabled and the dashboard must rescan/restart. Check `/api/dashboard/plugins` before debugging UI code.
2. **Route redirects to Sessions**: the plugin is not discovered/enabled, or the JS bundle failed to register with the same manifest name.
3. **Backend works in the repo venv but not dashboard**: dashboard runtime must have the backend dependencies. Keep plugin APIs mostly stdlib/FastAPI to reduce dependency risk.
4. **Dashboard UI without rationale**: portfolio dashboards must explain why trades exist; otherwise humans cannot judge strategy quality.
5. **Conflating workflows**: do not merge prototype crons, formal schedules, direct Discord cards, backtests, and paper execution into one undifferentiated “trading bot” state.
6. **Same-day OI confusion**: whale radar should not confirm or fail OI carryover before the next trading day’s market-open OI update window.

## Support Files

**Implementation Reference**: `references/session-trading-tracker-implementation.md` captures the working dashboard plugin pattern, backend response shape, frontend registration pattern, activation steps, and verification sequence.

**Manifest Template**: `templates/dashboard-manifest.json` is a starter manifest for a Trading Tracker dashboard tab.

## Verification Checklist

- [ ] `plugin.yaml` exists and plugin is enabled.
- [ ] `dashboard/manifest.json` exists and route is correct.
- [ ] `dashboard/plugin_api.py` imports successfully in the Hermes/dashboard Python environment.
- [ ] `dashboard/dist/index.js` passes JS syntax check.
- [ ] `dashboard/dist/style.css` uses dashboard CSS variables.
- [ ] `/api/dashboard/plugins` lists the plugin.
- [ ] `/api/plugins/<name>/data` returns portfolio, position, workflow, whale, and event counts.
- [ ] The dashboard route renders the tracker tab.
- [ ] No secrets appear in the API response or UI.
- [ ] The UI shows workflow state, portfolio state, position rationale, and whale radar state.
