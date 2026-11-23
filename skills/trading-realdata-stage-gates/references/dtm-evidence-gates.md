# DTM evidence gates for trading systems

## Populated baseline

Use stable need, requirement, design, protocol, evidence and gap IDs. Support many-to-many links. Each requirement includes measurable acceptance criteria, their approval basis, implementation paths/mechanism, exact test identities, expected result, execution evidence and separate verification/validation/deployment states. Future features remain proposed; do not turn formal SHALL wording into implicit architecture approval.

Suggested workbook: Readme, Needs, DTM, Protocols, Evidence, Gaps, File Baseline, Summary. Canonical JSON permits forward/reverse trace and change impact; CSV makes the matrix portable. Local file-URI report links work only where those files exist, not as public links.

## Evidence qualification

- Read source and report scope before assigning links. Use AST to confirm class/method names without importing production code; this is not a behavioral test.
- Match methods to reviewed selections or execution logs. Historical broad acceptance with incomplete method mapping stays explicitly incomplete.
- Distinguish TEST fixtures, recorded-data REPLAY, REAL observations, documentation validation and source inspection.
- A report with overall HOLD may contain a passing sub-scope; cite that sub-scope without relabeling the whole report.
- Preserve report hashes, baseline manifests and supersession relationships. Do not overwrite old independent reports or count overlapping suites as additive coverage.
- Separate an implementation defect from an evidence-mapping gap, an intended-use validation gap and a deployment gap. An open gap is not automatically a failed test.

## Structural verification

Persist an initial skeleton, then append bounded evidence batches. Generate workbook from the canonical data. Reopen and compare every flattened matrix value; verify unique IDs, valid relationship endpoints, no orphan needs, actual test symbols and referenced-file hashes. Report structural checks as DOCUMENT STRUCTURE ONLY. Do not rerun product tests merely to populate documentation unless separately in scope. A same-agent check must not be described as independent review.

## Operational gates exposed by traceability

Research ingestion acceptance does not authorize sends/orders. One provider-filtered sample is not complete market coverage or a confirmed directional setup. Historical GEX/TA collection needs an approved universe, cadence, coverage/loss criteria and provenance; candidate-triggered snapshots cannot establish pre-signal completeness. Kian feedback and setup tracking need their own requirements and protocols rather than being inferred from Discord ingestion existing.

For selective legacy cron reactivation, inspect startup migrations and sink drains before source flags, plus backlog pagination and cursor-vs-durable-record consistency. A disabled source flag alone need not isolate all side effects. Keep these as inspection findings until a corrected path is actually tested; do not describe an unimplemented isolation proposal as verified.

## Change control and clutter

Amar favors one canonical system with explicit legacy/Astra transition labels, not permanent duplicated stacks. A registry should map workflow purpose, entrypoint, source/sink, state, schedule, current acceptance and replacement relation. Architecture changes, collection budgets/cadence, storage boundaries and execution permissions require Amar approval. Preserve useful multi-source architecture where practical; source isolation does not automatically require a database per source. Trace all references before moving hash-gated scripts or reports.
