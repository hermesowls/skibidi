# Step 1: local paper execution and monitoring contract

Scope: local SQLite simulation only. This interface cannot submit a broker order. It does not authorize live execution, publishing, learning, deployment, or scheduler activation. No production session/provider has been qualified.

## Entry caller

`DualPortfolioEngine(explicit_database).execute_autonomous_trade(decision, account_tier='growing', now=aware_datetime)` consumes a caller-owned immutable decision. `now` defaults to aware UTC; tests can supply an explicit clock. The engine snapshots the validated decision rather than retaining a mutable caller dictionary.

Required decision fields:

- `execution_authorized` must be the boolean `True`, specifically authorizing this paper simulation. Absent, false, numeric/string truthiness, and non-paper modes fail closed.
- `execution_mode` must equal `paper`.
- Nonempty stable `intent_id`, `flow_id` (actual immutable source event), `parent_trace_id` (actual upstream decision identity), and `policy_version`. These are caller-owned identities, not synthesized from ticker/strike or inferred from a conviction score. No new policy registry/learning system is implemented.
- `ticker`, positive OCC-representable `strike`, `call_put` exactly `C` or `P`, canonical ISO `expiration`, and exact matching `occ_symbol`. Compact OCC and correctly six-character-padded OCC are supported; malformed symbols are not repaired. Original tokens remain in the stored payload.
- `entry_price` matching the observed quote ask. Targets `tp1_price`, `tp2_price`, `stop_loss_price` must satisfy `0 < stop < entry < TP1 <= TP2`; absent targets retain the existing execution defaults. Optional `quantity` must be a positive integral contract count; absent quantity retains existing tier sizing.
- `risk_limits`: explicit existing `SimulationLimits` fields `max_order_notional`, `max_gross_notional`, `max_positions`, `max_evidence_age_seconds`. All are positive and bounded; positions is an integer. No test threshold becomes a runtime default.
- `quote`: complete contract identity above, matching `flow_id` and `intent_id`, nonempty `quote_id` and `source`, `evidence_status='observed'`, aware ISO `observed_at`, positive finite `bid` and `ask`, and `bid <= ask`.

Freshness requires `0 <= now-observed_at <= max_evidence_age_seconds`. No bid is synthesized from last, midpoint, estimated prices, or a haircut. The caller is responsible for truthful upstream evidence; a dictionary is not broker authentication.

Before any new cash debit, under the entry `BEGIN IMMEDIATE` lock, `flow_id` must identify an already persisted `notable_flow` source with exactly matching ticker/strike/right/expiry, `final_outcome='MONITORING'`, and no parent or linked analytics quarantine. The database's existing NULL/0 quarantine convention means unflagged; any other parent value denies admission. No source is synthesized or repaired from the execution intent. Concurrent source writers serialize behind this lock; a change committed before admission is observed. Exact completed-intent receipt replay precedes requalification and never debits again.

Expiry policy is deliberately date-only: a new entry is denied if expiration is earlier than the aware execution clock's date in `America/New_York`. Same-day and future dates are eligible for the remaining gates, including across the UTC/local date boundary. This conservative stale-date exclusion does NOT assert exchange sessions, holidays, early closes, AM/PM settlement, last-trading-time or after-hours tradability. No calendar/settlement capability is implemented. A fresh quote cannot make a prior-local-date expired contract admissible. Already admitted exact receipt replay remains available after expiration.

The ARM evaluator accepts `execution_decision=` (or an upstream `quant_result.execution_decision`). It validates the decision against the evaluated contract, persists its supplied parent decision identity before execution, and passes the decision through without manufacturing permission. If the upstream decision lacks a version, the caller must supply `execution_policy_version=`; otherwise it abstains. Score/DREAM/publication success never grants execution permission. Invalid admission is logged and returned as `paper_trade=None`.

The broad `scripts/validate_full_workstream.py` caller likewise requires an explicit matching `execution_decision`, supplied source record, lifecycle quote reader and aware clock; its demo data/score cannot grant permission. Its focused `execute_validation_transition` caller is tested independently. The broad runner was NOT invoked for step 1 and is not the guarded tracer.

## Risk, economics and replay

Existing constraints are shared, not replaced by speculative strategy thresholds: ARM's $200 micro-contract affordability gate, `RiskManagementAgent`'s existing 1.5% per-trade equity risk cap, and explicit `SimulationLimits` order/gross/position caps. For long options the full premium is the theoretical maximum loss; a stop is not a guarantee. Available cash and portfolio exposure are checked under the same write lock.

All raw/derived persisted amounts are finite and bounded by the SQLite REAL exact-integer envelope (`2**53 - 1`); bools and fractional option contracts are rejected. Underflow that cannot debit cash is rejected. Decimal input arithmetic is converted once to SQLite REAL, without display-cent rounding of cost or tranche PNL. SQLite REAL remains the existing storage representation, not arbitrary-precision accounting. Both long calls and long puts gain when premium rises. Actual zero cash is preserved.

Entry, trim, exit: one `BEGIN IMMEDIATE` connection owns holding, cash/equity and economic journal writes. A journal error propagates and rolls back economics. A late SQL failure rolls back journal and economics. Caller-owned journal connections are never independently committed. Standalone durable trace exact-replay/conflict behavior is preserved.

An entry retry returns the original receipt, including after closure or under concurrency. Any changed intent payload/tier or reused source for another intent fails. This deliberately compares the full supplied intent (including policy/quote identity), not merely ticker/price. Fresh quote age is checked on first execution; an exact receipt replay need not requalify an already completed fill.

Trim and exit each have one durable economic operation identity per holding. Public `execute_autonomous_trim(holding_id, quote=envelope, now=aware_clock)` and `execute_autonomous_exit(...)` require complete observed quote evidence, including holding/source/intent lineage. They delegate to the SAME monitor transition; raw economic code is inline behind that boundary, with no caller-owned `_connection` route. Optional numeric `current_price` must equal observed bid. Optional exit `outcome_label` must equal the selected transition, not authorize it. A trim request requires OPEN/TP1, an exit request requires the stop or TRIMMED/TP2; an OPEN one-contract TP1 is a terminal trim (`CLOSED_TP1`). Valid `trim_pct` is `(0,1]`, default 0.5; rounded whole contracts are conserved. Direct freshness defaults to the persisted entry limit; any supplied tighter limit is honored, never a looser override.

Exact quote replay returns the saved economic receipt to direct callers, even after closure or expiry; monitor replay returns no new update. Changed evidence under the same quote ID conflicts. A requested different operation, trim fraction or outcome cannot reuse that receipt. No fresh quote can replay economics on a closed position. Legacy fractional/corrupt holdings do not execute. Low-level autonomous add/trim/close APIs cannot bypass the journaled caller. Generic research marks are not executable evidence and update stored portfolio equity atomically.

## Scheduled monitor

`AutonomousRiskManager(..., quote_reader=reader, quote_max_age_seconds=explicit_limit, clock=aware_clock)` is the configuration contract. No runtime config/service was changed. The existing scheduled `monitor_and_update_positions()` and `process_price_update(holding_id, quote_envelope)` use the same shared transition logic. Default reader/freshness absence abstains. The quote-reader boundary receives the holding and returns observed evidence or None; no live provider adapter is added here.

Monitor envelopes additionally require exact `holding_id`. The monitor verifies immutable entry intent, holding contract and source flow contract/expiry, quarantine/outcome state, and complete quote provenance. Unknown/stale/future/naive/malformed/crossed/no-bid evidence cannot advance outcomes. Stored research marks remain usable for research but are never relabeled as an observed bid.

Transitions use persisted targets checked against admitted policy: OPEN -> TP1 partial and stop at entry -> runner TP2, or actual bid stop. A one-contract TP1 closes all contracts. A losing gap below the runner stop is `LOSS_STOP_HIT`, not falsely breakeven; exact entry-price stop can be `CLOSED_BREAKEVEN`. First lifecycle observation must be at or after BOTH admitted entry observation and execution timestamps. Same-tick first transitions are explicitly supported (aware instants, not string ordering); subsequent observations must be strictly newer than the last committed monitor event. This persists across restart and direct/monitor interleaving. No duplicate exit occurs on concurrent retry.

Economic mutation, corresponding monitor/outcome journal event, and `notable_flow` outcome/excursion update share one transaction. Missing/mismatched holdings never update a source outcome. Monitor code does not call the publisher. No delivery/outbox/learning/UI/reconciler implementation is included.

## Offline evidence

Dedicated tests: `tests/test_step1_execution.py` and `tests/test_step1_closeout.py`. TEST-only helper fixtures: `tests/step1_fixtures.py`. Real public execution, real ARM caller, scheduled monitor, focused validator caller and SQLite are exercised; only external inference/publisher construction and quote data boundaries are substituted. A SQLite trace callback observes locking without replacing business logic. No extracted AST or mocked economic outcomes. Sources are persisted before entry, not retrofitted after debit.

The tracer supplies a fixed aware TEST clock (2026-09-19T06:00:00+00:00), observed TEST entry ask 4, TP1 bid 5, then a fresh bid 6 ten seconds later. Its explicit TEST freshness limit is 60 seconds, not a broker claim or production default. Actual persisted receipts/holding/equity/journal reconciliation are emitted as `STEP1_TEST_TRACER` in guarded logs.

Use the evidence directory's `guarded_tests.py`, not an unguarded operational command. It launches with a scrubbed environment, temporary HOME/HERMES_HOME/SQLite, and denies network/process creation, secrets/default-profile databases and non-sandbox writes. Denied attempts remain failures even if application code catches them. A separate synthetic audit-event self-test intentionally exits 1 to prove swallowed-network detection without performing networking.

Implementation evidence is not independent certification. Parent review is required before relying on or integrating these changes. No scheduler/provider/broker/live-session qualification is claimed.
