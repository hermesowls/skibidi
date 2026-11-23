# Research MVP controls (unplugged software deployed and verified)

Use the existing CLI from the repository with its existing virtualenv:

```sh
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research --help
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research status --cohort REAL_DATA_RESEARCH
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research cycle --cohort REAL_DATA_RESEARCH --authorize-research --request-budget 0
```

Status reads the selected `~/.hermes/research/config.json` root without migrations, outbox, provider calls or writes. The disconnected cycle performs no write/request. Discord and Skylit report DISCONNECTED deliberately, not failed tests. UW-only selection now uses the existing bounded discovery/intraday transports and coordinator, not legacy startup. Discord/Skylit remain disconnected. This is a manual one-shot authorization, not recurring activation.

```sh
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research cycle --uw-live --cohort REAL_DATA_RESEARCH --root /ABSOLUTE/ACTIVE_HERMES_HOME/research/APPROVED_ROOT --authorize-research --run-id UNIQUE_APPROVED_RUN_ID --profile-db /ABSOLUTE/SAVED_PROFILE.sqlite --profile-version EXACT_VERSION --stages discovery followup --request-budget 2 --max-rows 20 --timeout 10 --date YYYY-MM-DD --window-start AWARE_ISO_START --window-end AWARE_ISO_END
```

Replace placeholders with the explicitly authorized root/profile/date and a current aware time window of at most 300 seconds. `UNUSUAL_WHALES_API_KEY` (or `UW_API_KEY`) must already be present in the process environment; the command never reads credential files or prompts, and missing credentials produce only `MISSING_CREDENTIAL`/presence=false. No credential was accessed in offline verification. Zero budget returns before lookup. Backdated `--now` and all fixture inputs reject this selection. A private Python process-boundary injection requires TEST cohort and cannot admit REAL evidence.

The same cohort/root retains `uw-cycle-state.json` with immutable run-ID parameter bindings and every prior consumed claim. Supply a distinct `--run-id` for each separately approved cycle (1..128 ASCII letters/digits/`_.:-`, starting alphanumeric); never delete claims or make another canonical store. Exact same-ID replay sends zero; conflicting root/cohort/profile/version/stages/budget/window/date/row/timeout parameters reject. Replay with an expired window rejects before writes and still sends zero. Admission and sends are serialized by the existing nonblocking root/cohort lock. Interrupted/ambiguous attempts are consumed, never retried. Recovery of research records/archives and saved intraday responses runs before any fresh send; unresolved recovery blocks sends. A new ID may send within its explicit current window and budget only when no provider stop exists.

**Conservative stop policy:** discovery or followup 429 persists a root/provider stop. Neither new IDs nor elapsed time clear it automatically. Offline explicit migration and audited release are available below; run IDs/flags record intent, **not authenticated permissions**. Existing canonical data is never reset. No DAILY request is selected implicitly. Row cap applies to discovery; intraday retains the existing 1440-row bound.

### Manual offline recovery (no provider calls)

```sh
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research migrate-ledger --root /ABSOLUTE/ACTIVE_HERMES_HOME/research/APPROVED_ROOT --cohort REAL_DATA_RESEARCH --authorize-research
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research recovery-status --root /ABSOLUTE/ACTIVE_HERMES_HOME/research/APPROVED_ROOT --cohort REAL_DATA_RESEARCH --authorize-research
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research release-rate-limit --root /ABSOLUTE/ACTIVE_HERMES_HOME/research/APPROVED_ROOT --cohort REAL_DATA_RESEARCH --authorize-research --run-id EXACT_STOP_RUN_ID --receipt-reference EXACT_RECEIPT_REFERENCE --release-id UNIQUE_RELEASE_ID --reason 'Recorded operator review and decision basis' --operator-decision allow-new-cycle
```

Use `stop.run_id` and `receipt_reference` from recovery-status exactly. Migration is optional and a no-op if no legacy file exists; do not run it to reset canonical data. It atomically retains original bytes as `legacy.original_base64` plus SHA256 and the entire old consumed/ambiguous state under a deterministic `legacy:SHA256` run ID. It sets a conservative unknown-provider stop even for CONSUMED, because old receipts may omit429. Incompatible/corrupt ledgers fail closed. Migration replay does not rewrite evidence.

Review saved receipts and provider policy manually before release. Release requires an explicit operator decision even for unknown/daily quota; no actual quota availability is asserted. Available delta/date Retry-After deadlines must have elapsed according to the process clock; no caller clock accepted. Legacy delta delays conservatively start at migration. Malformed Retry-After or historical delta with no receipt anchor stays closed and requires separate evidence repair/review, not deleting/resetting state. Followup saved429 deadlines are also enforced. Historical followup rate-limited flags/claims remain unchanged; an exact receipt-fingerprint release records the exception. A new429 changes the fingerprint and closes again.

Release and admission share the root/cohort lock; release also locks followup state. Audit intent, reason, stop, observed decision time, deadline and unknown quota are written atomically in the root ledger. Exact release replay is a no-op; conflicting IDs/stale receipts reject, and replay cannot clear a newer stop. No retry, request, credential lookup or automatic fresh-ID cycle is performed. After successful reviewed release, separately authorize a **fresh** run ID with the same-root bounded cycle command above; old runs stay consumed. Never delete history or create another canonical root to bypass a stop.

Explicit measurement configuration (choose your own version, metric, horizon minutes and receipt; these are NOT approved trading horizons):

```sh
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research configure-horizons --cohort TEST --root /ABSOLUTE/ISOLATED/PROFILE/research --authorize-research --version TEST-user-v1 --minutes 1 3 --metric close --received-at 2026-09-24T17:00:00Z
venv/bin/python -B -m plugins.analyst_trader.realdata_cli research update-request --cohort TEST --root /ABSOLUTE/ISOLATED/PROFILE/research --authorize-research --update-json /ABSOLUTE/update.json
```

A watchlist must already exist before configuration or lifecycle updates. Update JSON uses the existing coordinator schema: update_id, ticket_id, setup_id, state, actor{id,kind}, occurred_at, received_at, timeframe, note, evidence_ids. Monitoring additionally requires the existing monitoring_plan; this records caller claims, not operating permission.

Offline TEST cycle inputs:
- `--test-response`: bounded JSON envelope `{source:"TEST_FIXTURE",status:200,received_at:"...",body:{data:[documented option trades]}}`, with `--profile-db`, exact `--profile-version`, and optional aware `--now`.
- `--test-followup`: `{source:"TEST_FIXTURE",evidence_cohort:"TEST",status:200,received_at:"...",body:{data:[{start_time:"...",close:2}]}}`, with explicit `--date` and `--now`.
- `--context-json`: saved native Discord message array, with `--received-at`; no source connection or attachment fetch.
- `--request-budget` must exactly match the number of supplied discovery/followup fixtures (0..2). No retries. TEST inputs reject REAL cohorts. Followup roots must be inside the active HERMES_HOME, enforced by the existing coordinator.

## Finviz-only underlying policy — source repair, not deployed

The `underlying` cycle stage is fail-closed pending a qualified Finviz Elite OHLC/quote adapter. It never selects UW stock history or falls back to another provider. UW remains for whale discovery and option-contract followup. Existing historical UW SPY snapshots and offline saved-artifact replay retain their original provenance. The external coordinator's artifact-free underlying caller returns `BLOCKED_FINVIZ_ADAPTER_UNQUALIFIED` before credentials or transport.

`FINVIZ_API_URL` is present in the operator configuration; its redacted route is `elite.finviz.com/export/screener` (query names `v`, `f`, `auth`; values must never be logged). No consumer or historical OHLC schema was located in the scoped checkout/scripts. API existence is confirmed, not missing credentials. Required next input: documented Elite historical OHLC endpoint and schema, timestamp/timezone and session/completion semantics, adjustment/history limits, plus quote as-of/delay fields and approved authentication binding. A screener export is not a historical candle series.

TEST cycles persist unique ticker queue diagnostics, preserving incompatible legacy UW queue bytes without importing them as Finviz. A REAL underlying-only cycle returns the blocker before UW credential lookup or writes; it does not initialize a live acquisition queue. Mixed stages may still perform explicitly selected whale/options work under existing budget/recovery controls. No Finviz live acquisition, automatic TA completion, deployment or recurring activation is claimed.

## Deterministic acceptance command

```sh
venv/bin/python -B tests/run_mvp_research_guard.py
```

`tests/test_research_cli.py` builds a disposable TEST profile and exercises actual discovery admission -> archive/watchlist persistence -> followup -> native context -> lifecycle update -> explicit outcome configuration -> reader. Only transport and clock boundaries are fixtures; no production DB or real market data is fabricated. Unconfigured horizons remain UNKNOWN.

## Acceptance status

- [x] Existing public CLI: status, configuration, lifecycle updates, bounded disconnected/TEST cycle.
- [x] Integrated-fix guarded suite: 62 passed including prior57, horizon rejection/recovery and live-selector TEST process-boundary cap/replay/failure coverage; final evidence under integrated-fix.
- [x] Existing Tracking API surface displays lifecycle/setup, descriptive outcomes, coverage heuristic and insufficient empirical sample.
- [x] Independent prior mounted frontend selection: 13 passed, zero skips with preserved saved projection; not rerun in this Python-only fix.
- [x] Prior independent integrated review: H1/H2 bounded PASS (62 guarded); ongoing R1 HOLD.
- [x] R1 follow-up: 67 guarded passes (prior62 plus5 named repeat-run tests); no application audit denials. Same-store repeat cycles, conflict/replay, lock exclusion, archive recovery, ambiguous claims, discovery/followup429 stops exercised with TEST process boundaries.
- [x] R1 recovery implementation: 70 guarded tests pass, including prior67; explicit offline migration, reviewed release and later same-root cycles. Evidence: `evidence/r1-recovery/RESULT.md`.
- [x] Independent R1 PASS: 70 guarded +4 report-local probes; final closeout matched all196 reviewed hashes. No live full-MVP claim.
- [x] App and node TypeScript: USEREXTERNALPASS (user-provided exit0; not rerun).
- [x] Final Vite build USEREXTERNALPASS: operator screenshot20.85s exit0; supplied61 files inspected/hashed. No rebuild/reproducibility claim; prior blocked tool attempt remains historical.
- [x] Latest reader/UI deployed on loopback9119, PID73680;60 served asset hashes,auth200/unauth401,full canonical equality, unchanged research DB, paused cron definitions;70 guarded +13 mounted current passes.
- [ ] Discord/Skylit live plugging and qualification, requester identity verification.
- [ ] Authorized real combined-cycle transport and explicit budget/cadence; no activation performed.
- [ ] Empirical point-in-time learning validation; descriptive returns are not edge or trade P&L.

Evidence: `~/.hermes/reports/mvp-closeout/evidence/runner-usability/` includes before bytes, RED runs and final guarded output. R1 and integrated H1/H2 have bounded independent acceptance. Latest deployment and bounded software acceptance are complete. All5 integrated frontend hashes match the nested source_sha256 manifest;195 non-documentation R1 hashes match, with expected documentation-only drift. Current evidence: `/Users/admin/.hermes/reports/mvp-closeout/evidence/final-deployment-20261001T040654Z/RESULT.md`; operator handoff: `~/.hermes/reports/mvp-closeout/FINAL_HANDOFF.md`. No live-source/activation/learned-edge or reproducible-build claim; no background closeout remains.

