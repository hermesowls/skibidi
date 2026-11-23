# Step 2: durable alert delivery (local code contract)

This is not deployment approval. No live notifications, trading, cron, service, gateway or production migration was exercised. Step 3 is not authorized.

## Caller graph and compatibility

`flow_ingestion_engine.py` and `owlfred_engine.py` call the real `AutonomousRiskManager.evaluate_candidate_end_to_end`. The evaluator calls `publish_actionable_alert`, which now uses `_publish_cards -> AlertOutbox.enqueue -> AlertOutbox.drain -> transport`. The public Telegram and position-guidance wrappers use the same outbox. Paper monitors still do not publish automatically. No generic Discord poster or default gateway behavior was changed.

The existing gateway ledger was inspected but is not compatible: it deliberately permits sends when persistence fails, replaces obligations, and replays ambiguous deliveries with a marker. Step 2 instead uses the analyst producer's existing SQLite database and BEGIN IMMEDIATE source-admission pattern. Three additive tables (`alert_messages`, `alert_units`, `alert_resolutions`) are initialized on explicit publisher use. Existing Step 1 tables/contracts are unchanged.

## Explicit inputs, not global discovery

Construct ARM with an explicit database, `delivery_destinations` (platform/destination pairs), `delivery_transport` and optionally `delivery_clock` (epoch seconds). `ProviderTransport` accepts explicit Discord/Telegram tokens; it never loads environment files or discovers default-profile credentials. The default constructor does not instantiate the old Discord publisher.

Pass `publication` to the evaluator or publisher with:

- `publishing_authorized` exactly `True` (distinct from `execution_authorized`).
- Stable `alert_id`, positive integer `revision`, `policy_version`, `flow_id`.
- For revision > 1, a nonempty `revision_reason` and an existing immediately preceding revision.

Upstream callers do not manufacture this decision. Calls without permission remain denied. A deployment integrator must obtain an explicit policy decision and configure destinations/transport; no hardcoded permission bypass was added. The old on-demand invented ATM candidate is no longer used by `eval_ticker`.

### Usable upstream dependency contracts (no live enablement)

`FlowIngestionEngine(db, publication_policy=policy, delivery_destinations=destinations,
delivery_transport=transport, delivery_clock=clock, quant_engine=quant,
deep_dive_analyzer=llm, observation_reader=read_observation,
chart_loader=load_chart, discord_token=token)` retains its actual `_process_message`
ingestion path. `policy(source)` receives the just-persisted flow record and must
return the explicit publication dict above, or None to deny. Its flow_id must
equal the saved source; alert_id/policy_version are never invented by the engine.
`read_observation(parsed, raw_message)` returns observed `entry_price` and
`spot_price` (aliases contract_price/underlying_price supported), not contract
identity or permission. The entry is saved as entry_contract_price. No observed
entry means no evaluator call. External adapters must supply real observations,
not estimates. `load_chart(**attachment_metadata)` controls chart enrichment;
chart storage is not a request to deliver media. The upstream evaluator now
explicitly requests text (`image_path=None`; ARM uses use_graphic_card=False).
`last_evaluation` exposes the actual evaluator result; ingestion's boolean still
means saved, not delivered. Missing policy denies even an A+ result.

`owlfred_engine.eval_ticker(ticker, db_path=path, flow_id=source_id,
publication=decision, delivery_destinations=destinations,
delivery_transport=transport, delivery_clock=clock, quant_engine=quant,
deep_dive_analyzer=llm, observation_reader=read_spot)` reads the actual persisted
source from that DB, checks ticker/source eligibility, and uses its exact
strike/right/expiry/premium/observed entry. `read_spot(source)` returns a positive
observed spot_price. Missing source/permission/observed economics abstains; no
Finviz fallback, estimated entry/premium, synthetic strike, or default permission.
Bare CLI `eval` has no configured authorization and cannot publish. The callable
returns a structured result. Quant and LLM injected objects implement ARM's
existing evaluate_ticker_complete_quant and analyze_candidate_deep_dive methods;
only these external enrichment boundaries are replaced in offline tests.

For restart, call `engine.resume_publication(original_decision, limit=1..100)` or
`owlfred_engine.resume_publication(original_decision, db_path=path,
delivery_destinations=destinations, delivery_transport=transport,
delivery_clock=clock, limit=1..100)`. This is an explicit producer-level API,
not a scheduler. Duplicate raw ingestion still returns false; callers must use
this resume path for outstanding delivery. It loads persisted outbox identity,
requires the exact original decision/source/policy and destination obligations,
and drains stored payloads only. It neither calls the policy/observation/quant/LLM
boundaries nor regenerates recommendations/paper orders. Changed config is a
conflict, missing publication blocked, absent permission denied. Existing
send-intent source/quarantine checks and unknown-no-resend semantics apply.
Caller authorization is a trusted integration boundary, not authentication.

Source identity must match persisted notable flow, remain MONITORING, and have neither parent nor linked quarantine. Admission is checked under the enqueue write transaction and again under the send-intent write transaction. This is an admission boundary, not a lock across remote I/O: later administrative changes cannot retract a send already admitted. Position guidance requires the original eligible source recommendation and an explicit exact compact uppercase OCC display identity matching its ticker/expiry/right/strike. ARM's `_position_source_subject` adapter validates the source representation before forwarding a copy with all source fields retained. The canonical ticker, expiration (ISO date), call_put (C/P), and strike are required. Each optional source symbol field is independently checked, even if the other is absent: `contract_symbol` accepts compact OCC or exactly the producer's `f'{ticker} {strike:g}{call_put} {expiration}'` readable label; `occ_symbol` accepts compact OCC or exactly the same OCC with its ticker right-padded with spaces to six characters. No trimming, case-folding, parsing/repair of unknown labels, or ignoring conflicting/empty/null supplied fields is permitted. For example, unchanged evaluator fields `contract_symbol='TEST 100C 2026-10-16'` and `occ_symbol='TEST  261016C00100000'` are compatible with the separate required display argument `contract_symbol='TEST261016C00100000'`. The padded source form is not the display input representation: passing that padded literal as the displayed argument is rejected rather than normalized. Source fields must in turn match the persisted eligible row before any units are created. It is research guidance, not proof of a paper/live fill. Closed-source lifecycle notification integration is not introduced.

## Durable identity and results

The complete recommendation, authorization, ordered required destination set and card payloads are canonicalized and stored atomically. Unit key = alert + revision + platform + destination + card. Exact replay cannot reset progress; same-key changed payload/required destinations raises `ALERT_ID_CONFLICT`. Revisions are intentional new messages, never automatic retry IDs.

Publication consists of two durable text cards (open/thesis and risk/sizing). The old untracked asynchronous graphic patch is removed. Text-only support is an explicit restriction: `publish_actionable_alert` defaults to `use_graphic_card=False`; any supplied image_path/card_image_path (including empty or missing paths) or explicit graphics request returns `status=unsupported`, `capability=text_only`, `media_delivered=False`, and no units, before enqueue or transport. Paths are not opened. Supported completed text results also label capability=text_only and media_delivered=False. A changed image request cannot replay a complete text result. No graphics or attachment delivery is claimed by this milestone.

Publishers return a structured aggregate and full unit states/receipts, not Telegram OR Discord. The evaluator preserves `alert_published` as true only for `complete`, and returns `alert_delivery` for the structured result. Missing permission is denied; absent destinations blocked; unconfigured provider permanent failure, never success. Enqueue is pending, not delivered. Audit/analytics publication booleans are observations of completion, not durable retry controls; the outbox is authoritative.

## State, retry and concurrency

Units are pending, inflight, succeeded, retryable, permanent or unknown. They retain attempts, next retry, claim, lease, send intent, provider receipt, last error and update time. All required units must succeed for complete; partial and uncertain remain explicit.

A bounded drain handles at most 100 claims per call; total scope is bounded by 50 destinations and 10 cards. Three definitely-unsent/rejected attempts maximum; deterministic exponential delays start at five seconds, extended by Retry-After. No sleeping retry loop or background scheduler exists. A caller must explicitly call drain again after `next_retry`. Retry-After seconds and HTTP dates are parsed. Provider delays over one day are permanent under this policy. 429 is retryable; definitive 4xx rejections permanent; 408/425, 5xx, malformed success envelopes and transport exceptions are conservatively unknown. Unsupported/missing provider is permanent.

SQLite atomically claims each unit and commits a send intent before the single transport call. Claims have a 60-second lease and a random ownership token; updates compare that token. No SQLite transaction spans transport. Controlled tests prove another connection can write during transport and that competing drains cannot send the same unit. A late receipt from a superseded claim cannot overwrite a recovered unknown state.

## Crash ambiguity: not exactly once

Neither Telegram nor this Discord send API is assigned invented idempotency support. Receipt success followed by a process/SQLite failure is fundamentally ambiguous.

- Claim expired with no committed send intent: definitely unsent, retryable.
- Send intent committed, no confirmed receipt: unknown on recovery, never blind resend.
- A currently inflight send intent is reported conservatively as uncertain.
- Receipt committed: success retained across restart, never resent.
- Provider success followed by a receipt-write error: stop the batch; the durable intent preserves uncertainty even when another database write fails.

This chooses duplicate avoidance over unconditional at-least-once delivery. Some unknowns may actually be unsent. There is no exactly-once claim and no implicit automatic reconciliation.

`AlertOutbox.resolve` is an explicit trusted operator API, not an operational command or scheduler. It requires exact unit scope, authorization, operator identity, policy version, evidence reason and an explicit `workers_quiesced=True` attestation. The operator must actually quiesce all relevant workers before resolving; a boolean is not process authentication. Only unknown units can be resolved, transactionally with an audit row, to confirmed-delivered (receipt required), confirmed-unsent (retry budget still applies), or abandon. No force-resend-unknown option exists. Insufficient evidence means abandon/retain unknown, not invent a receipt.

## Offline evidence

`tests/test_step2_delivery.py` exercises actual ARM/evaluator, database/admission/outbox and retry logic. Only enrichment/provider boundaries are mocked. SQLite triggers exercise actual rollback/crash boundaries. TEST transports have no network capability. Isolated audit launchers and full RED/GREEN logs are in the Step 2 evidence directory identified by the result report.

Limits: controlled thread schedules, not exhaustive interleavings; Python audit hooks, not a hostile-native sandbox; caller/operator authorization is a trusted integration boundary, not cryptographic identity. No market validation, provider integration certification, image delivery, production retention/pruning, live migration or automatic retry scheduler is claimed.
