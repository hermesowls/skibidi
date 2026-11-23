# Workflow boundary acceptance

A paper-execution candidate passed 34 targeted/prior and 15 historical tests, but independent public-caller probes found gaps. These probes worked; later remediation was not independently accepted at capture time.

## Source admission

Persist a legitimate eligible source BEFORE entry in end-to-end fixtures. Inserting the source after cash debit can hide an unmanageable holding. Probe missing, quarantined, wrong-expiry/identity and resolved sources. Require transactional admission consistency rather than relaxing monitor safety. Distinguish new admission from replay of already-committed intent receipts; test concurrency.

## Public lifecycle routes

A safe scheduled monitor is insufficient when public trim/exit accepts bare price or arbitrary outcome. Exercise every supported caller and direct/monitor interleaving. Caller-owned connection parameters are not authorization. Cash, quantity, economic journal, outcome journal and source state must agree atomically. Inject source UPDATE failure as well as journal INSERT failure and compare complete snapshots.

## Temporal boundaries

Age-fresh quotes can still predate entry. Test the first quote relative to entry observation and later monotonicity; define same-tick semantics. Canonical expiry identity isn't expiry eligibility. Test expired/current-day/future dates against an aware clock and documented policy without overstating exchange-calendar/settlement qualification.

## Controls and guards

Independent probes verified rejection of competing distinct intents on one source, and full rollback on an SQLite source-update trigger failure. Preserve those controls plus replay, long-call/put economics and partial-close conservation. Fixtures/transports remain explicitly TEST, not live provider proof.

Guard logs are independently checked so swallowed network attempts fail runs. A synthetic audit event can test this without making a connection. Record hashes before/after and new evidence labels. Expected guard exit1 and reproduction exit0 are not product acceptance. Python audit isolation is not a hostile native-code sandbox guarantee.
