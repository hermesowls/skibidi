"""Bounded manual individual UW REST research admission, never activation.

The separate documented Option_Trade adapter preserves original identity and
raw revisions. Observation admission does not confer strategy qualification:
spot as-of, complex/correction and next-session OI evidence remain unknown.
The legacy flow-alert parser below never promotes totals to single prints.
"""
import json
import time
from decimal import Decimal
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from .execution_contract import contract, number
from .learning_evidence import aware_time
from .learning_store import canonical, digest
from .research_profiles import select
from .kian_research import validate_policy, _screen_validated

from .uw_option_trades import canonicalize_trade, PATH

ENDPOINT = PATH


def raw_threshold_diagnostics(raw, p, at):
    """Schema-validated raw economics only, never single-print certification.

    These independent checks remain visible when the strict baseline lacks
    spot as-of or aggregation/complexity evidence. None authorize qualification.
    """
    premium = raw.get('premium')
    size, volume, oi = (raw.get(k) for k in ('size', 'volume', 'open_interest'))
    dte = (date.fromisoformat(raw['expiry']) - at.astimezone(ZoneInfo(p['calendar_zone'])).date()).days
    checks = dict(premium=None if premium is None else Decimal(premium) >= Decimal(str(p['min_premium'])),
                  size=None if size is None else size >= p['min_size'],
                  volume_gt_oi=None if volume is None or oi is None else volume > oi,
                  dte=p['dte_min'] <= dte <= p['dte_max'])
    spot = raw.get('underlying_price')
    if spot is None:
        checks['otm'] = None
    else:
        distance = (Decimal(raw['strike']) - Decimal(spot)) / Decimal(spot)
        if raw['option_type'] == 'put':
            distance = -distance
        checks['otm'] = ((not p.get('otm_required', True) or distance > 0) and
                         (p['max_otm_fraction'] is None or distance <= Decimal(str(p['max_otm_fraction']))))
    return dict(checks=checks, failures=[k for k,v in checks.items() if v is False],
                unknown=[k for k,v in checks.items() if v is None], qualifies=False,
                semantics='RAW_FIELDS_ONLY_NOT_SINGLE_PRINT_OR_POINT_IN_TIME_CERTIFICATION')


def canonicalize_alert(raw, cohort):
    """Only verified mirror fields. Never use receipt time as market observation.

    Content hash is a local snapshot identity, explicitly NOT a provider event ID.
    Aggregates are retained raw, never treated as single-print premium or size.
    """
    if not isinstance(raw, dict):
        raise ValueError('Malformed UW alert object')
    if len(canonical(raw)) > 32768:
        raise ValueError('Oversized UW alert')
    ticker = raw.get('ticker')
    right = {'CALL':'C', 'PUT':'P'}.get(raw.get('option_type'))
    expiry = raw.get('expiry')
    strike = raw.get('strike')
    if type(strike) is str:
        strike = float(strike)
    number(strike, 'strike')
    parsed = date.fromisoformat(expiry)
    symbol = f'{ticker}{parsed:%y%m%d}{right}{int(strike*1000):08d}'
    source_id = cohort + ':UW-snapshot:' + digest(raw)
    e = dict(ticker=ticker, call_put=right, expiration=expiry, strike=strike,
             contract_symbol=symbol, source='UW_FLOW_ALERTS', source_id=source_id,
             evidence_id=source_id, observed_at=None, spot_observed_at=None,
             spot_price=None, premium_usd=None, size=None, volume=None,
             open_interest=None, complex_trade=None, reported_side=raw.get('side'),
             premium_definition='UNKNOWN', size_definition='UNKNOWN',
             volume_definition='UNKNOWN')
    contract(dict(e, occ_symbol=symbol))
    # Volume/OI are retained in raw only until provider semantics are qualified.
    return e


def run_once(db, grant, *, transport, now, max_rows=20, timeout_seconds=10):
    """One request, zero retries, isolated research table and no other producer.

    Transport(path, params=..., timeout=...) must enforce the supplied network
    timeout and return {status,source,received_at,body:{data:[...]}}. Built-in
    HTTP/client/credential lookup occurs only in the separate explicit CLI and
    isolated BoundedUWTransport. REAL_DATA_RESEARCH requires that transport and
    ResearchStore; injected TEST callers remain an offline compatibility seam.
    Time checks here are accounting, not cancellation; the built-in transport
    enforces its deadline by terminating the isolated worker. With now=None the
    decision clock is sampled after receipt, never backdated before the request.
    """
    required = {'mode','authorized','profile_version','evidence_cohort'}
    if (not isinstance(grant, dict) or set(grant) != required
            or grant['mode'] != 'REAL_DATA_RESEARCH' or grant['authorized'] is not True
            or grant['evidence_cohort'] not in ('TEST','REAL_DATA_RESEARCH')):
        raise ValueError('Explicit bounded research-only grant required')
    if grant['evidence_cohort'] == 'REAL_DATA_RESEARCH':
        from .realdata_store import ResearchStore
        from .realdata_transport import BoundedUWTransport
        if not isinstance(db, ResearchStore) or not isinstance(transport, BoundedUWTransport):
            raise ValueError('Real provenance requires dedicated research DB and bounded provider transport')
    if type(max_rows) is not int or not 1 <= max_rows <= 100:
        raise ValueError('Row bound must be 1..100')
    if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 30:
        raise ValueError('Timeout must be finite 0..30 seconds')
    at = datetime.now(timezone.utc) if now is None else aware_time(now.isoformat())
    profile = select(db, grant['profile_version'])
    if aware_time(profile['created_at']) > at:
        raise ValueError('Future saved profile')
    p = validate_policy(profile, profile['profile']['kian_policy_hash'])
    cohort = grant['evidence_cohort']
    started = time.monotonic()
    # Exact saved policy; optional OTM distance stays a local evidence check.
    params = {'limit':str(max_rows), 'include_agg_trades':'false',
              'min_premium':format(Decimal(str(p['min_premium'])), 'f'),
              'min_size':str(int(p['min_size'])), 'volume_greater_oi':'true',
              'min_dte':str(int(p['dte_min'])), 'max_dte':str(int(p['dte_max']))}
    if p.get('otm_required', True):
        params['is_otm'] = 'true'
    response = transport(ENDPOINT, params=params, timeout=timeout_seconds)
    if time.monotonic() - started > timeout_seconds:
        raise ValueError('Research request deadline exceeded')
    if not isinstance(response, dict) or response.get('status') != 200:
        status = response.get('status') if isinstance(response, dict) else None
        raise ValueError('UW request failed; no retry: ' + str(status))
    expected = 'TEST_FIXTURE' if cohort == 'TEST' else 'UW_LIVE'
    if response.get('source') != expected:
        raise ValueError('Source provenance/cohort mismatch; cache and TEST are not real observations')
    if now is None:
        at = datetime.now(timezone.utc)
    received = aware_time(response.get('received_at'))
    if not 0 <= (at-received).total_seconds() <= p['max_age_seconds']:
        raise ValueError('Stale/future response receipt')
    body = response.get('body')
    if not isinstance(body, dict) or not isinstance(body.get('data'), list):
        raise ValueError('Malformed UW response data')
    rows = body['data']
    if len(rows) > max_rows or len(canonical(body)) > 1048576:
        raise ValueError('UW response exceeds bounds')
    records = []
    for index, raw in enumerate(rows):
        if time.monotonic() - started > timeout_seconds:
            raise ValueError('Research evaluation deadline exceeded')
        raw_hash = digest(raw)
        identity = digest(dict(raw_hash=raw_hash, profile_hash=profile['content_hash'], cohort=cohort, at=at.isoformat()))
        try:
            e = canonicalize_trade(raw, cohort)
            decision = dict(decision_id='research:'+identity, source_id=e['source_id'],
                profile_version=profile['version_id'], decision_at=at.isoformat(),
                source_snapshot_hash=digest(e), raw_source_hash=raw_hash,
                inputs={'spot_price':e['spot_price']})
            result = _screen_validated(profile, p, decision, {'evidence':e}, e, cohort=cohort)
            result['observation_status'] = 'SCHEMA_VALID'
            # Validate receipt-relative chronology independently of missing
            # enrichment, retaining the exact provider timestamp and good rows.
            if aware_time(e['observed_at']) > received:
                result['observation_status'] = 'CHRONOLOGY_INVALID'
                result['baseline_reasons'].append('observed_at:after_receipt')
                result['baseline_status'] = 'INCOMPLETE'
            for field in ('is_agg', 'canceled'):
                if e[field] is not False:
                    result['baseline_reasons'].append(field + (':excluded' if e[field] is True else ':unknown'))
                    result['baseline_status'] = 'INCOMPLETE'
            result['provider_event_id'] = e['provider_event_id']
            result['raw_threshold_diagnostics'] = raw_threshold_diagnostics(raw, p, at)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            result = dict(decision_id='research:'+identity, policy_version=profile['version_id'],
                mode=cohort, baseline_status='INCOMPLETE', baseline_reasons=['malformed_alert:'+str(exc)],
                enhanced_status='UNKNOWN', execution_authorized=False,
                observation_status='MALFORMED', provider_event_id=raw.get('id') if isinstance(raw, dict) else None)
        result.update(publication_authorized=False, raw=raw, raw_source_hash=raw_hash,
            discovery_status='PROVIDER_FILTERED_CANDIDATE',
            received_at=received.isoformat(), profile_content_hash=profile['content_hash'],
            policy_context='REAL_DATA_RESEARCH',
            request_provenance={'path':ENDPOINT, 'params':params, 'source':response['source']},
            provenance_status='DOCUMENTED_REST_UNQUALIFIED_ENRICHMENT', market_proof=False)
        records.append(result)
    # Atomic bounded batch. Separate from TEST candidate/learning/outbox stores.
    with db._get_connection() as c:
        c.execute('CREATE TABLE IF NOT EXISTS realdata_research_records (decision_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)')
        for operation in ('UPDATE','DELETE'):
            c.execute(f"CREATE TRIGGER IF NOT EXISTS realdata_research_no_{operation.lower()} BEFORE {operation} ON realdata_research_records BEGIN SELECT RAISE(ABORT,'IMMUTABLE_RESEARCH'); END")
        for result in records:
            # Read immutable prior versions by exact provider identity, never overwrite.
            prior = [json.loads(r[0]) for r in c.execute('SELECT payload_json FROM realdata_research_records')]
            versions = sorted({r['raw_source_hash'] for r in prior
                if result['provider_event_id'] is not None
                and r.get('provider_event_id') == result['provider_event_id']
                and r.get('mode') == cohort
                and r.get('request_provenance', {}).get('path') == ENDPOINT
                and r['raw_source_hash'] != result['raw_source_hash']})
            result['prior_raw_versions'] = versions
            result['observation_revision'] = 'CHANGED_OBSERVATION' if versions else 'FIRST_VERSION'
            encoded = canonical(result)
            old = c.execute('SELECT payload_json FROM realdata_research_records WHERE decision_id=?',(result['decision_id'],)).fetchone()
            if old:
                previous = json.loads(old[0])
                # Revision lineage is frozen at first admission, not recomputed
                # using observations that arrived after this exact decision.
                for key in ('prior_raw_versions', 'observation_revision'):
                    result[key] = previous[key]
                encoded = canonical(result)
                if old[0] != encoded:
                    raise ValueError('Research record conflict')
            if not old:
                c.execute('INSERT INTO realdata_research_records VALUES (?,?)',(result['decision_id'],encoded))
    return dict(status='RESEARCH_ONLY', evidence_cohort=cohort, records=records,
                requests=1, provider_schema_qualified=False)
