# Trading Tracker Dashboard Plugin Pattern

Session-proven pattern for a trading/workflow dashboard tab similar to Graphify.

## What the Trading Tracker Should Show

- Portfolio cards: name, cash, allocated capital, estimated value, ROI, open positions.
- Position table: ticker, portfolio, strategy, conviction score, allocation, target/stop, status, thesis/synthesis.
- Workflow monitor: Kian, whale, market, Skylit, briefing, portfolio, Discord, and trading cron/workflow jobs.
- Whale radar: watched contracts, initial volume, OI, premium, side, conviction, status.
- Strategy events: latest JSONL/SQLite strategy log events.
- Auto-refresh for human operators, e.g. every 15 seconds.

## Durable Data Sources

Use profile-scoped paths whenever possible; for Amar's current default profile these are:

```text
~/.hermes/strategy_portfolios_db.json
~/.hermes/paper_trading_journal.json
~/.hermes/trading_logs/strategy_events.jsonl
~/.hermes/trading_logs/whale_position_monitor.sqlite
~/.hermes/cron/jobs.json
```

For cross-profile code, resolve the active Hermes home rather than hardcoding `~/.hermes`.

## API Auth Fix

If the dashboard page loads but plugin API calls return `401 Unauthorized`, patch the frontend to use Hermes SDK auth:

```js
const API = '/api/plugins/trading-tracker/data';
SDK.fetchJSON(API)
  .then(setData)
  .catch(...);
```

Plain `fetch(API, { credentials: 'include' })` may work in some modes but is not reliable under every dashboard auth mode.

## Enable / Mount Fix

If the tab appears but `/api/plugins/<name>/<route>` returns `404 No such API endpoint`, the dashboard process likely has not mounted the new plugin API yet. Enable and restart:

```bash
hermes plugins enable trading-tracker
hermes dashboard --stop
hermes dashboard
```

## Verification

Frontend:

```bash
node --check ~/.hermes/plugins/trading-tracker/dashboard/dist/index.js
```

Backend direct import:

```bash
/Users/admin/repos/hermes-agent/venv/bin/python - <<'PY'
import importlib.util, asyncio, json
p='/Users/admin/.hermes/plugins/trading-tracker/dashboard/plugin_api.py'
spec=importlib.util.spec_from_file_location('trading_tracker_plugin_api', p)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
data=asyncio.run(mod.get_data())
print(json.dumps({
  'portfolio_count': len(data.get('portfolios', [])),
  'positions': len(data.get('positions', [])),
  'workflows': len(data.get('workflows', [])),
  'whales': len(data.get('whale_watchlist', [])),
  'events': len(data.get('strategy_events', [])),
}, indent=2))
PY
```

Browser:

- Visit `/trading-tracker`.
- Confirm sidebar shows `TRADING TRACKER` under Plugins.
- Confirm no API auth error is displayed.
- Click through Positions, Workflow Monitor, Whale Radar, Strategy Events.
