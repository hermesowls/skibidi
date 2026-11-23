"""Explicit TEST authorization/quote fixtures, never application policy defaults."""
from datetime import datetime, timezone
from typing import Any


def paper_intent(rec, *, quantity=None):
    rec=dict(rec)
    rec.setdefault('expiration','2026-10-16')
    rec.update(execution_authorized=True, execution_mode='paper',
               intent_id='TEST-intent:'+rec['flow_id'], parent_trace_id='TEST-decision:'+rec['flow_id'],policy_version='TEST-policy-v1')
    expiry=datetime.strptime(rec['expiration'],'%Y-%m-%d')
    rec['occ_symbol']=f"{rec['ticker']}{expiry:%y%m%d}{rec['call_put']}{int(rec['strike']*1000):08d}"
    rec['risk_limits']=dict(max_order_notional=1500,max_gross_notional=5000,max_positions=5,max_evidence_age_seconds=60)
    rec['quote']={k:rec[k] for k in ('ticker','strike','call_put','expiration','occ_symbol','flow_id','intent_id')}
    rec['quote'].update(source='TEST-observed-fixture',evidence_status='observed',quote_id='TEST-entry:'+rec['flow_id'],observed_at=datetime.now(timezone.utc).isoformat(),bid=rec['entry_price'],ask=rec['entry_price'])
    if quantity is not None: rec['quantity']=quantity
    return rec


def persist_source(db, rec):
    """Explicit TEST upstream provenance, always persisted before admission."""
    return db.save_notable_flow(dict(rec,source='TEST-fixture',premium_usd=1000000,
                                    flow_score=90,entry_contract_price=rec['entry_price']))


def lifecycle_evidence(db, holding_id, price, operation='exit') -> dict[str, Any]:
    """Complete deterministic TEST observations; caller still runs real economics."""
    import json
    from datetime import timedelta
    with db._get_connection() as conn:
        row=conn.execute("SELECT payload_json FROM recorded_strategies WHERE holding_id=? AND event_type='autonomous_trade_executed'",(holding_id,)).fetchone()
    origin=json.loads(row[0]); intent=json.loads(origin['intent_json'])['intent']
    clock=datetime.fromisoformat(origin['receipt']['timestamp'])+timedelta(seconds=1 if operation=='trim' else 2)
    quote=dict(intent['quote'],holding_id=holding_id,quote_id='TEST-'+operation,observed_at=clock.isoformat(),bid=price,ask=price)
    return dict(quote=quote,now=clock,max_age=60)
