# Discovery validation: evidence and request scope

## Saved-response diagnosis
1. Read only the approved captured response and research store. Reconcile envelope row count, unique provider IDs and stored raw records programmatically; distinguish sample coverage from market coverage.
2. Inventory field presence, JSON types, nulls and usable values before attributing a problem to the parser. Trace canonicalization separately from screening.
3. Compute observable threshold results independently of evidence completeness. Preserve unknown OTM when spot is null; do not convert absent aggregation evidence into false. Valid raw premium/size can support diagnostic failures without certifying single-print semantics.
4. Compare execution, receipt and decision times. After-hours stale observations do not establish a provider outage or no whales. Never backdate live evaluation to force admission.
5. Option fills, bid/ask timestamps and IV may be retained raw even when enhanced confirmation is unavailable. ASK tags are not necessarily literal ask fills, and a raw IV level is not comparable before/after IV confirmation.

## Profile and terminology checks
Preserve the approved dimensions exactly: trade size and cumulative contract volume are different; an unlimited OTM-distance cap is not a premium cap. Current-analysis DTE and execution-date retrospective diagnostics need distinct labels. Preserve the selected immutable profile rather than substituting a generic endpoint example.

Keep provider-filtered candidates, locally verified threshold matches, aggregated activity, verified individual executions and directional inferences separate. Public flow does not generally establish participant identity or confirmed opening purchases. Endpoint documentation coverage is not live endpoint validation.

## Bounded change acceptance
For an approved targeted-request change, verify exact documented parameter names/types, closed allowlists in both parent and worker, profile-derived serialization, and immutable full-query provenance. Retain the approved call/row/time/retry limits; provider maximum limits are not authorization. Use isolated TEST boundary mocks to exercise caller through HTTP serialization and label any captured-data replay REPLAY, never LIVE.

After independent acceptance, update the scheduled job's accepted manifest/selection and use a new output root for changed record shapes. Read back the exact job before claiming the new request is scheduled. Do not overwrite the original captured evidence.

Dashboard clearance is separate: verify no active writer, accepted source, built/served frontend and intended process before granting restart clearance. Source acceptance alone does not prove the served UI is current; a messaging-gateway restart is not implied.
