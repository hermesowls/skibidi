# Step5 C1: caller-driven maximum-hold closeout

Implementation candidate; independent review and full protected regression remain pending.

The existing paper monitor enforces the admitted TEST `paper_lifecycle` deadline. It reads the immutable learning decision/profile, validates source/raw hashes and policy, reconstructs the lifecycle, and checks entry journal/payload/intent decision identity. Removing or extending a nested lifecycle cannot turn a registered research entry into a legacy entry. Legacy entries without registered research lifecycle retain their price-driven behavior.

## Boundary semantics

- All quote identity, observed provenance, chronology, registered freshness, holding identity, and source eligibility gates still apply.
- Inclusive deadline: `now >= exit_deadline` and `quote.observed_at >= exit_deadline` authorize the time exit.
- Deterministic priority after evidence gates: stop first, then maximum hold, then TP1/TP2. A stop uses its stop outcome, not a fabricated time-exit reason. At the deadline a target-level quote closes the entire remainder with `CLOSED_MAX_HOLD`, rather than starting another trim.
- An overdue neutral quote observed before the deadline cannot liquidate the position. A valid stop observation retains stop priority.
- Missing/stale/future/crossed/wrong-identity/unobserved quotes leave the position unchanged and return `EXIT_PENDING` with no operation or economic receipt. Corrupt deadlines return `INVALID_DEADLINE`. Direct execution requests raise `ValueError` on invalid evidence rather than manufacturing fills.
- Pending results are returned to the caller, not scheduled or autonomously persisted. A configured manager reader returning `None` reports pending; an entirely unconfigured monitor retains its pre-existing no-op behavior.
- Close, source outcome, holding and portfolio economics, and journal writes share one immediate transaction. Repeated/restarted/concurrent monitor calls cannot duplicate the sale. Exact direct evidence replay returns the saved receipt.
- Time exit is a source reason, not a profitability label. Learning derives gross economics from actual tranches; net outcome remains unknown until explicit observed costs. TEST outcomes remain `paper_test`, never production evidence.

## Focused verification

From the repository root, using the inspected offline guard:

```sh
python3 -I -S scripts/verify_step5_offline.py --tests test_step5_kian_closeout.Deadline
python3 -I -S scripts/verify_step5_offline.py --tests test_step1_execution.ExecutionTests.test_scheduled_test_tracer_observed_quote_to_close
```

The continuation verified 12 C1 tests and one separately isolated legacy tracer. The guard scrubs credentials, uses disposable HOME/profile/SQLite/cwd, denies network/private access/outside writes, and fails on swallowed application audit denials. The urllib3 IPv6 capability probe is blocked and separately reported.

C2 clock portability, C3 indicator semantics, canonical protected Python/mounted regressions, and independent review are deliberately not performed in this C1 slice. Current producer fixtures still use wall time with fixed option expiry; these green C1 results are not a claim of C2 determinism or whole-Step5 acceptance.
