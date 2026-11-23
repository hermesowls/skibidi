# 2026-08 unified flow ingestion build notes

This reference captures the concrete implementation details from the session that produced the `trading-ingestion-automation` workflow.

## Original state found

- No dedicated `flowerseeker` / `flowseeker` ingestion cron existed.
- Existing partial ingestion job was `learning-intraday-whale-monitor-discord-alerts`.
- That existing job was already `no_agent: true`.
- It ran `trading_learning_intraday.sh`, which called `trading_learning_engine.py intraday_monitor`.
- Existing engine did UW mirror, UW exit/sell-pressure check, and UW whale position monitor.
- Existing engine did not include dedicated Skylit/Flowseeker ingestion.
- Existing engine did not include Discord notable-flow channel ingestion.

## Stale state discovered

- State file: `/Users/admin/.hermes/flow_ingestion_state.json`
- It tracked Discord message IDs for notable-flow channels but was stale before rebuild.
- The file was reused and extended instead of discarded.

## Confirmed Discord channels

- `notable-flow`
- `notable-etf-flow`

## Build artifacts

- Unified script: `/Users/admin/.hermes/scripts/flowseeker_unified_ingestion.py`
- Central filters: `/Users/admin/.hermes/ingestion_filters.json`
- Unified operational DB: `/Users/admin/.hermes/trading_logs/unified_flow_ingestion.sqlite`
- Dashboard-visible DB: `/Users/admin/.hermes/data/analyst_trading.db`
- Dashboard-visible table: `notable_flow`
- Logs: `/Users/admin/.hermes/trading_logs/flow_ingestion/`

## New cron

- Name: `flowseeker-unified-ingestion`
- Job ID from build session: `c0319b163650`
- Schedule: every 15 minutes
- Mode: `no_agent: true`
- Delivery: `local`

Job IDs can change if recreated; always verify with `cronjob list` rather than relying on this ID.

## Verification results from build session

- Direct forced run with `--skip-flowseeker --verbose`: Discord polling worked and state advanced.
- Direct forced full run: Flowseeker source enabled and did not crash; no eligible capture candidate at that moment.
- Hermes cron manual run: returned `last_status: ok`.
- UW mirror hit HTTP 429 during verification, so script recorded a rate-limit backoff instead of hammering the API.
- Dashboard page was confirmed to read `/api/analyst-trader/notable-flow`, backed by `AnalystDatabase.get_notable_flow()` and `~/.hermes/data/analyst_trading.db:notable_flow`.
- Unified cron was patched so filter-passed rows write to the dashboard-visible `notable_flow` table; raw/no-op/audit information remains in the operational DB.

## Dashboard visibility rule

“No-agent stays silent” means no chat delivery on no-op success. It does not mean no persistence. Runs and audit details should persist locally. Only filter-passed/notable rows should be inserted into the dashboard-visible `notable_flow` table.

If a future ingestion cron writes to a new SQLite DB, do not assume the dashboard can see it. Inspect the dashboard endpoint and patch either the UI/API or the cron writer so visible rows land in the table the dashboard already reads.

## Skylit MCP/API rule

Use Skylit MCP/API before Playwright/browser Flowseeker capture when the MCP is healthy. Browser capture is fallback/enrichment.

In this session Skylit MCP was configured as an HTTP MCP with static bearer header, not OAuth:

```yaml
mcp_servers:
  skylit:
    url: https://mcp.skylit.ai/mcp
    headers:
      Authorization: Bearer ${...}
```

`hermes mcp test skylit` returned HTTP 403. For this auth shape, `hermes mcp reauth skylit` is not the repair path because `reauth` applies to OAuth-configured MCP servers. Static bearer 403s require updating the referenced env var/token/key, checking scope/account access, then reloading/retesting MCP. On remote gateways, prefer dashboard Connectors/MCP settings if available; otherwise update `~/.hermes/.env` directly without printing the secret.

## Security notes

- Credential presence was checked only; values were not printed.
- UW API key, Discord bot token, Skylit login, Skylit MCP bearer token, and webhook URLs must remain redacted.

## Important framing for future summaries

Say “partial UW ingestion existed” rather than “the full ingestion cron existed” when only the learning monitor is present. A cron being scheduled does not prove ingestion is healthy; verify DB/state freshness and source-specific run status.
