"""Evidence-gated paper monitoring. Quotes are supplied, never inferred from marks."""
import json
import copy
from datetime import datetime, timezone
from .execution_contract import (contract, identity, number, quantity, append_event,
                                 lifecycle_event, money, money_sum, validate_amounts)


def observed_quote(quote, expected, *, now, max_age):
    if not isinstance(quote, dict) or quote.get('evidence_status') != 'observed':
        raise ValueError('Observed quote required')
    if contract(quote) != contract(expected): raise ValueError('Wrong contract')
    for field in ('flow_id','intent_id'):
        if identity(quote.get(field),field) != identity(expected.get(field),field):
            raise ValueError('Wrong '+field)
    if expected.get('holding_id') is not None and quote.get('holding_id') != expected['holding_id']:
        raise ValueError('Wrong holding')
    identity(quote.get('source'),'quote source')
    identity(quote.get('quote_id'),'quote_id')
    bid=number(quote.get('bid'),'bid'); ask=number(quote.get('ask'),'ask')
    if bid > ask: raise ValueError('Crossed quote')
    maximum=number(max_age,'quote max age seconds')
    stamp=datetime.fromisoformat(identity(quote.get('observed_at'),'observed_at').replace('Z','+00:00'))
    if stamp.utcoffset() is None or now.utcoffset() is None: raise ValueError('Aware quote clock required')
    age=(now-stamp).total_seconds()
    if not 0 <= age <= maximum: raise ValueError('Stale/future quote')
    return bid


def registered_deadline(conn, intent, origin):
    """Recover time bound from admitted immutable decision, not caller settings."""
    from .kian_research import validate_paper_lifecycle, validate_policy
    from .learning_evidence import aware_time
    from .learning_store import digest, source_snapshot
    if intent['parent_trace_id'] != origin['parent_trace_id']:
        raise ValueError('Changed entry decision identity')
    row=conn.execute('SELECT payload_json FROM learning_decisions WHERE decision_id=?',
                     (origin['parent_trace_id'],)).fetchone()
    decision=json.loads(row[0]) if row else None
    research=decision and decision.get('recorded_profile',{}).get('profile',{}).get('kian_research')
    if 'research_lifecycle' not in intent and not research:
        return None
    if decision is None: raise ValueError('Missing registered lifecycle decision')
    lifecycle=intent['research_lifecycle']
    profile=decision['recorded_profile']
    source=conn.execute('SELECT * FROM notable_flow WHERE flow_id=?',(intent['flow_id'],)).fetchone()
    raw=conn.execute('SELECT * FROM raw_messages WHERE message_id=?',(decision['raw_source_id'],)).fetchone()
    if (not source or not raw or digest(dict(raw))!=decision['raw_source_hash']
            or digest(source_snapshot(source))!=decision['source_snapshot_hash']):
        raise ValueError('Changed registered lifecycle source')
    validate_policy(profile,profile['profile']['kian_policy_hash'])
    # The separately journaled ARM admission owns the original start. Execution
    # JSON is a redundant copy, not an authority for moving that start. This
    # detects partial persisted-evidence corruption, not rewriting the whole DB.
    admission=conn.execute("SELECT * FROM recorded_strategies WHERE trace_id=? AND event_type='paper_execution_decision'",
                           (origin['parent_trace_id'],)).fetchone()
    entry=conn.execute("SELECT * FROM recorded_strategies WHERE trace_id=? AND event_type='autonomous_trade_executed'",
                       ('paper-entry:'+intent['intent_id'],)).fetchone()
    if admission is None or entry is None:
        raise ValueError('Missing original lifecycle admission')
    admitted=json.loads(admission['payload_json'])
    if not isinstance(admitted,dict): raise ValueError('Malformed lifecycle admission')
    admitted=dict(admitted)
    if admitted.pop('trace_id',None)!=origin['parent_trace_id'] or admitted!=intent:
        raise ValueError('Changed original lifecycle admission')
    holding=conn.execute('SELECT * FROM portfolio_holdings WHERE holding_id=?',
                         (entry['holding_id'],)).fetchone()
    if (holding is None or entry['holding_id']!=origin['holding_id']
            or entry['parent_trace_id']!=admission['trace_id']
            or any(record['flow_id']!=intent['flow_id'] for record in (admission,entry,holding))):
        raise ValueError('Changed lifecycle admission identity')
    entered=aware_time(admitted['research_lifecycle']['entered_at'])
    # These are ordered clock reads, NOT equal timestamps: admission logging,
    # execution and storage can legitimately be delayed and retain microseconds.
    clocks=[entered, aware_time(admission['timestamp']), aware_time(admission['created_at']),
            aware_time(holding['created_at']), aware_time(entry['timestamp']), aware_time(entry['created_at'])]
    if (any(a>b for a,b in zip(clocks,clocks[1:]))
            or aware_time(origin['receipt']['timestamp'])!=clocks[3]
            or aware_time(origin['timestamp'])!=clocks[3]):
        raise ValueError('Inconsistent original admission clocks')
    deadline=aware_time(lifecycle['exit_deadline'])
    if (decision['source_id']!=intent['flow_id'] or decision['profile_version']!=intent['policy_version']
            or entered>aware_time(origin['receipt']['timestamp']) or entered<aware_time(decision['decision_at'])
            or lifecycle!=validate_paper_lifecycle({'baseline_status':'QUALIFIED'},decision,intent,entered)):
        raise ValueError('Invalid registered lifecycle deadline')
    return deadline


def process_quote(db, engine, holding_id, quote, *, now, max_age,
                  requested_operation=None, requested_price=None, requested_outcome=None, trim_pct=0.5):
    """Single lifecycle authority. No caller-owned connection or raw economics API.

    Direct callers request an operation, never authorize one: the same persisted
    TP1/runner/stop rules used by the monitor must select it. Exact direct replay
    returns the saved economic receipt; monitor replay remains an empty update.
    """
    direct=requested_operation is not None
    if requested_operation not in (None,'trim','exit'): raise ValueError('Invalid lifecycle operation')
    pending=None
    def reject(reason):
        if direct: raise ValueError(reason)
        return dict(pending,reason=reason) if pending is not None else None
    if db is None: raise ValueError('Explicit simulation database required')
    quote=copy.deepcopy(quote)
    trim_pct=number(trim_pct,'trim percentage')
    if not 0 < trim_pct <= 1: raise ValueError('Invalid trim percentage')
    conn=db._get_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute("SELECT * FROM portfolio_holdings WHERE holding_id=? AND portfolio_id='autonomous_ai'",(holding_id,)).fetchone()
        if row is None: return reject('Missing holding')
        h=dict(row)
        entry=conn.execute("SELECT trace_id,parent_trace_id,payload_json FROM recorded_strategies WHERE holding_id=? AND event_type='autonomous_trade_executed'",(holding_id,)).fetchone()
        if entry is None: return reject('Missing authorized entry lineage')
        origin=json.loads(entry['payload_json']); intent=json.loads(origin['intent_json'])['intent']
        expected=dict(intent,holding_id=holding_id)
        try:
            if origin['parent_trace_id'] != entry['parent_trace_id']:
                raise ValueError('Changed entry journal decision identity')
            deadline=registered_deadline(conn,intent,origin)
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            pending=dict(holding_id=holding_id,flow_id=h['flow_id'],exit_status='INVALID_DEADLINE',
                         operation=None,economic_receipt=None)
            return reject(str(exc))
        if deadline is not None and now>=deadline and h['status']!='CLOSED':
            pending=dict(holding_id=holding_id,flow_id=h['flow_id'],intent_id=intent['intent_id'],
                         policy_version=intent['policy_version'],exit_status='EXIT_PENDING',
                         exit_deadline=deadline.isoformat(),operation=None,economic_receipt=None)
        if not isinstance(quote,dict): return reject('Observed quote required')
        if requested_price is not None and number(requested_price,'price') != quote.get('bid'):
            return reject('Lifecycle must use observed bid')
        try:
            quote_id=identity(quote.get('quote_id'),'quote_id')
        except ValueError as exc:
            return reject(str(exc))
        trace='paper-monitor:'+holding_id+':'+quote_id
        prior=conn.execute('SELECT payload_json FROM recorded_strategies WHERE trace_id=?',(trace,)).fetchone()
        if prior:
            saved=json.loads(prior[0])
            if saved['quote'] != quote: raise ValueError('QUOTE_ID_CONFLICT')
            if direct:
                if saved.get('operation') != requested_operation or (requested_operation=='trim' and saved.get('trim_pct')!=trim_pct):
                    raise ValueError('LIFECYCLE_ID_CONFLICT')
                if requested_outcome is not None and requested_outcome != saved['outcome']:
                    raise ValueError('LIFECYCLE_ID_CONFLICT')
                return saved
            return None
        if h['status']=='CLOSED': return reject('Closed holding; exact evidence replay required')
        held=dict(ticker=h['ticker'],strike=h['strike'],call_put={'call':'C','put':'P'}.get(h['direction']),expiration=h['expiration'],occ_symbol=h['occ_symbol'])
        try:
            if (h['asset_type']!='option' or contract(held)!=contract(intent) or h['flow_id']!=intent['flow_id']
                    or h['average_cost']!=intent['entry_price']
                    or quantity(h['quantity'])+number(h['contracts_trimmed'],'trimmed',zero=True)!=origin['quantity']):
                return reject('Holding does not match authorized economic identity')
            allowed_age=number(intent['risk_limits']['max_evidence_age_seconds'],'entry quote age limit')
            age=allowed_age if max_age is None and direct else min(number(max_age,'quote max age seconds'),allowed_age)
            bid=observed_quote(quote,expected,now=now,max_age=age)
            stamp=datetime.fromisoformat(quote['observed_at'].replace('Z','+00:00'))
            # Same-tick first observation allowed; never pre-entry. Later ticks strict.
            for boundary in (origin['receipt']['timestamp'],intent['quote']['observed_at']):
                admitted=datetime.fromisoformat(boundary.replace('Z','+00:00'))
                if admitted.utcoffset() is None or stamp < admitted: return reject('Pre-entry lifecycle quote')
        except (ValueError,TypeError,OverflowError) as exc:
            return reject(str(exc))
        flow_row=conn.execute('SELECT * FROM notable_flow WHERE flow_id=?',(h['flow_id'],)).fetchone()
        if flow_row is None: return reject('Missing source')
        flow=dict(flow_row)
        if flow['is_quarantined'] or flow['final_outcome'] not in ('MONITORING','WIN_TP1'): return reject('Ineligible source')
        if any(flow[key]!=intent[key] for key in ('ticker','strike','call_put','expiration')): return reject('Wrong source identity')
        if conn.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND is_quarantined=1 LIMIT 1',(h['flow_id'],)).fetchone():
            return reject('Quarantined source analytics')
        previous=conn.execute("SELECT payload_json FROM recorded_strategies WHERE holding_id=? AND event_type='paper_monitor_outcome' ORDER BY rowid DESC LIMIT 1",(holding_id,)).fetchone()
        if previous:
            old=json.loads(previous[0])['quote']['observed_at']
            if stamp <= datetime.fromisoformat(old.replace('Z','+00:00')): return reject('Nonmonotonic lifecycle quote')
        tp1=number(h['target_tp1'],'tp1'); tp2=number(h['target_tp2'],'tp2'); stop=number(h['target_sl'],'stop')
        entry_price=number(h['average_cost'],'entry')
        if (tp1!=intent.get('tp1_price',entry_price*1.25) or tp2!=intent.get('tp2_price',entry_price*1.5)
                or stop!=(entry_price if h['status']=='TRIMMED' else intent.get('stop_loss_price',entry_price*.75))):
            return reject('Holding targets differ from admitted policy')
        outcome=flow['final_outcome']; operation=None; economic=None
        if bid <= stop:
            outcome='CLOSED_BREAKEVEN' if h['status']=='TRIMMED' and bid==entry_price else 'LOSS_STOP_HIT'
            operation='exit'
        elif deadline is not None and now >= deadline and stamp >= deadline:
            outcome='CLOSED_MAX_HOLD'; operation='exit'
        elif pending is not None:
            return reject('Time exit requires quote at or after deadline')
        elif h['status']=='OPEN' and bid>=tp1:
            operation='trim'
        elif h['status']=='TRIMMED' and bid>=tp2:
            outcome='WIN_TP2'; operation='exit'
        if direct and requested_operation!=operation: return reject('Requested operation not authorized by observed transition')
        qty=quantity(h['quantity'])
        sold=min(qty,max(1.0,float(int(round(qty*trim_pct))))) if operation=='trim' else qty
        remaining=qty-sold if operation else qty
        if operation=='trim': outcome='WIN_TP1' if remaining else 'CLOSED_TP1'
        if requested_outcome is not None and requested_outcome!=outcome: return reject('Outcome label does not match observed transition')
        if operation:
            # Economics are inline behind all evidence gates, inaccessible via _connection.
            pnl=money(bid,sold,100,basis=entry_price); revenue=money(bid,sold,100)
            market=money(bid,remaining,100); unrealized=money(bid,remaining,100,basis=entry_price)
            receipt=dict(portfolio='Autonomous AI Trader',action='AUTONOMOUS_TRIM' if operation=='trim' else 'AUTONOMOUS_'+outcome,
                         holding_id=holding_id,flow_id=h['flow_id'],ticker=h['ticker'],quantity=sold,realized_pnl=pnl,timestamp=now.isoformat())
            if operation=='trim': receipt.update(trimmed_quantity=sold,remaining_quantity=remaining,trim_price=bid,new_stop_loss=entry_price)
            else: receipt.update(closed_quantity=sold,exit_price=bid,outcome_label=outcome)
            request=dict(quote=quote,operation=operation,trim_pct=trim_pct if operation=='trim' else None,outcome_label=outcome)
            economic=lifecycle_event(db,conn,h,operation,request,receipt)
            conn.execute('''UPDATE portfolio_holdings SET quantity=?,contracts_trimmed=?,realized_pnl=?,current_price=?,market_value=?,
                         unrealized_pnl=?,status=?,target_sl=?,outcome_label=?,closed_at=?,updated_at=? WHERE holding_id=?''',
                         (remaining,h['contracts_trimmed']+sold if operation=='trim' else h['contracts_trimmed'],money_sum(h['realized_pnl'],pnl),
                          bid,market,unrealized,'TRIMMED' if remaining else 'CLOSED',entry_price if operation=='trim' else stop,
                          outcome,None if remaining else now.isoformat(),now.isoformat(),holding_id))
            p=conn.execute("SELECT cash_balance,realized_pnl FROM portfolios WHERE portfolio_id='autonomous_ai'").fetchone()
            if p is None: raise ValueError('Missing portfolio')
            cash=money_sum(number(p['cash_balance'],'cash',zero=True),revenue)
            realized=money_sum(number(p['realized_pnl'],'realized',signed=True,zero=True),pnl)
            aggregate=conn.execute("SELECT COALESCE(SUM(market_value),0),COALESCE(SUM(unrealized_pnl),0) FROM portfolio_holdings WHERE portfolio_id='autonomous_ai' AND status IN ('OPEN','TRIMMED')").fetchone()
            equity=money_sum(cash,aggregate[0])
            validate_amounts(cash=cash,realized=realized,pnl=pnl,revenue=revenue,market_value=aggregate[0],unrealized=aggregate[1],equity=equity)
            conn.execute("UPDATE portfolios SET cash_balance=?,realized_pnl=?,total_value=?,unrealized_pnl=?,updated_at=? WHERE portfolio_id='autonomous_ai'",(cash,realized,equity,aggregate[1],now.isoformat()))
        else:
            db.update_holding_market_price(holding_id,bid,_connection=conn)
        pnl_pct=number((bid-entry_price)/entry_price*100,'premium pnl pct',signed=True,zero=True)
        mfe=max(0 if flow['mfe_max_gain_pct'] is None else number(flow['mfe_max_gain_pct'],'mfe',signed=True,zero=True),pnl_pct)
        mae=min(0 if flow['mae_max_drawdown_pct'] is None else number(flow['mae_max_drawdown_pct'],'mae',signed=True,zero=True),pnl_pct)
        conn.execute('UPDATE notable_flow SET final_outcome=?,mfe_max_gain_pct=?,mae_max_drawdown_pct=?,updated_at=? WHERE flow_id=?',(outcome,mfe,mae,now.isoformat(),h['flow_id']))
        result=dict(holding_id=holding_id,ticker=h['ticker'],flow_id=h['flow_id'],intent_id=intent['intent_id'],policy_version=intent['policy_version'],outcome_label=outcome,outcome=outcome,pnl_pct=pnl_pct,quote=quote,economic_receipt=economic,operation=operation,trim_pct=trim_pct if operation=='trim' else None)
        append_event(db,conn,'paper_monitor_outcome',result,trace,economic['trace_id'] if economic else entry['trace_id'])
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def monitor(manager):
    if manager.quote_max_age_seconds is None or manager.quote_reader is None: return []
    from .db import AnalystDatabase
    from .portfolio_engine import DualPortfolioEngine
    db=AnalystDatabase(manager.db_path); engine=DualPortfolioEngine(db)
    results=[]
    for h in db.list_portfolio_holdings('autonomous_ai',status='ACTIVE'):
        quote=manager.quote_reader(dict(h))
        result=process_quote(db,engine,h['holding_id'],quote,now=manager.clock(),max_age=manager.quote_max_age_seconds)
        if result: results.append(result)
    return results
