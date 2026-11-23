"""Paper execution contracts. No broker access; callers supply decision identity."""
import json
import copy
import math
import re
from datetime import date
from decimal import Decimal, localcontext


def money(price, units: float = 1, multiplier: float = 1, *, basis: float = 0):
    """Decimal input economics, converted once at the SQLite REAL boundary."""
    with localcontext() as ctx:
        ctx.prec = 80
        value=(Decimal(str(price))-Decimal(str(basis)))*Decimal(str(units))*Decimal(str(multiplier))
        result=float(value)
    number(result, 'economic amount', signed=True, zero=True)
    if value and not result: raise ValueError('Economic amount underflow')
    return result


def money_sum(left, right):
    with localcontext() as ctx:
        ctx.prec = 80
        result=float(Decimal(str(left))+Decimal(str(right)))
    return number(result, 'economic sum', signed=True, zero=True)



def number(value, name, *, zero=False, signed=False):
    # SQLite REAL's exact-integer envelope bounds all persisted economics.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Invalid numeric ' + name)
    if abs(value) > 2**53 - 1 or not math.isfinite(value) or (not signed and (value < 0 if zero else value <= 0)):
        raise ValueError('Out of bounds ' + name)
    return float(value)


def identity(value, name):
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 256:
        raise ValueError('Missing/invalid ' + name)
    return value


MICRO_MAX_CONTRACT_COST = 200.0  # Existing ARM recommendation affordability rule.


def quantity(value, asset_type='option'):
    value = number(value, 'quantity')
    if asset_type == 'option' and not value.is_integer():
        raise ValueError('Fractional option contracts')
    return value


def validate_amounts(**values):
    for key, value in values.items():
        number(value, key, zero=True, signed=key in ('pnl','unrealized','realized'))


def contract(data):
    ticker=identity(data.get('ticker'),'ticker')
    if not re.fullmatch(r'[A-Z]{1,6}',ticker): raise ValueError('Invalid ticker')
    right=data.get('call_put')
    if right not in ('C','P'): raise ValueError('Invalid option right')
    expiry=identity(data.get('expiration'),'expiration')
    parsed=date.fromisoformat(expiry)
    if parsed.isoformat()!=expiry: raise ValueError('Noncanonical expiry')
    strike=number(data.get('strike'),'strike')
    if strike*1000 != int(strike*1000) or strike*1000 > 99999999:
        raise ValueError('Invalid OCC strike')
    occ=f'{ticker}{parsed:%y%m%d}{right}{int(strike*1000):08d}'
    if data.get('occ_symbol') not in (occ,f'{ticker:<6}{parsed:%y%m%d}{right}{int(strike*1000):08d}'):
        raise ValueError('OCC identity mismatch')
    return occ


def validate_intent(data, tier):
    data = copy.deepcopy(data)
    if data.get('execution_authorized') is not True or data.get('execution_mode')!='paper':
        raise ValueError('Explicit paper simulation authorization required')
    for key in ('intent_id','flow_id','parent_trace_id','policy_version'):
        identity(data.get(key),key)
    contract(data)
    if tier not in ('micro','growing','established'): raise ValueError('Invalid tier')
    price = number(data.get('entry_price'),'entry_price')
    tp1 = number(data.get('tp1_price',price*1.25),'tp1')
    tp2 = number(data.get('tp2_price',price*1.5),'tp2')
    stop = number(data.get('stop_loss_price',price*.75),'stop')
    if not stop < price < tp1 <= tp2: raise ValueError('Invalid target ordering')
    if 'quantity' in data: quantity(data['quantity'])
    if tier == 'micro' and price*100 > MICRO_MAX_CONTRACT_COST:
        raise ValueError('Micro affordability policy')
    return json.dumps({'intent':data,'account_tier':tier},sort_keys=True,allow_nan=False,separators=(',',':'))


def lifecycle_replay(conn, holding_id, operation, request):
    trace_id = 'paper-' + operation + ':' + holding_id
    row = conn.execute('SELECT payload_json FROM recorded_strategies WHERE trace_id=?', (trace_id,)).fetchone()
    if row:
        saved = json.loads(row[0])
        if saved['request'] != request:
            raise ValueError('LIFECYCLE_ID_CONFLICT')
        return saved['receipt']
    return None


def lifecycle_event(db, conn, holding, operation, request, receipt):
    entry = conn.execute("SELECT trace_id,payload_json FROM recorded_strategies WHERE holding_id=? AND event_type='autonomous_trade_executed'", (holding['holding_id'],)).fetchone()
    if entry is None: raise ValueError('Missing authorized entry lineage')
    origin = json.loads(entry['payload_json'])
    intent = json.loads(origin['intent_json'])['intent']
    held = dict(ticker=holding['ticker'],strike=holding['strike'],expiration=holding['expiration'],
                call_put={'call':'C','put':'P'}.get(holding['direction']),occ_symbol=holding['occ_symbol'])
    if (holding['asset_type'] != 'option' or contract(held) != contract(intent)
            or holding['flow_id'] != intent['flow_id'] or holding['average_cost'] != intent['entry_price']
            or quantity(holding['quantity']) + number(holding['contracts_trimmed'],'trimmed',zero=True) != origin['quantity']):
        raise ValueError('Holding does not match authorized economic identity')
    receipt.update(intent_id=origin['intent_id'],policy_version=origin['policy_version'],
                   parent_trace_id=entry['trace_id'],trace_id='paper-'+operation+':'+holding['holding_id'])
    append_event(db, conn, 'autonomous_trade_'+('trimmed' if operation=='trim' else 'closed'),
                 dict(receipt,request=request,receipt=receipt),receipt['trace_id'],entry['trace_id'])
    return receipt


def append_event(db, conn, event, payload, trace_id, parent):
    return db.save_recorded_strategy(dict(trace_id=trace_id,event_type=event,ticker=payload['ticker'],
        action=payload.get('action',event),holding_id=payload['holding_id'],flow_id=payload['flow_id'],
        parent_trace_id=parent,quantity=payload.get('quantity'),realized_pnl=payload.get('realized_pnl'),
        entry_price=payload.get('entry_price'),exit_price=payload.get('exit_price',payload.get('trim_price')),
        outcome_label=payload.get('outcome_label'),payload_json=payload), connection=conn)
