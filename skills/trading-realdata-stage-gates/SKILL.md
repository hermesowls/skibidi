---
name: trading-realdata-stage-gates
description: "Use when gating trading real-data validation stages."
---

# Trading real-data validation expectations

Amar explicitly expects Stage 3 to use actual provider observations only. Synthetic fixtures, documentation examples and hypothetical previews are never market evidence or a substitute for failed provider access.

Isolated development tests may use clearly labelled TEST fixtures. Keep their records and conclusions separate from real-data research. Missing evidence remains Unknown/Incomplete, and provider failures are reported directly. Successful observation ingestion does not establish a qualified trading signal.

## Requirement-to-evidence traceability

Amar expects medical-device-style DTM discipline for trading work: high-level need → product requirement and acceptance criterion → spec/design output with module/script and mechanism → automated protocol with exact test module/class/method → passing report. Keep verification, real-use validation and deployment statuses independent. A method existing is not proof it ran; a broad suite PASS cannot silently fill a missing per-requirement trace. Label legacy, Astra-new and Astra-modified only with supporting provenance. Proposed cadence, storage and architecture remain draft until approved. Same-agent workbook readback is document-structure verification, not independent product review.

Build a populated canonical JSON baseline and filterable workbook, with explicit UNMAPPED/NONE links and a gap register. Persist a skeleton and bounded evidence batches early so interrupted workers leave recoverable output. Check referential integrity, exact test symbols, report hashes and reviewed-manifest identity before delivery; do not sum overlapping suites. A current matching hash is identity evidence, not a fresh test execution. See `references/dtm-evidence-gates.md` for the operational trace procedure.

## Bounded historical followup verification
For the existing research coordinator, use the exact `BoundedUWIntradayTransport` identity and dedicated intraday worker rather than widening the option-trades worker route. Public documented intraday `date` supports current/past trading dates; save request-date, raw bytes/hash, receipt and source separately from as-of. Closed-session historical reads are not market-fresh discovery. A one-shot manual ledger must preclaim the total request cap and refuse reruns; preserve ambiguous failures without automatically retrying. Read the exact canonical snapshot BLOB back after ingestion. Run `tests/run_mvp_research_guard.py` for coordinator tests; actual OS-worker lifecycle tests require `tests/stage2_worker_guard.py`, not the socket/process-denying card guard. Do not weaken guards to fix runner-precondition failures.

## Discovery test design and honest reporting
Before scheduling a real-data test, verify that the actual request targets the approved economic profile. A latest-N unfiltered tape sample is a connectivity/admission probe, not a whale-discovery validation. Trace saved-profile filters through the actual caller, transport validation, worker and HTTP boundary; record the exact query with the observations. Server filtering is not independent local confirmation.

When a run is incomplete, diagnose saved raw observations first without spending another market request. Report separate per-threshold pass/fail/unknown counts alongside freshness and semantic-evidence blockers. A preliminary missing-field gate must not conceal independently observable economic failures. Distinguish fields absent upstream from valid raw fields suppressed by canonicalization; keep diagnostic results separate from qualification.

Amar expects plain-language budget reporting: say 'the authorized one-request budget was consumed', not simply 'exhausted'. Do not imply a provider quota failure, no qualifying activity across the market, or a full-session scan without evidence. Freshness failures and economic threshold failures are different findings.

For the reproducible saved-response diagnosis and request-change gates, see `references/discovery-validation.md`.

Communicate scoped feature acceptance separately from whole-stage readiness, deployment and operational activation. Finish the approved stage with focused independent review; do not imply a subfeature PASS closes remaining operational gates.

Request explicit approval for project-local dependency installation when outside approved scope. Such approval does not authorize global installs, dashboard restarts, deployment, live trades or cron activation. Keep a record of dependency changes and disclose pre-existing conflicts without silently repairing unrelated packages.
