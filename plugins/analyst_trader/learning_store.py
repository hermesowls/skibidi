"""Local append-only learning derivations from committed economic journal events.

No broker, scheduler, provider or execution side effects. Missing evidence stays
unknown. These descriptive paper samples never authorize policy promotion.
"""
import hashlib
import json
import math
from typing import Any
from datetime import datetime, timezone
from .execution_contract import money, number, quantity, contract
from .learning_evidence import aware_time


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def source_provenance(source):
    value = source.get('quant_metrics_json')
    metadata = {} if value is None else json.loads(value)
    if not isinstance(metadata, dict):
        raise ValueError('Malformed source metadata: object required')
    provenance = metadata.get('source_evidence', {})
    if not isinstance(provenance, dict):
        raise ValueError('Malformed source_evidence: object required')
    return provenance


def source_snapshot(source):
    """Immutable decision evidence, not the lifecycle projection.

    Outcomes/prices/OI follow-up, archive paths, review scores and updated_at
    legitimately evolve. Initial source identity/content and source provenance
    must not change underneath a historical decision. Corrections require a new
    source/decision; no retroactive promotion from the mutable current row.
    """
    fields = ('flow_id', 'source', 'ticker', 'asset_type', 'strike', 'call_put',
              'expiration', 'premium_usd', 'premium_raw', 'raw_message_id',
              'channel_id', 'trade_timestamp', 'vol_to_oi_ratio', 'is_sweep')
    result = {k: source[k] for k in fields}
    result['source_evidence'] = source_provenance(dict(source))
    return result


def migrate(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS learning_samples (
        sample_id TEXT PRIMARY KEY, holding_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
        supersedes TEXT, payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
        UNIQUE(holding_id,fingerprint))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS learning_versions (
        version_id TEXT PRIMARY KEY, content_hash TEXT NOT NULL,
        payload_json TEXT NOT NULL)''')
    conn.execute('''CREATE TRIGGER IF NOT EXISTS learning_versions_no_update
        BEFORE UPDATE ON learning_versions BEGIN SELECT RAISE(ABORT,'IMMUTABLE_VERSION'); END''')
    conn.execute('''CREATE TRIGGER IF NOT EXISTS learning_versions_no_delete
        BEFORE DELETE ON learning_versions BEGIN SELECT RAISE(ABORT,'IMMUTABLE_VERSION'); END''')
    conn.execute('''CREATE TABLE IF NOT EXISTS learning_corrections (
        correction_id TEXT PRIMARY KEY, holding_id TEXT NOT NULL,
        payload_json TEXT NOT NULL, created_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS learning_decisions (
        decision_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)''')
    for table in ('learning_decisions','learning_samples','learning_corrections'):
        for operation in ('UPDATE','DELETE'):
            conn.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_LEARNING_RECORD'); END")


def save_version(db, snapshot):
    snapshot=json.loads(canonical(snapshot))
    required=('schema_version','code_identity','config_identity','training_cutoff','created_at',
              'source_mode','evidence_ids','uncertainty','classification','profile')
    if any(k not in snapshot for k in required): raise ValueError('Incomplete version provenance')
    if snapshot['schema_version']!=1 or snapshot['classification'] not in ('proposal','exploratory_unvalidated','stated_policy'):
        raise ValueError('Unvalidated learning cannot promote policy')
    if aware_time(snapshot['training_cutoff'])>aware_time(snapshot['created_at']): raise ValueError('Future training cutoff')
    if not isinstance(snapshot['evidence_ids'],list) or not isinstance(snapshot['uncertainty'],list): raise ValueError('Missing evidence selection/uncertainty')
    for key in ('code_identity','config_identity','source_mode'):
        if not isinstance(snapshot[key],str) or not snapshot[key]: raise ValueError('Missing identity')
    identity=snapshot.pop('version_id',None) or 'profile:'+digest(snapshot)
    encoded=canonical(snapshot); content_hash=digest(snapshot)
    conn=db._get_connection()
    try:
        with conn:
            old=conn.execute('SELECT content_hash FROM learning_versions WHERE version_id=?',(identity,)).fetchone()
            if old and old[0]!=content_hash: raise ValueError('VERSION_ID_CONFLICT')
            if not old: conn.execute('INSERT INTO learning_versions VALUES (?,?,?)',(identity,content_hash,encoded))
    finally: conn.close()
    return identity


def get_version(db, version_id, decision_at=None):
    conn=db._get_connection()
    try: row=conn.execute('SELECT content_hash,payload_json FROM learning_versions WHERE version_id=?',(version_id,)).fetchone()
    finally: conn.close()
    if row is None: raise ValueError('UNKNOWN_PROFILE_VERSION')
    snapshot=json.loads(row['payload_json'])
    if digest(snapshot)!=row['content_hash']: raise ValueError('VERSION_CONTENT_MISMATCH')
    if decision_at is not None and aware_time(snapshot['created_at'])>aware_time(decision_at): raise ValueError('FUTURE_PROFILE_VERSION')
    return dict(snapshot,version_id=version_id,content_hash=row['content_hash'])


def replay_decision(db, decision_id):
    conn=db._get_connection()
    try: row=conn.execute('SELECT payload_json FROM learning_decisions WHERE decision_id=?',(decision_id,)).fetchone()
    finally: conn.close()
    if not row: raise ValueError('UNKNOWN_DECISION')
    data=json.loads(row[0])
    snapshot=get_version(db,data['profile_version'],data['decision_at'])
    if snapshot['content_hash']!=data['profile_content_hash']: raise ValueError('DECISION_VERSION_MISMATCH')
    return data


def record_decision(db, classifier, decision_id, source_id, profile_version, decision_at, inputs):
    cutoff=aware_time(decision_at)
    if not decision_id or not source_id: raise ValueError('Missing decision lineage')
    snapshot=get_version(db,profile_version,decision_at)
    inputs=json.loads(canonical(inputs))
    # Replay has no permission to fetch today's TA and relabel it historical.
    if 'technical_data' not in inputs or inputs['technical_data'] is None:
        raise ValueError('Explicit point-in-time technical evidence or empty unknown required')
    ta=inputs['technical_data']
    if ta and (not ta.get('evidence_ids') or aware_time(ta['available_at'])>=cutoff):
        raise ValueError('Unavailable technical evidence')
    request=dict(source_id=source_id,profile_version=profile_version,decision_at=decision_at,inputs=inputs)
    scored=classifier.classify_and_score_flow(**inputs,profile_version=profile_version,decision_at=decision_at)
    conn=db._get_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')
        old=conn.execute('SELECT payload_json FROM learning_decisions WHERE decision_id=?',(decision_id,)).fetchone()
        if old:
            result=json.loads(old[0])
            if any(result[k]!=v for k,v in request.items()): raise ValueError('DECISION_ID_CONFLICT')
            conn.rollback(); return result
        source=conn.execute('SELECT * FROM notable_flow WHERE flow_id=?',(source_id,)).fetchone()
        if not source or source['is_quarantined'] or source['final_outcome']!='MONITORING': raise ValueError('SOURCE_NOT_ELIGIBLE')
        if conn.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND COALESCE(is_quarantined,0)<>0',(source_id,)).fetchone(): raise ValueError('LINKED_QUARANTINE')
        if any(source[k]!=inputs.get(k) for k in ('ticker','strike','call_put','expiration')): raise ValueError('DECISION_CONTRACT_MISMATCH')
        raw=conn.execute('SELECT * FROM raw_messages WHERE message_id=?',(source['raw_message_id'],)).fetchone()
        if not raw or aware_time(raw['timestamp'])>cutoff or aware_time(source['trade_timestamp'])>cutoff: raise ValueError('RAW_SOURCE_NOT_AVAILABLE')
        # This existing scorer is deterministic because observed inputs are explicit.

        result=dict(request,decision_id=decision_id,raw_source_id=source['raw_message_id'],
            source_snapshot=source_snapshot(source),source_snapshot_hash=digest(source_snapshot(source)),
            raw_source_snapshot=dict(raw),raw_source_hash=digest(dict(raw)),
            source_contract={k:source[k] for k in ('ticker','strike','call_put','expiration')},
            source_mode=snapshot['source_mode'],profile_content_hash=snapshot['content_hash'],
            recorded_profile=snapshot,result=scored,execution_authorized=False)
        conn.execute('INSERT INTO learning_decisions VALUES (?,?)',(decision_id,canonical(result)))
        conn.commit(); return result
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def record_correction(db, data):
    data=json.loads(canonical(data))
    if 'supersedes' in data:
        raise ValueError('Explicit correction supersession is unsupported; use a newer observation')
    for key in ('correction_id','holding_id','evidence_id','observed_at'):
        if not isinstance(data.get(key),str) or not data[key].strip():
            raise ValueError('Missing correction '+key)
    aware_time(data['observed_at'])
    if 'total_costs' not in data and 'corrected_exit_price' not in data:
        raise ValueError('No observed correction')
    if 'total_costs' in data: number(data['total_costs'],'total costs',zero=True)
    if 'corrected_exit_price' in data: number(data['corrected_exit_price'],'corrected price',zero=True)
    conn=db._get_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')
        if not conn.execute('SELECT 1 FROM portfolio_holdings WHERE holding_id=?',(data['holding_id'],)).fetchone():
            raise ValueError('Unknown holding')
        if 'corrected_exit_price' in data and not conn.execute("SELECT 1 FROM recorded_strategies WHERE trace_id=? AND holding_id=? AND event_type IN ('autonomous_trade_trimmed','autonomous_trade_closed')",(data.get('corrected_event_id'),data['holding_id'])).fetchone():
            raise ValueError('Unknown corrected economic event')
        encoded=canonical(data)
        old=conn.execute('SELECT payload_json FROM learning_corrections WHERE correction_id=?',(data['correction_id'],)).fetchone()
        if old and old[0]!=encoded: raise ValueError('CORRECTION_ID_CONFLICT')
        if not old:
            conn.execute('INSERT INTO learning_corrections VALUES (?,?,?,?)',(data['correction_id'],data['holding_id'],encoded,datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def correction_value(corrections, field, event_id=None):
    """Newest observation wins, never insertion order. Equal-time conflict abstains."""
    relevant = [c for c in corrections if field in c and
                (event_id is None or c.get('corrected_event_id') == event_id)]
    if not relevant:
        return None
    latest = max(aware_time(c['observed_at']) for c in relevant)
    values = {number(c[field], field, zero=True) for c in relevant
              if aware_time(c['observed_at']) == latest}
    if len(values) != 1:
        raise ValueError('Conflicting correction observations: ' + field)
    return values.pop()


def _derive(holding, source, events, corrections, linked_quarantine, decision, raw, *, include_partial=False):
    result: dict[str, Any]=dict(holding_id=holding['holding_id'],source_id=holding['flow_id'],
        outcome_id='holding:'+holding['holding_id'],cohort='paper_unknown',status='unresolved',
        basis=None,gross_pnl=None,gross_return_pct=None,net_pnl=None,net_return_pct=None,
        costs=None,outcome=None,policy_version=None,decision_id=None,intent_id=None,
        evidence_ids=[e['trace_id'] for e in events]+[c['correction_id'] for c in corrections],
        uncertainty=['costs_unobserved'],classification='exploratory_unvalidated',lineage_status='legacy_unknown')
    if source is None:
        result.update(status='missing_source'); return result
    mode = str(source['source']).lower()
    result['cohort'] = ('paper_test' if mode.startswith('test') or any(x in mode for x in ('synthetic','demo','fixture'))
                        else 'paper_unknown')
    # Observed classification requires explicit provenance; arbitrary source names
    # and legacy histories do not establish a production/observed cohort.
    provenance = source_provenance(source)
    if (result['cohort'] != 'paper_test' and provenance.get('mode') in ('paper_observed','paper_test')
            and provenance.get('source_id') == source['flow_id'] and provenance.get('evidence_id')):
        result['cohort'] = provenance['mode']
    if source['is_quarantined'] or linked_quarantine:
        result.update(status='quarantined'); return result
    entries=[e for e in events if e['event_type']=='autonomous_trade_executed']
    if len(entries)!=1:
        result.update(status='missing_entry'); return result
    origin=json.loads(entries[0]['payload_json']); intent=json.loads(origin['intent_json'])['intent']
    result.update(policy_version=intent['policy_version'],decision_id=intent['parent_trace_id'],intent_id=intent['intent_id'])
    if decision:
        frozen = decision.get('source_snapshot')
        if frozen is not None and (digest(frozen) != decision.get('source_snapshot_hash')
                or source_snapshot(source) != frozen
                or aware_time(source['trade_timestamp']) > aware_time(decision['decision_at'])):
            raise ValueError('Decision/source lineage mismatch: source revision')
        if (decision['decision_id']!=intent['parent_trace_id'] or decision['source_id']!=source['flow_id']
            or decision['profile_version']!=intent['policy_version']
            or decision['source_mode']!=result['cohort']
            or not raw or decision['raw_source_hash']!=digest(raw)
            or decision['source_contract']!={k:source[k] for k in ('ticker','strike','call_put','expiration')}
            or aware_time(decision['decision_at'])>aware_time(origin['timestamp'])):
            raise ValueError('Decision/source lineage mismatch')
        result['lineage_status']='linked' if frozen is not None else 'legacy_unknown_source_snapshot'
        result['evidence_ids'] += [decision['decision_id'],decision['raw_source_id']]
    if (intent['execution_mode']!='paper' or intent['flow_id']!=source['flow_id']
        or holding['flow_id']!=source['flow_id']
        or any(source[k]!=intent[k] for k in ('ticker','strike','call_put','expiration'))
        or contract(intent)!=holding['occ_symbol'].replace(' ','')
        or holding['direction']!={'C':'call','P':'put'}[intent['call_put']]
        or holding['average_cost']!=intent['entry_price']):
        raise ValueError('Economic identity mismatch')
    units=quantity(origin['quantity']); entry_price=number(intent['entry_price'],'entry')
    basis=money(entry_price,units,100); gross=0.; sold=0.; closes=[]
    overrides={c['corrected_event_id']:correction_value(corrections, 'corrected_exit_price', c['corrected_event_id'])
               for c in corrections if 'corrected_exit_price' in c}
    costs=correction_value(corrections, 'total_costs')
    for event in events:
        if event['event_type'] not in ('autonomous_trade_trimmed','autonomous_trade_closed'): continue
        p=json.loads(event['payload_json'])
        if (event['parent_trace_id']!=entries[0]['trace_id'] or event['flow_id']!=source['flow_id']
            or p['intent_id']!=intent['intent_id'] or p['policy_version']!=intent['policy_version']):
            raise ValueError('Event lineage mismatch')
        q=quantity(event['quantity']); price=number(event['exit_price'],'exit',zero=True)
        raw=money(price,q,100,basis=entry_price)
        if not math.isclose(raw,event['realized_pnl'],abs_tol=1e-8): raise ValueError('Event economics mismatch')
        gross+=money(overrides.get(event['trace_id'],price),q,100,basis=entry_price); sold+=q
        if event['event_type']=='autonomous_trade_closed': closes.append(event['trace_id'])
    if sold>units: raise ValueError('Overclosed holding')
    result.update(basis=basis,realized_quantity=sold,initial_quantity=units)
    terminal=holding['status']=='CLOSED' and sold==units
    if not terminal:
        result['status']='partial' if sold else 'unresolved'
        if include_partial:
            result.update(gross_pnl=gross, gross_return_pct=gross/basis*100,
                          costs=costs, net_pnl=None if costs is None else gross-costs)
        return result
    if not closes and not (sold==units and holding['outcome_label']=='CLOSED_TP1'):
        raise ValueError('Missing terminal event')
    result.update(status='resolved',gross_pnl=gross,gross_return_pct=gross/basis*100,
        closed_at=holding['closed_at'],source_outcome=source['final_outcome'],
        available_at=max([holding['closed_at']]+[c['observed_at'] for c in corrections],key=aware_time))
    if costs is not None:
        net=gross-costs
        result.update(costs=costs,net_pnl=net,net_return_pct=net/basis*100,
                      outcome='WIN' if net>0 else 'LOSS' if net<0 else 'SCRATCH',uncertainty=[])
    return result


def summarize(db, cohort, cutoff) -> dict[str, Any]:
    if cohort not in ('paper_test','paper_observed'): raise ValueError('Explicit paper cohort required')
    clock=aware_time(cutoff)
    samples=import_outcomes(db)['samples']; eligible=[]; retained={}
    for sample in samples:
        if sample['cohort']!=cohort: continue
        reason=sample['status']
        if reason=='resolved':
            if sample.get('lineage_status')!='linked': reason='legacy_unknown_lineage'
            elif sample.get('net_pnl') is None: reason='costs_unobserved'
            elif aware_time(sample['available_at'])>clock: reason='unavailable_at_cutoff'
            else:
                eligible.append(sample); continue
        retained[reason]=retained.get(reason,0)+1
    count=len(eligible); wins=sum(s['net_pnl']>0 for s in eligible); losses=sum(s['net_pnl']<0 for s in eligible)
    basis=sum(s['basis'] for s in eligible); pnl=sum(s['net_pnl'] for s in eligible)
    result=dict(cohort=cohort,resolved_count=count,wins=wins,losses=losses,scratches=count-wins-losses,
        net_pnl=pnl if count else None,net_return_pct=pnl/basis*100 if basis else None,
        win_rate_pct=wins/count*100 if count else None,retained=retained,
        classification='exploratory_unvalidated',validated_rules=[],
        uncertainty=['Paper cohort only; descriptive arithmetic, not evidence of trading edge.'])
    from pathlib import Path
    code=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['proposed_version']=save_version(db,dict(schema_version=1,code_identity=code,
        config_identity=digest({'cohort':cohort,'net_costs_required':True}),training_cutoff=cutoff,
        created_at=max(datetime.now(timezone.utc),clock).isoformat(),source_mode=cohort,evidence_ids=sorted(s['sample_id'] for s in eligible),
        dataset_selection={'cohort':cohort,'terminal':True,'linked':True,'observed_costs':True},
        uncertainty=result['uncertainty'],classification='proposal',profile=result))
    return result


def import_outcomes(db) -> dict[str, Any]:
    conn=db._get_connection(); inserted=0; samples=[]
    try:
        conn.execute('BEGIN IMMEDIATE')
        for h in conn.execute("SELECT * FROM portfolio_holdings WHERE portfolio_id='autonomous_ai' ORDER BY holding_id").fetchall():
            h=dict(h)
            source=conn.execute('SELECT * FROM notable_flow WHERE flow_id=?',(h['flow_id'],)).fetchone()
            source=dict(source) if source else None
            events=[dict(e) for e in conn.execute('SELECT * FROM recorded_strategies WHERE holding_id=? ORDER BY timestamp,trace_id',(h['holding_id'],))]
            corrections=[json.loads(c[0]) for c in conn.execute('SELECT payload_json FROM learning_corrections WHERE holding_id=? ORDER BY rowid',(h['holding_id'],))]
            quarantine=bool(conn.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND COALESCE(is_quarantined,0)<>0',(h['flow_id'],)).fetchone())
            decision=None; raw=None
            entries=[e for e in events if e['event_type']=='autonomous_trade_executed']
            if len(entries)==1:
                origin=json.loads(entries[0]['payload_json'])
                drow=conn.execute('SELECT payload_json FROM learning_decisions WHERE decision_id=?',(origin.get('parent_trace_id'),)).fetchone()
                decision=json.loads(drow[0]) if drow else None
            if source:
                rawrow=conn.execute('SELECT * FROM raw_messages WHERE message_id=?',(source['raw_message_id'],)).fetchone()
                raw=dict(rawrow) if rawrow else None
            input_fingerprint=digest([h,source,events,corrections,quarantine,decision,raw])
            old=conn.execute('SELECT payload_json FROM learning_samples WHERE holding_id=? ORDER BY rowid DESC LIMIT 1',(h['holding_id'],)).fetchone()
            if old:
                previous=json.loads(old[0])
                if previous.get('input_fingerprint',previous['fingerprint'])==input_fingerprint:
                    samples.append(previous); continue
            supersedes=json.loads(old[0])['sample_id'] if old else None
            fingerprint=digest([input_fingerprint,supersedes])
            sample: dict[str, Any]
            try: sample=_derive(h,source,events,corrections,quarantine,decision,raw)
            except (ValueError,KeyError,TypeError) as exc:
                # Retain the original decision cohort for rejected lineage; never
                # promote an invalid current source into observed learning.
                cohort = decision.get('source_mode', 'paper_unknown') if isinstance(decision, dict) else 'paper_unknown'
                sample=dict(holding_id=h['holding_id'],status='rejected',reason=str(exc),
                            cohort=cohort, lineage_status='rejected', source_id=h['flow_id'])
            sample.update(input_fingerprint=input_fingerprint,fingerprint=fingerprint,sample_id='sample:'+digest([h['holding_id'],fingerprint]),supersedes=supersedes)
            conn.execute('INSERT INTO learning_samples VALUES (?,?,?,?,?,?)',(sample['sample_id'],h['holding_id'],fingerprint,sample['supersedes'],canonical(sample),datetime.now(timezone.utc).isoformat()))
            inserted+=1; samples.append(sample)
        conn.commit()
        return dict(inserted=inserted,samples=samples)
    except Exception:
        conn.rollback(); raise
    finally: conn.close()
