---
name: trading-ingestion-automation
description: Use when auditing trading ingestion crons and filters.
---

# Trading Ingestion Automation

Use this skill when Amar asks to verify, build, repair, or audit trading ingestion infrastructure across market data sources such as Unusual Whales, Discord notable-flow channels, Skylit/Flowseeker, watchlist databases, and Hermes cron jobs.

## Core pattern

Prefer a deterministic `no_agent: true` Hermes cron for mechanical polling and ingestion. The script should stay silent on no-op success and emit stdout only when it ingests new material, hits an actionable error, or enters a rate-limit/backoff state.

Keep ingestion separate from:

- generated Kian/Discord conviction cards,
- paper/live execution workflows,
- research/learning reports,
- one-off visual chart capture.

## Audit checklist

1. List Hermes cron jobs and identify whether the relevant job is enabled, paused, scheduled, and `no_agent`.
2. Search scripts/state for source aliases and typos: `flowseeker`, `flowerseeker`, `skylit`, `notable_flow`, `ingest`, `flow_ingestion_state`.
3. Inspect current process state only after checking scheduler metadata.
4. Inspect source freshness through DB/state files, not only cron status.
5. Check credential presence only; never print secret values.
6. Confirm filters are centralized. If filters only exist embedded inside scripts, create a durable filter config and point the cron script at it.
7. Verify by running the script directly, then triggering the cron once via Hermes to test the scheduled path.

## Reusable ingestion architecture

Build or repair trading ingestion as a small, auditable pipeline with explicit source adapters, durable state, centralized filters, and separate sinks for raw operations versus dashboard-visible alerts.

Required components:

- source-specific adapter code for each feed, with rate-limit/backoff state per source,
- a centralized filter config rather than thresholds embedded only in scripts,
- an operational store for raw poll/run/audit details,
- a dashboard-visible store or API path for finalized notable rows,
- a cron entry that invokes the ingestion script deterministically,
- logs/state files that prove freshness without requiring chat delivery.

Keep concrete session paths, job IDs, and one-off verification results in `references/2026-08-unified-flow-ingestion-build.md`; do not rely on those paths until you verify the current host.

## Dashboard visibility contract

Do not assume a newly-created ingestion database is visible in the dashboard. First identify the dashboard API/table actually used by the UI.

For the current Hermes trading dashboard, the Notable Flow page calls `/api/analyst-trader/notable-flow`, which reads `~/.hermes/data/analyst_trading.db` through `plugins.analyst_trader.db.AnalystDatabase.get_notable_flow()` and its `notable_flow` table.

Recommended storage split:

- raw poll/run/audit details -> unified operational DB such as `~/.hermes/trading_logs/unified_flow_ingestion.sqlite`,
- dashboard-visible notable rows -> `~/.hermes/data/analyst_trading.db:notable_flow`,
- only filter-passed/notable items should be written to the dashboard table,
- no-op cron runs should still update state/logs but should not create dashboard noise.

## MCP/API preference for Skylit

When Skylit MCP/API is configured, use it as the primary data source before Playwright/browser capture. Keep Playwright Flowseeker capture as fallback/enrichment only.

Before using MCP from a cron, verify auth and transport with `hermes mcp list` and `hermes mcp test skylit`, redacting tokens. If the MCP entry is configured with `headers.Authorization: Bearer ${VAR}`, then `hermes mcp reauth skylit` is not the right fix; this is static bearer-token auth, so a 403 usually means the referenced token/key/scope needs replacement or account MCP access needs enabling. OAuth reauth applies only to OAuth-configured MCP servers.

For remote gateways, prefer dashboard Connectors/MCP settings for token/auth updates when available. If there is no dashboard auth flow and the MCP uses static bearer auth, update the referenced env var in `~/.hermes/.env`, then reload/retest MCP. Do not print token values.

### Skylit documented handshake and diagnosis

Official references: https://docs.skylit.ai/mcp/overview and /mcp/quickstart. Unified endpoint https://mcp.skylit.ai/mcp uses streamable HTTP. One API key spans Flowseeker and Heatseeker; an environment variable name such as FLOWSEEKER_API_KEY does not restrict its product scope. Keep keys in env and verify the configured reference without printing values.

For raw diagnostics use initialize protocolVersion 2025-06-18, Accept application/json, text/event-stream and Content-Type application/json. Only after successful initialize reuse Mcp-Session-Id, send notifications/initialized, then tools/list and a bounded read-only tool call. A failed initialize prevents testing later handshake steps; do not claim an omitted notification caused an initialization 403.

Docs advertise both Authorization: Bearer and X-API-Key. If their behavior differs, record exact status/body and report a documentation/runtime discrepancy rather than repeatedly changing credentials. A generic 403 alone does not uniquely prove invalid key, missing plan, suspension or network policy; official MCP and REST pages describe different possible causes. Do not rewrite a correct configured header merely to appear to fix access.

## Source wiring

### Unusual Whales

Use the existing notable-flow mirror as source ingestion, then copy current finalists into the unified DB when needed.

Typical embedded filters discovered in UW scripts:

- `min_premium=50000`
- `min_size=100`
- `unusual=true`
- ranking by premium and volume
- watchlist trigger based on initial contract volume from notable whale flow

If UW returns HTTP 429, record a backoff timestamp and skip until the backoff expires. Do not hammer the API.

### Research-only adapter qualification

Historical `run_uw_kian_one_ticker.py` / `run_uw_kian_test.py` mirrors verify a `/option-trades/flow-alerts` caller, but their permissive aliases and zero defaults do not establish provider schema, single-print semantics, event IDs, market timestamps or spot as-of. Do not import these scripts: they have cache/output/credential side effects. Read source only. Keep aggregate premium/size raw until semantics are qualified; never map them to single-print evidence just to obtain passing candidates. Receipt timestamps and content hashes are not provider observation timestamps/event IDs. For the documented individual REST source use `/api/option-trades` and explicit `include_agg_trades=false` (not MCP `add_agg_trades`); preserve original `id`, `executed_at`, decimal premium text and raw versions. Missing `is_agg`/`canceled` is unknown, not false. Schema-valid observations can persist while strict strategy status remains INCOMPLETE. Freeze revision lineage at admission so replaying an old observation after a changed version stays idempotent. Check maintained-calendar packages in the actual caller interpreter before promising calendar readiness; do not install or hand-code weekday substitutes under an offline/no-install scope. A bounded transport-injected admission path returning INCOMPLETE is only partial wiring, not completed ingestion qualification or Stage3 market proof. Reuse the inspected repository audit guard with a narrow --tests selection; all injected fixtures remain TEST even when exercising a real-research policy context. When a project-local maintained-calendar install is explicitly approved, snapshot source and pip inventory/check first, inspect resolver dry-run for unrelated changes, pin additions in scoped requirements, verify actual import in the exact caller interpreter and compare pipcheck to baseline. Calendar TA must compare observed completions against open-anchored hourly (including short final bars) or daily session closes through decision; overnight age alone is not a missing bar. Next-session OI requires independent provider observed_at, not availability/receipt relabeled as an update. Keep synthetic fixed-interval compatibility caller-explicit, never provider-selected.

### UW fill/spread and IV confirmation requirement

User clarified that reported ASK labels require actual fill-relative-to-spread and IV review. Preserve aggregate whale detection separately from directional confirmation. Use execution-time quote/print evidence, comparable same-contract IV observations and complex/canceled/corrected trade context; never equate UW midpoint ask_side with literal at/above ask. Missing evidence remains unconfirmed, not pass or silent candidate deletion. Keep reported side, verified fill location, IV confirmation and rationale distinct. Next-session Open Interest is separate. Thresholds/scoring need qualification, not invention. Current requirement handoff: /Users/admin/.hermes/hardening/20260914_230002/UW_FILL_IV_REQUIREMENTS.md; document existence is not implementation or deployment evidence.

### Discord notable flow

Poll Discord notable-flow channels through the Discord API and track `last_seen_msg_ids` in the state JSON.

Known channel roles from the working setup:

- `notable-flow`
- `notable-etf-flow`

Do not expose channel tokens or webhook URLs. Channel IDs are not secrets, but still present them only when operationally useful.

### Skylit / Flowseeker

Use Flowseeker as a visual/capture enrichment step fed by ingested candidates, not as the only source of truth.

User-approved fallback while Skylit API access is unresolved: Unusual Whales remains the flow-ingestion source; authenticated Skylit browser access supplies heatmaps/enrichment. This preference is not proof that UW jobs are currently healthy; verify source/sink freshness before claiming operational status. Do not change crons or filters merely to adopt this reading workflow.

After Skylit navigation, ticker search, or filter changes, wait for application data, not merely DOM/navigation load. Allow an initial settling interval (12 seconds is a tested starting point), then bounded polling up to 75 seconds for loading indicators to disappear and populated rows/heatmap cells or explicit empty results. Verify ticker, expiry/date filters, and displayed timestamps before using data; previous-ticker content and restored historical filters are not fresh results. A live browser check populated 100 Flowseeker rows after the settling wait, but restored a historical date filter; neither immediate Loading trades nor a table count alone establishes failure or freshness. Report timeout/loading distinctly from access denial and valid empty results. Never silently alter saved filters.

Default capture filters from the working setup:

- `max_captures_per_run=1`
- `min_premium_for_capture=250000`
- `cooldown_hours_per_contract=12`
- candidate sources: Discord notable flow and Unusual Whales

## User-refined baseline is the research boundary

Amar clarified that the starting Notable Flow filter reflects substantial manual refinement and is the intentional baseline, not an arbitrary screen to undo. The learning safeguard compares adaptive prioritization against ALL captured baseline-eligible candidates, including lower-ranked and enhancement-rejected candidates within that cohort; it does not require collecting the entire market or automatically relaxing hard filters. Treat manual experience as the rationale/working edge hypothesis, not yet quantified out-of-sample proof. Preserve baseline version and exact criteria. Separate baseline threshold eligibility from semantic uncertainty and execution readiness. Any outside-baseline control sample or hard-filter expansion is a separately proposed and approved experiment with bounded cost. Distinguish complete tracking of captured candidates from unverified completeness of baseline discovery across the market.

## Adaptive Notable Flow prioritization

Amar requires discovery to evolve dynamically as observed outcomes establish predictable edge, because raw whale volume will exceed useful attention. Separate broad raw discovery/retention, adaptive research ranking, and execution authority. Dynamic ranking may update with observed point-in-time features; learned ranking rules/weights require versioned evidence, out-of-sample/time-ordered evaluation, sufficient sample and uncertainty reporting. Preserve baseline and deprioritized/exploration cohorts so rejected candidates can still inform learning and adaptive collection does not silently censor its own evidence. Prioritize enrichment by ranked value and an explicit approved provider budget; cheap baseline outcome tracking should cover the captured cohort where feasible, with coverage gaps recorded. High premium and ask tags are features, not proof of edge. Changes to hard discovery eligibility, source coverage/cadence/cost, architecture or trade risk remain Amar-approved; online scoring is not authority for uncontrolled production self-modification. Show score version, rationale, uncertainty, freshness and validation state in frontend, separating heuristic priority from empirically supported edge.

## Research retention versus freshness

Amar clarified that all observed candidates meeting raw discovery criteria belong in longitudinal research tracking, even when older than the configured 120-second evidence-age threshold or lacking advanced confirmation. Evidence age is a feature and execution-readiness concern, not a research-retention cutoff. Keep raw-match eligibility, provenance/semantic confidence, freshness, enrichment and trade authorization separate; retain unknowns without claiming verified individual buys. Store execution, first-seen/receipt and decision times separately. Evaluate outcomes from first availability as well as event time, explicitly labeling event-time studies not executable at discovery, to avoid look-ahead. Compare baseline and confluence cohorts, failures and successes, with out-of-sample validation. The 120-second default is not an established predictive-edge threshold. Tracking requirements do not imply collectors are active, complete tape coverage, approved polling budgets or permission to relax live execution checks.

## Kian baseline versus added confluence

Amar clarified the intended MVP starts with the existing Kian-style whale screen (high premium, OTM, shorter DTE, volume/Open Interest), then improves it with reasoning, GEX and TA/statistics; it is not a new generic idea-generation system. Research candidate eligibility must be distinct from enhanced trade confirmation and execution authorization. An unavailable advanced qualifier must not silently redefine the baseline strategy or imply a baseline candidate is a validated trade.

Read-only recovery found historical `Workspace/agentic-hub/scripts/run_uw_kian_one_ticker.py:kian_pick` used volume > Open Interest, premium >= 50000, size >= 500 and ask-side preference, sorted by premium. These are historical implementation thresholds, NOT independently verified original Kian rules. That selector did not enforce OTM or DTE; a separate historical scan used DTE <= 14. Do not present those variants as one verified canonical policy. The user's remembered OI > volume was tentative; recovered screen is volume > OI. Volume > OI does not prove net opening or a specific whale still holding. Recover original Kian source material before asserting exact original thresholds. Preserve baseline cohort alongside enhanced cohort to measure incremental benefit rather than assume advanced signals improve results. No filter/deployment changes are implied by a read-only review.

## Kian-requested GEX setup tracking and feedback governance

Amar requires Kian's ticker GEX-analysis requests to create a durable tracked setup/research ticket, with subsequent updates appropriate to the trader's intended timeframe. Treat this as a product requirement, not proof the automation is implemented or enabled. A request creates research tracking, not trade/execution authority. Record requester/source message, ticker, setup identity, requested timeframe/holding horizon, analysis timestamp, thesis, trigger/invalidation/targets, expiry context, data provenance and lifecycle. Different horizons/theses on one ticker are separate linked setups. If timeframe is absent, ask Kian; retain timeframe-pending state rather than silently choose intraday or swing. Tracking cadence and closure require explicit operating rules and approved collection budget; do not enable paused collectors from this requirement alone.

After providing the requested analysis, collect Kian's process knowledge through focused relevant questions (horizon if unknown, entry confirmation, invalidation, what would change his view, later outcome/reason for exit). Separate attributed analyst feedback from verified observations and preserve original analyses/revisions. Avoid repetitive questionnaires and interruption of the analysis workflow.

Amar alone approves major changes. Route any Kian recommendation with architecture impact to Amar before implementation, including schema/data-model, source/pipeline, cross-workstream routing, permissions/isolation, collection cost/cadence or execution/risk authority changes. Objective low-risk improvements without architectural impact may be implemented with scoped verification if they preserve existing workstreams, safeguards and permissions. Ambiguous impact means escalate rather than presume approval. Kian feedback is research input, never authority to bypass Amar's gates. Record proposal, evidence, impact, disposition and approver where required.

## Historical data collection as a core product requirement

Amar identifies historical GEX and TA data collection as core intellectual property, not merely on-demand candidate enrichment. The desired research dataset preserves market evolution at sufficient frequency to reconstruct sequences, with explicit coverage gaps rather than claims to see everything. Collection cadence, ticker universe, retention, provider entitlements and quota budget require a concrete approved design before collector activation. Candidate-triggered snapshots alone miss pre-signal context and create selection bias; include continuous approved-universe context and baseline/enhanced/rejected cohorts. Preserve original observations, event/as-of/receipt times, raw versus derived data, indicator/model versions and point-in-time availability. GEX is provider-model-derived; distinguish OI-based exposure from live-flow updates and do not interpolate snapshots into alleged observations.

Manual analyst Discord whale posts remain a separate discovery source alongside UW discovery, not merely duplicates. Retain source attribution and analyst claims separately from provider verification; cross-link shared contracts without merging distinct executions. Existing parser/source wiring does not establish current capture or complete image/edit/backfill support. Keep paused ingestion paused until explicitly approved.

## Approved starting TA scope

Amar approved adding TTM Squeeze and EMAs 8, 21, 50, 100, 200 to the Kian-baseline enhancement layer. These are EMAs, not the historical SMA chart overlay. Baseline whale detection stays separate from TA confirmation, paper authorization and advanced A+ qualification. Intended research interpretation: 8/21 momentum and reclaim/loss, 50 intermediate trend, 100/200 broader regime; bullish/bearish stacking and slopes support context, mixed stacks indicate conflict. TTM compression is not directional; release plus momentum direction and price confirmation supplies candidate entry context, not guaranteed breakout. Exact squeeze variant/parameters, price source, timeframe and completed-bar policy must be explicit/versioned and verified before implementation claims or numeric conviction. Default proposal is daily regime plus 1-hour setup context for short-DTE swing research, with intraday timing separately scoped; this timeframe proposal is not a user-approved fixed specification. Preserve missing/insufficient indicator data as unknown. Compare baseline versus enhanced cohorts including rejected candidates to evaluate incremental benefit. User approval defines starting design; skill update alone does not mean indicators are wired, tested or deployed.

## Filter defaults

A good centralized filter config should include:

```json
{
  "unusual_whales": {
    "scan_limit": 500,
    "output_limit": 15,
    "min_premium": 50000,
    "min_size": 100,
    "require_unusual": true,
    "prefer_ask_side": true,
    "rate_limit_backoff_seconds": 900
  },
  "discord_notable_flow": {
    "fetch_limit_per_channel": 50,
    "min_premium": 50000,
    "min_dte": 0,
    "max_dte": 90,
    "accepted_sides": ["ASK", "ABOVE_ASK", "A", "AA"],
    "allow_unparsed_if_keyword_hit": true
  },
  "skylit_flowseeker": {
    "max_captures_per_run": 1,
    "min_premium_for_capture": 250000,
    "cooldown_hours_per_contract": 12
  }
}
```

## Production-readiness audit checks

- A green cron exit, HTTP 200, or capture file does not establish source/sink success. Compare newest source-event timestamp with newest dashboard row; report freshness for each source and sink separately.
- Verify the imported dashboard database module actually exists in the deployed checkout. A fallback HTTP route can keep old rows visible while ingestion imports fail silently. Do not assume a historical plugin path remains installed.
- Review the insert-to-dashboard boundary for durable retries: an audit insert followed by a swallowed sink error must not make the event permanently ineligible on replay. Prefer a transactional outbox and idempotent sink upsert.
- Test money parsing with comma-formatted premiums and messages containing a strike before a labeled premium. Extract the premium field explicitly; the first dollar amount is not necessarily premium.
- For read-only audits, do not invoke ingestion, backfill, or trading entrypoints. Use read-only SQLite, pure-function tests, and isolated temporary-home scheduler tests.
- Loopback dashboard session-token injection is not an identity gate for a public tunnel. Check current authentication mode and require an authenticated gateway/edge before exposing the administrative UI.

## Dashboard blank-tab debugging

If Amar reports Analyst/Flow dashboard tabs are blank, do not assume the DB is empty. First check both DB counts and API routes.

Tight checks:

```bash
sqlite3 ~/.hermes/data/analyst_trading.db "select 'notable_flow',count(*) from notable_flow; select 'positions',count(*) from positions; select 'analysts',count(*) from analysts;"
```

Then fetch the SPA root, extract the injected `window.__HERMES_SESSION_TOKEN__`, and call dashboard APIs with `X-Hermes-Session-Token`. Symptoms seen in Sep 2026: DB had rows (`notable_flow`, `positions`, `analysts`) but `/api/analyst-trader/notable-flow` returned 404 after token auth. Root cause: the React NotableFlowPage existed, but the backend analyst-trader routes/plugin were missing from the running dashboard repo. Fix was to mount fallback routes in `hermes_cli/web_server.py` before `mount_spa(app)`, backed directly by `~/.hermes/data/analyst_trading.db`.

Minimum routes needed for the Notable Flow page:

- `GET /api/analyst-trader/notable-flow`
- `GET /api/analyst-trader/live-quotes`
- `POST /api/analyst-trader/notable-flow/backfill`
- `GET /api/analyst-trader/flow-chart/{flow_id}`

Analyst/position tabs also need:

- `GET /api/analyst-trader/analysts`
- `GET /api/analyst-trader/positions`

After patching, restart the dashboard and verify both local and Cloudflare URLs return 200 with rows.

## Reference files

- `references/2026-08-unified-flow-ingestion-build.md` — concrete build notes for the unified UW + Discord notable-flow + Skylit/Flowseeker no-agent cron, including dashboard visibility and Skylit MCP bearer-token auth findings.

## Verification commands

Use the direct script path first, then the scheduler path:

```bash
/Users/admin/repos/hermes-agent/venv/bin/python /Users/admin/.hermes/scripts/flowseeker_unified_ingestion.py --force --skip-flowseeker --verbose
/Users/admin/repos/hermes-agent/venv/bin/python /Users/admin/.hermes/scripts/flowseeker_unified_ingestion.py --force --verbose
```

Then trigger the Hermes cron once and confirm `last_status: ok`.

## Output discipline

When reporting back to Amar, separate:

- what existed before,
- what was missing,
- what was built,
- whether the original cron was `no_agent`,
- where filters live now,
- what was verified with real output,
- what remains blocked by external API rate limits.

Never summarize an ingestion job as “running” just because a cron exists; verify recent DB/state freshness.
