# Step5 C2/C3 closeout candidate

Independent acceptance remains pending. Production source and eligibility rules were not changed by this slice.

## C2: portable TEST clocks

`tests/step5_test_clock.py` freezes the fixture observation clock and module-local external `datetime.now` / `date.today` boundaries used by the actual Flow/Owlfred producers, simulator, manager, persistence and learning timestamps. The fixture as-of is `2026-09-23T12:00:00+00:00`; delivery and monitor clocks continue to use explicit arguments. No system clock is changed and no evaluator/eligibility function is mocked.

The portability regression installs surrounding module wall clocks in **2025 and 2028**, verifies those surrounding years are actually active, then exercises the same frozen fixture through real producer authorization and deadline closure. Full candidate, decision, lifecycle and exit economics match. The original fixture failed this positive invariant in both years before the frozen wrapper was applied; RED is preserved separately from successful validation.

Expired contracts, future/expired observations and future policies still reject relative to the same as-of. C1's future/stale/missing quote gates remain covered. Fixed-time gain/loss prints in the shared SQLite dataset have distinct observation timestamps (30/31 seconds before as-of), preserving the real unique-print constraint. Canonical validation caught that fixture collision; no database constraint was relaxed.

## C3: real technical function boundaries

Two new tests exercise `kian_technicals.analyze` directly. Momentum tests use independent rational LR endpoint weights, fixed Donchian midpoint and manually derived detrending, covering positive/negative fading, growing magnitude and flat equality. EMA tests use rational recurrence expectations for periods 8/21 and explicit hold-above/hold-below, reclaim/loss, crossings from equality and exact arrivals at equality from either side.

These are coverage additions for existing correct behavior, not reproduced production bugs. No technical implementation fix was necessary. The indicator remains the documented **KIAN-TA-v1 TTM-style** variant, not a proprietary-equivalence claim. No strategy threshold or calibration was changed.

## Guarded validation

```sh
python3 -I -S scripts/verify_step5_offline.py --tests test_step5_clock_portability,test_step5_kian_technicals,test_step5_kian_closeout.Deadline
```

Focused selection: 19 passed (12 C1, 2 C2, 5 technical including 2 new C3). Historical canonical 94 passed twice, additional 93 passed, legacy upstream 1 passed separately. Code-deduplicated historical union 171; with C1/C2/C3 additions, **187 unique Python identities passed**. Exact authenticated API snapshots mounted twice: **2 unique mounted cases**, not four unique tests. Zero application audit denials. Blocked urllib3 IPv6 capability probes and Node CommonJS/ESM experimental warnings are separately reported.

Each connected repeat produced equal full research candidates, decisions and publication receipts, equal entry/learning economics and proposal contents excluding generated identifiers/hashes, and equal aggregate API statistics. Full raw journals remain preserved rather than claimed byte-identical. Exact normalization is recorded in `semantic-determinism.json`.

Evidence: `/Users/admin/.hermes/hardening/astra-remediation/step5-kian-closeout-c2c3-95o37aq2`. `canonical-selection.json` preserves exact historical identity selections; `run-index.json` preserves commands/selections, results and sandbox locations. `deduplicated-counts.json` records the unique union and verifies imported source hashes against the final checkout. Guards were inspected before use. No frontend source changed; build/typecheck not repeated.

## Prior prose correction (C4)

The earlier repair's statement that `learning_store.py` was unchanged was incorrect: that repair changed TEST cohort assignment to `paper_test`, as its manifest records. This C2/C3 slice did not change that file. Prior reports and logs remain immutable.

Remaining: parent independent C1/C2/C3 adversarial review and combined final acceptance. No live qualification or deployment.
