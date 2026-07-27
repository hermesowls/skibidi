# Session Implementation Note: Trading Tracker Dashboard

This note captures a reusable implementation pattern from building a trading dashboard tracker plugin.

## Built Artifact Pattern

A working trading dashboard tracker can be packaged as a user dashboard plugin:

```text
~/.hermes/plugins/trading-tracker/
├── plugin.yaml
└── dashboard/
    ├── manifest.json
    ├── plugin_api.py
    └── dist/
        ├── index.js
        └── style.css
```

## Backend Aggregation Pattern

The backend should expose a read-only endpoint like:

```text
GET /api/plugins/trading-tracker/data
```

A useful response shape:

```json
{
  "generated_at": "...",
  "summary": {
    "estimated_value": 0,
    "roi_pct": 0,
    "portfolio_count": 0,
    "open_positions": 0,
    "workflow_count": 0,
    "running_workflows": 0,
    "journal_open_trades": 0
  },
  "portfolios": [],
  "positions": [],
  "workflows": [],
  "whale_watchlist": [],
  "strategy_events": [],
  "journal": {},
  "alpaca": {}
}
```

Keep backend dependencies light. Prefer Python stdlib plus FastAPI already available in the dashboard runtime. If calling Alpaca/paper-trader helpers, never surface credentials.

## Frontend Pattern

Use a plain IIFE bundle and register the tab:

```javascript
(function () {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;
  const React = SDK.React;
  const h = React.createElement;
  function TradingTrackerPage() {
    return h("div", null, "Trading Tracker");
  }
  window.__HERMES_PLUGINS__.register("trading-tracker", TradingTrackerPage);
})();
```

Poll read-only data gently every 10-30 seconds. Provide a manual Refresh button.

## Activation Pattern

User plugins are not shown just because files exist. They must be enabled and the dashboard must rescan or restart.

```bash
hermes plugins enable trading-tracker
curl http://127.0.0.1:9119/api/dashboard/plugins/rescan
curl http://127.0.0.1:9119/api/dashboard/plugins
```

If `/trading-tracker` redirects to Sessions, the plugin was not discovered/enabled or the bundle failed registration.

## Verification

1. Import `plugin_api.py` with the same Python environment the dashboard uses.
2. Run `node --check dashboard/dist/index.js`.
3. Confirm `/api/dashboard/plugins` includes `trading-tracker`.
4. Open `/trading-tracker` and check visible sections: Portfolios, Positions, Workflow Monitor, Whale Radar, Strategy Events.
5. Inspect browser console for plugin bundle errors.
