STEP3 correction contracts (candidate; independent acceptance required)

Legacy analyst learning
  analyze_analyst(..., cutoff=aware_timestamp) uses exactly that cutoff in
  its immutable version. Current legacy outcome availability is updated_at:
  aware entry_time <= exit_time <= updated_at <= cutoff (equality allowed).
  Missing/naive/malformed/reversed/future times are retained, not resolved.
  No timezone is invented for legacy events. Empty selections also save a
  version with empty evidence IDs and retained counts. created_at is real now;
  future training cutoffs cannot manufacture a future creation timestamp.

Decision/source revision
  Decisions append a raw-message snapshot/hash plus notable snapshot/hash.
  Immutable notable evidence: flow_id, source, ticker, asset_type, strike,
  call_put, expiration, premium_usd, premium_raw, raw_message_id, channel_id,
  trade_timestamp, vol_to_oi_ratio, is_sweep and source_evidence provenance.
  Caller inputs and their registered as-of profile are also frozen.
  Lifecycle outcome/quote/entry-monitor prices, follow-up OI, review scores,
  derived quant metrics, archive paths and updated_at are not the immutable
  source identity. Their changes still revise the derived sample fingerprint.
  Quarantine remains a current exclusion, including linked analytics.
  New learning rejects changed immutable source/raw evidence. Correction of
  immutable source evidence requires a new source/decision; no automatic
  retroactive requalification. Historical decision replay uses its recorded
  version/snapshot and remains retrievable after quarantine. Legacy decisions
  without a source snapshot remain legacy_unknown_source_snapshot; no backfill.

Economic corrections
  Journal and source economic outcomes are never rewritten by learning.
  Total costs and each corrected event price independently select the newest
  aware observed_at, not insertion rowid. Contradictory values at the latest
  equal observation time reject the sample; identical values are unambiguous.
  Explicit correction supersedes is unsupported and rejected (not ignored).
  A newer observed revision may resolve an earlier conflict. Zero is observed;
  missing costs are unknown. Current derivation conservatively abstains if any
  correction availability is later than summary cutoff; it does not reconstruct
  an old economic state from today's current inputs. Earlier immutable samples
  and versions remain queryable by their IDs. Appended samples supersede the
  exact prior derived revision, including state reverts; repeated imports are
  idempotent. No statistical edge is inferred.

Provenance shape and isolation
  JSON metadata and source_evidence must be objects. SQL NULL metadata means
  absent/unknown; JSON null, lists, scalar and malformed JSON are rejected.
  Invalid source evidence yields a per-holding rejected sample without aborting
  valid holdings. Database/transaction failures still propagate and roll back.
  Rejected decisions retain their original cohort, never promote to observed.

ARM caller
  evaluate_candidate_end_to_end(..., learning_context={decision_id, source_id,
  profile_version, decision_at, inputs}) validates exact evaluated input identity,
  records a real classifier decision against an as-of registered version, and
  invokes real confluence validation with that version. Historical inputs cannot
  be enriched with today's quant results. Descriptive versions yield no bonus.
  Learning proposals/exploratory versions cannot authorize simulation. Stated
  policy context still requires the original separate Step1 execution intent,
  source, quote, risk limits and matching decision/source/version identities.
  Without learning context the existing separately authorized Step1 path remains
  available, explicitly legacy_unknown rather than fabricated learning linkage.
  Step2 publication authorization remains separate and its delivery logic intact.
  Evaluation trace and analytics use caller IDs; absent source identity means no
  invented analytics source. Missing conviction/ratio/excursion/OI stays unknown.
  Deep-dive reporting uses supplied evidence, not invented skew/TA/macro values
  or a fabricated synthesis probability. Heuristic targets are plans, not observed
  outcomes. No provider, live policy service, automatic promotion or Step4 work.
