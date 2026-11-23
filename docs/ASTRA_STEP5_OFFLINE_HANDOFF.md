Step5 offline integration handoff — BLOCKED, not acceptance

Checkout: /Users/admin/repos/hermes-agent (existing dirty reconciliation checkout).
Evidence: /Users/admin/.hermes/hardening/astra-remediation/step5-integration-20260923-052241
Report: /Users/admin/.hermes/reports/ASTRA_STEP5_RESULT.md

Repeatable commands (installed Python; no installation):
  cd /Users/admin/repos/hermes-agent
  python3 -I -S scripts/verify_step5_offline.py --require-publication

Expected current result: exit 1, one assertion failure: I1 requires actual upstream durable card obligations. This is a RED capability probe, NOT a complete acceptance command. Output gives a fresh disposable evidence directory containing probe.log, summary.json, import origins/hashes and guard denials.

To verify the existing conservative behavior instead:
  python3 -I -S scripts/verify_step5_offline.py
Expected current result: exit 0, one passing abstention probe. This does not certify I1.

Real path exercised
  TEST message -> real Flow parser/raw/notable persistence -> real ARM -> real quant/cache/OFI proxy/directional alpha/orchestrator -> watchlist abstention.
  Same persisted source -> real OWLFRED eval_ticker positive source route -> real ARM and quant -> abstention.
  Duplicate Flow ingestion skips. No durable alert units, transport calls or holdings.
  Only Finviz market-data return, quote observation, chart boundary and TEST transport are supplied. No classifier/ARM/quant/orchestrator/outbox business result is mocked. Transport is never invoked.

Hard blocker
  DatabentoOFIEngine is an explicitly unverified OHLCV proxy, not an observed L2 adapter. DynamicShadowQuantEngine rejects that evidence.
  Independently, ExecutionOrchestrator has no qualified non-L2 verifier/calibrated success consumer and always returns a nonqualifying grade. ARM only invokes publication for an A+ DREAM result. Therefore even replacing the missing L2 adapter alone cannot establish the requested positive producer-to-publication chain.
  Earlier Step2 positive upstream fixtures substitute quant success; those local delivery contracts remain useful but cannot establish the stronger Step5 external-boundary-only claim.
  FlowIngestionEngine and OWLFRED also do not forward explicit learning_context to ARM. This is a separate narrow integration gap, not the sufficient explanation for the unconditional quant gate. No context plumbing was changed while the fundamental positive path is blocked.

Do not make the probe green by replacing quant output, planting a qualified score, suppressing assertions, injecting a hand-built unconnected outbox/holding, or weakening proxy abstention. Do not copy old staging bytes into this shared checkout.

Parent/owner decisions required
  Parent independent reviewer: reproduce the blocker on exact current bytes, confirm the source/gate diagnosis, and assess whether a narrowly scoped policy design can legitimately separate explicit TEST publication from unqualified strategy scoring without misrepresenting confidence. This is a design decision, not an approved implementation here.
  Amar: choose a separately scoped missing-capability effort or explicitly revise the integration acceptance contract. Do not describe either as Step5 completed. Missing provider implementation/strategy qualification is not authorized by this handoff.
  IDE implementer after that decision: preserve accepted Steps1–4, immutable before bytes and single-writer discipline; TDD context injection only if needed by the approved path; resume the complete shared-dataset chain and adverse matrix, not a sum of unit suites.

Remaining I1/I2/I3 work
  Registered/as-of policy via producer, classifier/ARM recorded decision, durable card obligations, partial/rejected/unknown transport, restart/no-resend receipts, separately authorized option simulation, entry/unequal trim/close journals, observed costs and corrections, idempotent importer/proposal/replay, actual authenticated complete-history APIs and mounted exact API snapshots remain unverified as ONE chain.
  Gain/loss economic traces, integrated adverse cases, two deterministic successful chains, protected-suite identity deduplication, installed frontend typecheck/disposable build and mounted UI must follow the blocker resolution. None ran in this blocked slice. No browser E2E claim.

Operational boundaries and later manual-only work
  The active-profile cron snapshot shows disabled/paused jobs. This does not mean servers are off: ai.hermes.gateway was listed with PID 78961, last status 75. No interpretation as health qualification. Existing Python/Node/MCP processes were untouched; dashboard loaded code may be stale. No process argv/env, plist content, DB, secret or HTTP read was needed.
  Three installed external flow scripts have no matching checkout filename and are not covered by checkout acceptance. Hash inventory is in runtime-inventory.json; do not deploy/copy over them. Plist existence does not prove a loaded scheduler. Production historical DB immutability remains unknown.
  Later owner approvals must separately cover: consistent DB backup and disposable migration rehearsal; bounded real UW quota/calendar/quote and Skylit observation validation; exact destinations and explicitly approved test delivery; reviewed deployment mapping and staged restarts; rollback artifacts and controlled soak. No traffic here, so current quota/data quality/entitlements remain unknown.
  Distinguish TEST prototypes, reviewed checkout, installed runtime scripts/packages, scheduler, unavailable provider adapters, local option paper simulation and real broker execution. No broker/live-trading or autonomous policy-promotion qualification.

Inherited immutable acceptance references
  /Users/admin/.hermes/reports/ASTRA_STEP3_CLOSEOUT_INDEPENDENT_REVIEW.md
  /Users/admin/.hermes/reports/ASTRA_STEP4_FINAL_INDEPENDENT_REVIEW.md
  Earlier Step1/Step2 evidence remains inherited through those scope statements, not newly rerun or recertified here.

Changes in this slice: new bounded test, new guarded runner, this handoff only. No application implementation fixes or accepted-source modifications. Full final acceptance, profitability, statistical edge and production readiness are NOT claimed. Parent independent review is still required.
