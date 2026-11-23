# Step5 Kian connection repair — offline candidate, independent review pending

Mission: observable whale discovery -> transparent flow/GEX/TA evidence -> separately authorized paper tests -> trustworthy economics, learning and UI. Candidate qualification is not a confirmed setup, A+ grade, probability, or execution permission.

## Provenance and policy

Historical local `run_uw_kian_one_ticker.py:kian_pick` used premium >= $50,000, size >= 500, volume > Open Interest, ask-side preference and premium sorting. It did not enforce OTM or DTE. A separate historical scan used <=14 DTE. These are recovered local implementations, NOT independently verified canonical Kian rules. The installed kian_analysis wrapper is not an authority or executed integration.

`plugins/analyst_trader/kian_research.py` accepts only explicit registered `stated_policy`, `paper_test`, schema 1, `TEST_OFFLINE_ONLY`, `recovered_local_plus_test_proposals` profiles whose canonical policy hash matches the request and profile. Registration/as-of validation comes from the existing learning store. No production default/profile is activated. A hash establishes immutable configuration identity, not proof of original strategy authorship or cryptographic owner authentication.

TEST fixture proposals: DTE 0..40, OTM distance >0 and <=10%, evidence age 120 seconds, UTC calendar, simple trades only. These values exercise validation and are NOT approved live trading thresholds. Premium is single-print USD; size single-print contracts; volume aggregate contract-session contracts. Known zero OI is valid; missing OI is INCOMPLETE. Calls require strike > as-of spot, puts strike < spot. DTE is expiration minus decision/analysis calendar date, not spotted date. Unknown required fields do not become zero/pass. Reported ask is not verified buying; execution-time fill/IV and next-session OI remain separate unknowns.

## Real caller connections

FlowIngestionEngine and OWLFRED expose optional learning_context, research_context and execution_decision. Default omitted contexts preserve abstention. Actual ARM evaluation creates a separate research result and source-specific persisted cohort observation; the quant A+ path is unchanged and unavailable. Qualified explicit research may publish through the existing durable outbox, with independent publication authorization. Rejected/incomplete baselines are retained. Both source and raw-source hashes follow candidate evidence; delivery resume rechecks those hashes as well as existing quarantine/contract guards.

Execution still requires the existing explicit option-paper intent, source/policy/decision alignment, quote/risk controls and registered TEST lifecycle. Publication alone does not execute. Learning registration alone does not publish. Recommendations carry research provenance and cards label TEST/offline research, not confirmed setup. Existing UI is not redesigned; mounted evidence validates its real economic API consumption.

## Deterministic technical evidence

KIAN-TA-v1 uses EMA periods 8,21,50,100,200, seeded with the first period's SMA, then EMA[t] = EMA[t-1] + 2/(period+1)*(close[t]-EMA[t-1]). At least 201 bars are needed for current/previous EMA200 slope. Price states compare previous close to previous EMA and current close to current EMA: cross from <=0 to >0 is reclaim; >=0 to <0 is loss; strictly positive/negative at both is hold above/below. Equality is at EMA. The price plus five EMA stack is bullish/bearish only when strictly ordered, otherwise conflict. EMA50 price trend and EMA100/200 context are explicit.

TTM-style variant, not claimed proprietary-identical: BB20 uses SMA close, population standard deviation and multiplier 2. KC20 uses SMA close and SMA true range times 1.5; true range includes previous-close gaps. Strict BB-inside-KC is squeeze on; equality is off. Release is previous on/current off. Momentum is the 20-bar least-squares endpoint of close minus the mean of Donchian midpoint20 and SMA20. Momentum sign, change and fading magnitude are separate from compression/direction.

Candles require source/evidence/ticker/timeframe/as-of, finite valid OHLCV, sorted unique timezone-aware completion times, completed bars only, interval continuity, warmup and freshness. Registered TEST TA settings bind timeframe/interval/max-age; a caller cannot relax them. Hourly and daily are supported separately, not blended. Daily-regime/hourly-setup combination remains an operational proposal, not an approved rule. Session gaps currently return UNKNOWN; no calendar adapter/imputation is introduced.

Observed GEX requires explicit ticker/source/evidence/timeframe/time and levels. King/OPEX nodes are targets/pins, never entries; directional gatekeeper/negative walls indicate conflict, room is distance to target. Missing GEX is UNKNOWN, not a bearish conclusion. TA/GEX availability/alignment does not assert probability or learned edge. Baseline and enhancement statuses are stored separately.

## Paper lifecycle and learning

TEST lifecycle: explicit source-matched owner-test trigger, four option contracts, entry fixture $2, stop $1, TP1 $4, TP2 $6, max hold 86,400 seconds, quote max age 60 seconds, evidence-backed explicit partial/final exits, observed costs required before net learning. Max-hold is a recorded caller-driven deadline, NOT a new autonomous scheduler/executor. Operational enforcement/thresholds need owner decisions before any live deployment.

Shared dataset: gain and loss sources run real Flow and OWLFRED research evaluations. Explicit Flow intent enters options through the real portfolio engine; three-versus-one and one-versus-three unequal exit tranches exercise gross +500/-100 and observed $4 cost each, net +496/-104. Combined net is +392. Terminal runner-loss labels do not override total economics. Existing importer, correction, proposal and replay paths execute. Proposals remain exploratory and cannot authorize execution. Baseline/enhancement cohort comparisons are hypotheses, not statistical edge claims.

## Reproduction and review

Use `python3 -I -S scripts/verify_step5_offline.py --tests test_step5_kian_repair,test_step5_kian_technicals,test_step1_execution,test_step2_delivery,test_step3_learning,test_step3_tracer,test_step4_statistics,test_step4_mark_contract` from the checkout. Installed venv only; runner creates disposable HOME/HERMES_HOME/cwd/databases, scrubs environment, audits prohibited access, and fails on retained swallowed application denials. Synthetic guard selftests are recorded. The blocked urllib3 IPv6 dependency probe is separately identified.

Run the unchanged legacy `test_step5_upstream_boundary` in a fresh runner process: shared quant call-budget exhaustion otherwise changes its precise abstention reason after the many research tests. No assertion was weakened. Additional protected closeout/correction/temporal tests are listed in the repair result.

`python3 -I -S scripts/verify_step5_kian_ui.py <runner-evidence-directory> <new-log-path>` mounts the unchanged React page from the exact authenticated ASGI strategies/portfolio JSON generated by the connected run, including refresh-error state. No real HTTP/listener or handmade economics fixture.

Independent acceptance remains required. The checked-in runner's historical default and summary scope text remain blocker-probe wording; explicit test selection plus the new repair report define this candidate's scope. Reconciler Git/process integration tests are intentionally not run under this no-Git-mutation task. No providers, brokers, notifications, service/config/cron changes, installs, deployments, or served web_dist edits.

Owner decisions before operations: exact DTE range and calendar zone; OTM cap; source/premium/size semantics and complex handling; source-specific freshness/session calendar; daily/hourly combination; independent publication/execution approval mechanism; entry trigger/invalidation, sizing, stops/targets/max hold, quotes and costs. No additional approval is needed to review this offline candidate.
