"""Explicit offline candidate policy; never an A+ grade or execution authority.

Historical local screen provenance is documented in STEP5_KIAN_REPAIR.md.
Production thresholds are deliberately unsupported pending owner confirmation.
"""
from datetime import date
from typing import Any
from zoneinfo import ZoneInfo
from .execution_contract import number, contract, identity
from .learning_evidence import aware_time
from .learning_store import canonical, digest, source_snapshot


def validate_policy(profile, expected_hash):
    p = profile['profile'].get('kian_research')
    if not isinstance(p, dict):
        raise ValueError('Missing registered Kian policy')
    if (profile['classification'] != 'stated_policy' or profile['source_mode'] != 'paper_test'
            or type(p.get('schema_version')) is not int or p.get('schema_version') not in (1, 2) or p.get('mode') != 'paper_test'
            or p.get('approval') != 'TEST_OFFLINE_ONLY'
            or p.get('origin') not in ('recovered_local_plus_test_proposals', 'user_chosen_research')
            or digest(p) != expected_hash or profile['profile'].get('kian_policy_hash') != expected_hash):
        raise ValueError('Unapproved, proposed or changed research policy')
    required = {'schema_version','mode','approval','origin','min_premium','min_size','dte_min','dte_max',
                'max_otm_fraction','max_age_seconds','calendar_zone','complex_handling','ask_handling',
                'premium_definition','size_definition','volume_definition'}
    optional = {'ta_settings','paper_lifecycle'}
    if p['schema_version'] == 2:
        required.add('otm_required')
        if type(p.get('otm_required')) is not bool:
            raise ValueError('Invalid OTM requirement')
    if not required <= p.keys() or p.keys() - required - optional:
        raise ValueError('Invalid policy schema')
    for key in ('min_premium','min_size','dte_min','dte_max','max_otm_fraction','max_age_seconds'):
        if key == 'max_otm_fraction' and p['schema_version'] == 2 and p[key] is None:
            continue
        if type(p[key]) not in (int, float):
            raise ValueError('Numeric policy field required: '+key)
        number(p[key], key, zero=key in ('dte_min','dte_max'))
    if any(int(p[k]) != p[k] for k in ('min_size','dte_min','dte_max')) or p['dte_min'] > p['dte_max']:
        raise ValueError('Invalid policy bounds')
    ZoneInfo(p['calendar_zone'])
    expected = dict(complex_handling='reject',ask_handling='report_only',premium_definition='single_print_usd',
                    size_definition='single_print_contracts',volume_definition='aggregate_contract_session')
    if any(p.get(k) != v for k,v in expected.items()):
        raise ValueError('Unsupported evidence semantics')
    return p


def validate_paper_lifecycle(candidate, decision, intent, now):
    from datetime import timedelta
    p=decision['recorded_profile']['profile']['kian_research'].get('paper_lifecycle')
    if not isinstance(p,dict) or p.get('approval')!='TEST_OFFLINE_ONLY':
        raise ValueError('Missing explicitly registered TEST paper lifecycle')
    if (p.get('entry_trigger')!='explicit_source_matched_owner_test'
            or p.get('cost_requirement')!='observed_costs_before_learning'
            or p.get('exits')!='explicit_evidence_backed_partial_final'):
        raise ValueError('Unsupported paper lifecycle')
    for key in ('quantity','stop_loss_price','tp1_price','tp2_price','max_hold_seconds','quote_max_age_seconds'):
        number(p.get(key),key)
    if not float(p['quantity']).is_integer() or not p['stop_loss_price']<intent['entry_price']<p['tp1_price']<=p['tp2_price']:
        raise ValueError('Invalid TEST paper lifecycle amounts')
    for key in ('quantity','stop_loss_price','tp1_price','tp2_price'):
        if intent.get(key)!=p[key]: raise ValueError('Paper intent differs from registered lifecycle')
    if candidate['baseline_status']!='QUALIFIED': raise ValueError('Baseline unavailable for entry')
    if intent.get('risk_limits',{}).get('max_evidence_age_seconds')!=p['quote_max_age_seconds']:
        raise ValueError('Quote age differs from registered policy')
    # A deadline is a persisted manual control, never an autonomous executor.
    return dict(p,entered_at=now.isoformat(),exit_deadline=(now+timedelta(seconds=p['max_hold_seconds'])).isoformat(),
                enforcement='caller_driven_no_autonomous_exit',candidate_decision_id=decision['decision_id'])


def observed_gex(data, evidence, decision_at, max_age) -> dict[str, Any]:
    try:
        if not isinstance(data,dict) or data.get('ticker') != evidence['ticker']:
            raise ValueError('Missing/mismatched GEX')
        identity(data.get('source'),'GEX source'); identity(data.get('evidence_id'),'GEX evidence')
        if data.get('timeframe') not in ('0DTE_INTRADAY','1W_SWING'):
            raise ValueError('Unknown GEX timeframe')
        age=(aware_time(decision_at)-aware_time(data.get('observed_at'))).total_seconds()
        if not 0<=age<=max_age: raise ValueError('Stale/future GEX')
        levels=data['levels']
        if not isinstance(levels,list) or not levels: raise ValueError('Missing GEX levels')
        spot=number(evidence.get('spot_price'),'GEX reference spot')
        sign=1 if evidence['call_put']=='C' else -1
        for level in levels:
            number(level['price'],'GEX level')
            if level['kind'] not in ('king_node','opex_node','negative_wall','gatekeeper'):
                raise ValueError('Unknown GEX level kind')
        targets=[level['price'] for level in levels if level['kind'] in ('king_node','opex_node') and sign*(level['price']-spot)>=0]
        target=min(targets,key=lambda x:abs(x-spot)) if targets else None
        wall=any(level['kind'] in ('negative_wall','gatekeeper') and sign*(level['price']-spot)>=0
                 and (target is None or abs(level['price']-spot)<=abs(target-spot)) for level in levels)
        return dict(status='AVAILABLE',provenance=data,target=target,entry=None,wall_conflict=wall,
                    room=abs(target-spot) if target is not None else None,pin=target==spot,
                    meaning='King/OPEX nodes are destinations/pins, never entries')
    except (KeyError,TypeError,ValueError) as exc:
        return dict(status='UNKNOWN',reason=str(exc),entry=None)


def evaluate_research(db, decision, request, now):
    """Validate current source against immutable decision, persist candidate cohorts.

    A missing baseline observation is INCOMPLETE, never zero. Known zero OI is
    allowed in the strict volume > OI comparison (no infinite ratio invented).
    """
    if not isinstance(request, dict) or request.get('authorized') is not True or request.get('mode') != 'paper_test':
        raise ValueError('Explicit offline research authorization required')
    if not decision:
        raise ValueError('Research requires registered learning decision')
    at = aware_time(decision['decision_at'])
    if at > now:
        raise ValueError('Future decision')
    profile = db.get_learning_version(decision['profile_version'], decision_at=decision['decision_at'])
    p = validate_policy(profile, request.get('policy_hash'))
    with db._get_connection() as c:
        row = c.execute('SELECT * FROM notable_flow WHERE flow_id=?',(decision['source_id'],)).fetchone()
        raw = c.execute('SELECT * FROM raw_messages WHERE message_id=?',(decision['raw_source_id'],)).fetchone()
        if (not row or not raw or row['is_quarantined'] or row['final_outcome'] != 'MONITORING'
                or digest(source_snapshot(row)) != decision['source_snapshot_hash']
                or digest(dict(raw)) != decision['raw_source_hash']
                or c.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND COALESCE(is_quarantined,0)!=0',(decision['source_id'],)).fetchone()):
            raise ValueError('Changed or ineligible research source')
        source = dict(row)
    e = request.get('evidence')
    if not isinstance(e,dict):
        raise ValueError('Explicit evidence object required')
    if e.get('source_id') != decision['source_id'] or e.get('source') != source['source']:
        raise ValueError('Research source identity mismatch')
    for key in ('ticker','strike','call_put','expiration'):
        if e.get(key) != source[key]:
            raise ValueError('Research contract mismatch')
    result = screen_research(profile, decision, request, source)
    # Immutable, source-specific cohort observations; repeats remain carryover.
    with db._get_connection() as c:
        c.execute('CREATE TABLE IF NOT EXISTS kian_research_candidates (decision_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, payload_json TEXT NOT NULL)')
        old=c.execute('SELECT payload_json FROM kian_research_candidates WHERE decision_id=?',(decision['decision_id'],)).fetchone()
        if old:
            import json
            previous=json.loads(old[0])
            result['novelty']=previous['novelty']
            if canonical(result) != old[0]:
                # Only the exact prior producer shape is compatible. Never discard
                # present metadata or relax source, policy, evidence or economics.
                additions = {'max_otm_fraction', 'filter_provenance'}
                if p['schema_version'] == 1:
                    additions |= {'otm_fraction', 'profile_name'}
                legacy = {k: v for k, v in result.items() if k not in additions}
                if (type(previous.get('schema_version')) is not int
                        or previous['schema_version'] != 1
                        or previous.keys() != legacy.keys()
                        or canonical(legacy) != old[0]):
                    raise ValueError('Research decision conflict')
            return previous
        result['novelty']='carryover' if c.execute('SELECT 1 FROM kian_research_candidates WHERE source_id=?',(decision['source_id'],)).fetchone() else 'new_source'
        c.execute('INSERT INTO kian_research_candidates VALUES (?,?,?)',(decision['decision_id'],decision['source_id'],canonical(result)))
    return result


def screen_research(profile, decision, request, source):
    """Pure shared screening; callers own validated lineage and persistence.

    TEST previews supply declared synthetic evidence, never live scan authority.
    """
    p = validate_policy(profile, request.get('policy_hash'))
    return _screen_validated(profile, p, decision, request, source, cohort='paper_test')


def _screen_validated(profile, p, decision, request, source, *, cohort):
    """Shared filter arithmetic, not an authorization or persistence boundary.

    Only explicit caller-owned cohorts; the TEST evaluator retains its guard.
    Real-data callers must independently validate grant, source and saved policy.
    """
    if cohort not in ('paper_test', 'TEST', 'REAL_DATA_RESEARCH'):
        raise ValueError('Unsupported research cohort')
    at = aware_time(decision['decision_at'])
    e = request['evidence']
    contract(dict(e,occ_symbol=e.get('contract_symbol')))
    identity(e.get('evidence_id'),'evidence_id')
    reasons = []
    for key in ('observed_at','spot_observed_at'):
        try:
            age = (at-aware_time(e.get(key))).total_seconds()
            if age < 0 or age > p['max_age_seconds']:
                reasons.append(key+':stale_or_future')
        except (TypeError,ValueError):
            reasons.append(key+':missing_or_invalid')
    values = {}
    for key in ('spot_price','premium_usd','size','volume','open_interest'):
        try:
            values[key] = number(e.get(key),key,zero=key in ('volume','open_interest'))
            if key in ('size','volume','open_interest') and not values[key].is_integer():
                raise ValueError('Fractional contracts')
        except ValueError:
            reasons.append(key+':missing_or_invalid')
    for key in ('premium_definition','size_definition','volume_definition'):
        if e.get(key) != p[key]: reasons.append(key+':unknown_semantics')
    if type(e.get('complex_trade')) is not bool: reasons.append('complex_trade:unknown')
    status = 'INCOMPLETE' if reasons else 'QUALIFIED'
    dte = (date.fromisoformat(e['expiration'])-at.astimezone(ZoneInfo(p['calendar_zone'])).date()).days
    otm = None
    if status == 'QUALIFIED':
        if values['spot_price'] != decision['inputs']['spot_price'] or values['premium_usd'] != source['premium_usd']:
            raise ValueError('Research observed economics mismatch')
        distance = (e['strike']-values['spot_price'])/values['spot_price']
        otm = distance if e['call_put']=='C' else -distance
        checks = dict(premium=values['premium_usd']>=p['min_premium'],size=values['size']>=p['min_size'],
            volume_gt_oi=values['volume']>values['open_interest'],
            otm=(not p.get('otm_required', True) or otm>0) and (p['max_otm_fraction'] is None or otm<=p['max_otm_fraction']),
            dte=p['dte_min']<=dte<=p['dte_max'],simple_trade=e['complex_trade'] is False)
        reasons.extend(k+':rejected' for k,v in checks.items() if not v)
        if reasons: status='REJECTED'
    result: dict[str, Any] = dict(schema_version=1,decision_id=decision['decision_id'],source_id=decision['source_id'],
        policy_version=decision['profile_version'],policy_hash=digest(p),origin=p['origin'],mode=cohort,
        baseline_status=status,baseline_reasons=reasons,enhanced_status='UNKNOWN',
        enhancement_unknowns=['TA unavailable','GEX unavailable','Execution-time fill/IV unverified','Next-session OI pending'],
        reported_side=e.get('reported_side'),verified_buy=False,dte=dte,calendar_zone=p['calendar_zone'],
        evidence=e,source_hash=decision['source_snapshot_hash'],raw_source_hash=decision['raw_source_hash'],
        confirmed_setup=False,execution_authorized=False,probability=None)
    result['otm_fraction'] = otm
    result['profile_name'] = profile['profile'].get('research_profile_name')
    result['max_otm_fraction'] = p['max_otm_fraction']
    result['filter_provenance'] = profile['profile'].get('filter_provenance')
    from .kian_technicals import analyze
    settings = p.get('ta_settings')
    if not isinstance(settings, dict):
        settings = {}
    candles = request.get('candles')
    valid_settings = (isinstance(settings, dict) and settings.get('approval') == 'TEST_OFFLINE_ONLY'
        and settings.get('variant') == 'KIAN-TA-v1'
        and settings.get('timeframe') in ('1h', '1d'))
    if valid_settings:
        try:
            number(settings.get('max_age_seconds'), 'registered candle age')
            valid_settings = settings.get('expected_interval_seconds') == {'1h':3600,'1d':86400}[settings['timeframe']]
        except ValueError:
            valid_settings = False
    if (valid_settings and isinstance(candles, dict)
            and all(candles.get(k) == settings[k] for k in ('timeframe','max_age_seconds','expected_interval_seconds'))):
        # Compatibility is chosen by the caller cohort, never provider fields.
        ta = analyze(candles, e['ticker'], decision['decision_at'],
                     context='TEST_FIXED_INTERVAL' if cohort in ('TEST', 'paper_test') else 'XNYS_REGULAR')
    else:
        ta = dict(status='UNKNOWN',version='KIAN-TA-v1',direction='UNKNOWN',probability=None,
                  reason='Missing or mismatched registered TEST TA settings')
    result['ta'] = ta
    if ta['status'] == 'AVAILABLE':
        result['enhancement_unknowns'].remove('TA unavailable')
    result['gex'] = observed_gex(request.get('gex'), e, decision['decision_at'], p['max_age_seconds'])
    if result['gex']['status'] == 'AVAILABLE':
        result['enhancement_unknowns'].remove('GEX unavailable')
        if ta['status'] == 'AVAILABLE':
            desired = 'BULLISH' if e['call_put']=='C' else 'BEARISH'
            result['enhanced_status'] = 'ALIGNED_RESEARCH_EVIDENCE' if (ta['direction']==desired
                and not result['gex']['wall_conflict'] and result['gex']['room'] is not None
                and result['gex']['room']>0) else 'CONFLICT'
    return result
