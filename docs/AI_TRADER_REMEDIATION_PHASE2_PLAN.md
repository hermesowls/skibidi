# Comprehensive AI Trader Remediation Plan (Astra Re-Review Findings)

## Goal Description
Remediate the remaining findings identified in the three independent re-review reports:
1. `/Users/admin/.hermes/reports/ai-trader-remediation-rereview-learning.md`
2. `/Users/admin/.hermes/reports/ai-trader-remediation-rereview-execution.md`
3. `/Users/admin/.hermes/reports/ai-trader-remediation-rereview-validation.md`

The acceptance standard is not merely passing a unit suite, but ensuring the system can reliably answer: **"what really happened, what did it earn, and what should we learn?"**

---

## User Review Required

> [!IMPORTANT]
> **Production Safety Invariants strictly preserved during this remediation:**
> 1. **Zero Crons/Automation Resumed**: All Hermes cron jobs remain stopped (0 active jobs).
> 2. **Zero Daemons Started**: `ai.hermes.owlfred` and `ai.hermes.reconciler` remain stopped and unloaded.
> 3. **Zero Production Quarantine Applied**: Quarantine script is validated in dry-run and isolated temporary databases only; production data (`~/.hermes/data/analyst_trading.db`) is not modified.
> 4. **No External Network/Broker Calls**: Tests run offline in isolated environments with mock credentials.

> [!NOTE]
> **Preservation of Verified Fixes**: All previously verified fixes (long-put positive sign correction, profile-aware primary DB resolution, Format 2 no-fallback identity, removal of synthetic MFE/MAE WIN generation in candidate correlation) will be strictly preserved and built upon.

---

## Proposed Changes

### Component 1: Evidence & Quarantine Integrity

#### [MODIFY] [`scripts/quarantine_synthetic_data.py`](file:///Users/admin/repos/hermes-agent/scripts/quarantine_synthetic_data.py)
- **Truly Read-Only Dry-Run**:
  - Verify DB path exists before connecting; do NOT auto-create an empty file.
  - When `apply=False` (dry run), connect via `sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)`.
  - Do NOT execute `ALTER TABLE` in dry-run mode. Check for column existence using `PRAGMA table_info(...)`.
  - Add explicit `--dry-run` and `--apply` flags to `argparse`.
- **Comprehensive Predicates**:
  - `notable_flow`: Check for fallback identity (strike=100.0, expiration=2026-10-16) and verify raw message text provenance.
  - `flow_candidate_analytics`: Cover all fabricated outcomes including `WIN_TP2` / 220% MFE (entry=3.25, peak=10.4) and `WIN_RUNNER_7X` / 200%+ MFE.
  - OCC symbol matching: Correct pattern to standard OCC structure `[A-Z]{1,6}\d{6}[CP]\d{8}` (e.g. `%261016C00100000%` and `%261016P00100000%`).
- **Batch-Scoped Auditability & Scoped Revert**:
  - Add `quarantine_batch_id TEXT` column to both tables.
  - Generate a unique batch ID on apply (e.g., `batch_<timestamp>_<uuid>`).
  - `--revert` requires or defaults to `--batch-id <id>` rather than clearing all flags process-wide across all time.

#### [MODIFY] [`plugins/analyst_trader/db.py`](file:///Users/admin/repos/hermes-agent/plugins/analyst_trader/db.py)
- **Safe Ingestion Preserving Quarantine & Outcomes**:
  - Change `save_notable_flow` from `INSERT OR REPLACE` to `INSERT INTO notable_flow (...) VALUES (...) ON CONFLICT(flow_id) DO UPDATE SET ...`.
  - Preserve existing `is_quarantined = COALESCE(excluded.is_quarantined, notable_flow.is_quarantined, 0)`, `quarantine_reason = COALESCE(excluded.quarantine_reason, notable_flow.quarantine_reason)`, and do not overwrite resolved `final_outcome` with default `MONITORING`.
- **Consumer Quarantine Filtering**:
  - Ensure queries for candidate flows, analytics, and stats filter `WHERE (is_quarantined = 0 OR is_quarantined IS NULL)`.

#### [MODIFY] Consumers in Autonomous Trader Skills
- **`skills/financial/autonomous-trader/scripts/candidate_correlation_engine.py`**:
  - Add `WHERE (is_quarantined = 0 OR is_quarantined IS NULL)` to `notable_flow` candidate query.
- **`skills/financial/autonomous-trader/scripts/premarket_oi_auditor.py`**:
  - Add `WHERE (is_quarantined = 0 OR is_quarantined IS NULL)` to query.
  - **Remove Manufactured Carryover OI (Finding F6)**: Remove random PRNG score-seeded next OI generation (`rng.random()`). If `next_day_oi` or `initial_oi` is unobserved/missing, set `next_day_oi=None, oi_delta=None, is_carried_over=None`. Never fabricate OI delta and record as fact.
- **`skills/financial/autonomous-trader/scripts/flow_classifier.py`**:
  - Add `WHERE (is_quarantined = 0 OR is_quarantined IS NULL)` in `score_all_db_notable_flows`.
- **`skills/financial/autonomous-trader/scripts/flow_ingestion_engine.py`**:
  - Remove fallback derivation of entry price (`strike * 0.025`) and spot price (`spot = strike`) at lines 420-422. If pricing is unobserved, do not fabricate numbers or trigger automated entry without real quote evidence.
  - Update `CHARTS_DIR` to use `get_hermes_home() / "charts"` rather than hardcoded `Path.home() / ".hermes" / "flow_charts"`.
  - Make `get_discord_token` profile-aware with `get_hermes_home() / ".env"`.
- **`skills/financial/autonomous-trader/scripts/discord_poster.py`**:
  - Make `get_discord_token` profile-aware with `get_hermes_home() / ".env"`.

---

### Component 2: Transactional Options Accounting & Execution

#### [MODIFY] [`plugins/analyst_trader/portfolio_engine.py`](file:///Users/admin/repos/hermes-agent/plugins/analyst_trader/portfolio_engine.py)
- **Atomic Trade Execution**:
  - Wrap duplicate checking, cash availability check, holding insertion, and cash balance update inside a single immediate SQLite transaction (`with self.db.transaction() as conn:`).
  - Enforce history-wide idempotency: If `flow_id` already exists in `portfolio_holdings` (regardless of status: OPEN, TRIMMED, CLOSED), reject or return existing holding; do not allow closed-position duplicate execution.
  - Ensure concurrent executions for the same `flow_id` lock atomically at the DB level, preventing double-entry and cash overdrafts.
- **Lifecycle Price & Sizing Bounds**:
  - In `execute_autonomous_trim` and `execute_autonomous_exit`:
    - Strictly validate `current_price`: must be a positive, finite float (`current_price > 0 and math.isfinite(current_price)` and not `bool`). Reject zero, negative, NaN, and infinity.
    - Validate and clamp `trim_pct` to `(0.0, 1.0]`.
    - Enforce strict quantity conservation: `trim_qty = min(qty, max(1.0, float(int(round(qty * trim_pct))))))`. Remaining quantity cannot become negative.
- **Payload Lineage**:
  - Real callers in entry, trim, and exit pass `holding_id`, `flow_id`, `parent_trace_id`, and standard `quantity` to strategy logger.

#### [MODIFY] [`plugins/analyst_trader/db.py`](file:///Users/admin/repos/hermes-agent/plugins/analyst_trader/db.py)
- **Zero Cash Fallback Bug**:
  - Lines 827 and 859: Replace `float(p.get("cash_balance") or 100000.0)` with `float(p.get("cash_balance") if p.get("cash_balance") is not None else 100000.0)` so an actual $0.0 cash balance is not inflated to $100,000.
- **Total Value Formula**:
  - In `update_portfolio_balance`: Set `total_value = new_cash + open_market_val` (matching `get_portfolio_stats`), instead of `new_cash + realized_pnl`.
- **All-Path Put Accounting**:
  - Check and ensure `price_updater.py` and any dormant copy paths compute long put ROI consistently (`(entry - current) / entry`).

---

### Component 3: Production Monitor-Driven Lifecycle & Identity Matching

#### [MODIFY] [`skills/financial/autonomous-trader/scripts/autonomous_risk_manager.py`](file:///Users/admin/repos/hermes-agent/skills/financial/autonomous-trader/scripts/autonomous_risk_manager.py)
- **Scheduled Monitor (`monitor_and_update_positions`) Alignment**:
  - Ensure `monitor_and_update_positions` filters `WHERE (is_quarantined = 0 OR is_quarantined IS NULL)`.
  - **Runner Stop Loss for TRIMMED Positions**:
    - When an active holding has `status == 'TRIMMED'` (or `previous_outcome == 'WIN_TP1'`), use the holding's actual `target_sl` (breakeven entry price) and `target_tp2` rather than recomputed generic DTE thresholds.
    - If `executable_bid <= holding['target_sl']`, trigger breakeven stop loss exit in `portfolio_engine` and update final outcome.
  - **Exact Contract Identity Matching (`_match_holding`)**:
    - Strictly check: `ticker`, `strike`, `call_put`, AND `expiration`.
    - If `flow_id` is present on both, match on `flow_id`. Prevent matching across different expirations (e.g. 2026 flow closing 2027 holding).
  - **Execution Before Telemetry**:
    - Execute portfolio exits/trims transactionally before or alongside outcome updates; do not allow ledger failures to be swallowed while claiming terminal outcome.
  - **Pass `db_path` to Logger**:
    - Forward `self.db_path` to `log_event(...)` at lines 288-303.

---

### Component 4: Strategy Journal Lineage & Append-Only DB

#### [MODIFY] [`plugins/analyst_trader/strategy_logger.py`](file:///Users/admin/repos/hermes-agent/plugins/analyst_trader/strategy_logger.py)
- **Standardized Quantity Extraction**:
  - Extract `quantity = payload.get("quantity") or payload.get("trimmed_quantity") or payload.get("closed_quantity")`.
- **Acknowledge Persistence**:
  - If `db` is unavailable or `save_recorded_strategy` raises an exception, return `None` (do NOT return a trace ID as if persistence succeeded).

#### [MODIFY] [`plugins/analyst_trader/db.py`](file:///Users/admin/repos/hermes-agent/plugins/analyst_trader/db.py)
- **Append-Only Journal (`save_recorded_strategy`)**:
  - Prevent silent overwrites of trace IDs. If caller supplies an existing `trace_id`, generate an appended unique identifier (`{trace_id}_{uuid[:6]}`) and preserve `parent_trace_id = trace_id`.

#### [MODIFY] [`plugins/analyst_trader/analyst_learning.py`](file:///Users/admin/repos/hermes-agent/plugins/analyst_trader/analyst_learning.py)
- **Persistence of Learning Fields**:
  - In `upsert_analyst_profile`, persist `total_trades` and `preferred_direction`.
  - Calculate ROI across trims as quantity-weighted average rather than unweighted average.
  - Distinguish observed from censored/open trades in statistics.

---

### Component 5: Truthful API & UI Aggregation

#### [MODIFY] [`hermes_cli/web_server.py`](file:///Users/admin/repos/hermes-agent/hermes_cli/web_server.py)
- **Truthful Error Handling on DB Failure**:
  - In `/api/analyst-trader/portfolio`: If database fails or is corrupt, return HTTP 500/503 with `{"ok": false, "error": str(e)}`. Never invent $100,000 cash balance and return 200 with `ok: true`.
  - In `/api/analyst-trader/portfolio-holdings` and `/api/analyst-trader/strategies`: Raise HTTPException on database failure rather than silently returning `[]` with `ok: true`.
- **Chart Confinement**:
  - Support both `charts` and `flow_charts` directories under `get_hermes_home()`.
  - Return HTTP 403 Forbidden for path traversal attempts (`..` or files outside storage dirs).

#### [MODIFY] [`web/src/pages/NotableFlowPage.tsx`](file:///Users/admin/repos/hermes-agent/web/src/pages/NotableFlowPage.tsx)
- **Truthful Trade Aggregation (`getStrategyStats`)**:
  - Aggregate closed trades by unique `holding_id` with `status = 'CLOSED'`, summing realized P&L across all tranches/legs.
  - A position is a WIN if cumulative realized P&L > 0.
  - If closed trades == 0, display "Awaiting Data" (or "0 closed trades"), never default to "100.0%".
- **Truthful Balance Fallbacks**:
  - Lines 1763, 1771: Check `!= null` rather than `|| 100000`. Show $0.00 if cash is zero.
- **Truthful Directional Bias**:
  - Line 2089: If `directional_bias` is missing, display `"NEUTRAL"` or `"—"`, NOT `"BULLISH"`.

---

### Component 6: Test Suite Hardening

#### [MODIFY] [`tests/test_ai_trader_remediation_suite.py`](file:///Users/admin/repos/hermes-agent/tests/test_ai_trader_remediation_suite.py)
- **Hermetic Isolation**:
  - Ensure test fixture defines `DISCORD_BOT_TOKEN="mock_token"` and isolates `.env` so `flow_ingestion_engine` and `discord_poster` never touch `/Users/admin/.hermes/.env`.
- **Production Caller Tests**:
  - Test `monitor_and_update_positions()` directly for TRIMMED positions hitting breakeven stop loss ($4.00 entry -> $5.32 TP1 trim -> $3.80 bid -> closed at breakeven stop).
  - Test `_match_holding` contract matching across different expirations (verify 2027 holding is NOT closed by 2026 flow).
  - Test concurrent same-flow trade executions (thread race) verifying only one holding is created and cash is debited once.
  - Test closed-flow replay verifying duplicate trade is rejected.
  - Test corrupt DB against `/api/analyst-trader/portfolio` asserting HTTP 500 and `ok: false`.
  - Test chart serving with valid chart (200) and path traversal (403).
  - Test quarantine dry-run byte immutability and batch-scoped revert.

---

## Verification Plan

### Automated Tests
Execute the comprehensive test suite in isolated hermetic environment:
```bash
venv/bin/pytest tests/test_ai_trader_remediation_suite.py -v --tb=short
```

Validate specific failure reproduction scripts from the re-reviews:
- Test 1: Quarantine dry run leaves SQLite DB file SHA-256 unchanged.
- Test 2: Concurrent submission of same flow ID creates exactly 1 holding.
- Test 3: Negative trim/exit prices (-$1) and invalid `trim_pct` (2.0) are rejected with ValueError.
- Test 4: Real zero cash balance yields $0.00, not $100,000.00.
- Test 5: Production `monitor_and_update_positions` exits runner at breakeven stop and does not close mismatched expiration holdings.
- Test 6: Corrupt database bytes against web server portfolio API returns HTTP 500 with `ok: false`.
- Test 7: UI aggregation groups by unique closed holding.

### Documentation & Astra Disposition Artifact
Update `/Users/admin/.hermes/reports/ai-trader-remediation-report.md` with finding-by-finding verified dispositions linking every defect to affected files, regression tests, and exact verified outcomes.
