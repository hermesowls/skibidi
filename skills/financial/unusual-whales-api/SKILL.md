---
name: unusual-whales-api
description: Use when querying Unusual Whales API endpoints.
version: 0.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [finance, options, unusual-whales, api, flow]
---

# Unusual Whales API

Use for endpoint selection, schema-grounded requests, options-flow interpretation and documentation refresh. Documentation coverage is not live endpoint testing. No credentials are needed for the bundled documentation or helper; live reads require separately authorized access. Never call every endpoint to learn the API.

## Procedure
1. Read `references/selection-and-semantics.md` and `references/whale-protocol.md` before flow work.
2. Read `references/catalog.md` to locate the exact operation and its category file under `references/categories/`. Those files contain every operation, resolved parameter constraints, response schemas, security and original descriptions. `references/inventory.json` is the machine-readable equivalent; `references/openapi.yaml` is the complete authoritative source snapshot.
3. Distinguish the HTTP operations in the public OpenAPI (including websocket documentation entries) from the 128 Unusual Whales MCP wrappers advertised in this session. MCP names/counts are not a REST inventory and wrapper arguments may differ. Load a wrapper's actual tool schema before using it. No inferred one-to-one mapping.
4. Validate path identifiers, required parameters, enums, limits, array serialization, date ranges and timestamp units against the selected operation. Do not silently repair malformed identifiers. Preserve raw values and record request/response provenance without secrets.
5. For historical work, use an endpoint that explicitly supports the requested day. Latest-day `/api/option-trades` does not become historical through `intraday_only=false` or old cursors. An empty/partial page is not proof of no activity.
6. Classify whales using the evidence ladder and user defaults in the whale protocol: individual size >=500 (not volume), premium >=$50,000, volume > OI, analysis-date America/New_York DTE 1–14, OTM with unlimited distance (local `max_otm_fraction: null`), `include_agg_trades=false`, `limit=20`. Aggregate cohorts require separate authorization. Keep raw matches, aggregated orders, verified individual prints and directional inferences separate.

## Refresh and verification
Use `terminal` to run `python ~/.hermes/skills/financial/unusual-whales-api/scripts/refresh_docs.py --validate` for offline count, hash, coverage, examples and reference validation. Use `--refresh-payload /path/to/payload.json` to fetch only the public docs/spec and prepare a complete set of supporting-file operations; apply those through `skill_manage`, not direct writes to a repository. The helper uses Python stdlib plus already-installed PyYAML; no installs or market-data calls. Review changed semantics before publishing a refresh.

Read `references/storage.md` first for large files: logical files exceeding manager limits are losslessly sharded into `.partNNN` files with `.index.json` listing order/hash. Use the helper's `load_logical(path)` to reconstruct source, inventory or category files. Read `references/manifest.json` for actual retrieval time, source hash, counts, transport classification and limitations. All categories are covered in generated references; recursive schema references, if any, remain explicit and resolve against the bundled source rather than being silently dropped.

## Provider allocation for Amar's watchlist research
- Amar confirms an existing Finviz Elite API and prefers it for underlying stock data. He approved Finviz quotes plus CBOE historical OHLCV using existing integrations, provided coverage supports the requested EMA/TTM analysis. Qualify actual endpoint/schema/session/adjustment semantics and completed-bar coverage; missing sessions must yield insufficient data, not interpolation or invented candles. Finviz screener snapshots alone are not OHLC history. This source split does not authorize recurring collection.
- Reserve UW requests for whale discovery and the corresponding option contracts. Do not automatically fall back to UW underlying-stock history or quotes. Existing UW-derived SPY daily snapshots remain historical evidence with their original provenance, not authorization for ongoing UW stock collection.
- If Finviz history or live access is unqualified, show unavailable/blocked with the precise reason rather than fabricate candles or relabel delayed quotes as real-time.
- Recovery discovery found `FINVIZ_API_URL` present in environment/profile and checkout configuration: redacted host/path `elite.finviz.com/export/screener`, query names `v`, `f`, `auth`. Never print query values or request that URL merely to discover capabilities. Scoped code had no consumer or qualified historical OHLC schema. Distinguish an existing authenticated screener API from a qualified historical candle/quote-as-of adapter; ask for endpoint/schema/session and timestamp semantics, not a replacement key. CLI automatic underlying and external artifact-free coordinator must fail closed; preserve historical UW raw replay and records without relabelling as Finviz.

## Pitfalls
- Flow alerts and rolled-up tape rows are not single prints; ask-side labels do not establish a confirmed buy or opening trade.
- Unknown/missing fields are not false; null SPXW underlying price does not establish OTM. Never invent an execution timestamp.
- Contract volume greater than OI is not proof of opening activity. Next-session OI is later corroboration, not point-in-time evidence.
- Use endpoint-specific pagination; cursor, page and offset are not interchangeable. Report any unverified server behavior rather than inventing exhaustiveness.
- Specs can contain contradictory examples, sparse responses and undocumented entitlement/rate-limit behavior. Preserve those limitations. This build performs documentation-only validation, zero live market/account calls.
