"""Individual REST Option_Trade adapter; documentation is not market evidence.

No aliases from flow-alert totals. Missing optional evidence remains unknown.
Decimal text is retained exactly; float mirrors serve the legacy screen only.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from .execution_contract import contract, identity, number
from .learning_store import canonical

PATH = '/api/option-trades'


def decimal_field(raw, key, *, required=False):
    value = raw.get(key)
    if value is None and not required:
        return None
    if type(value) is not str or not value or value != value.strip():
        raise ValueError('decimal string required: ' + key)
    try:
        d = Decimal(value)
    except InvalidOperation:
        raise ValueError('invalid decimal: ' + key) from None
    if not d.is_finite() or d <= 0 or d > 2**53-1:
        raise ValueError('decimal bounds: ' + key)
    number(float(d), key)
    return d


def canonicalize_trade(raw, cohort):
    if not isinstance(raw, dict) or len(canonical(raw)) > 32768:
        raise ValueError('Malformed/oversized Option_Trade')
    event = identity(raw.get('id'), 'option trade id')
    stamp = raw.get('executed_at')
    if type(stamp) is not str or 'T' not in stamp:
        raise ValueError('execution timestamp required')
    executed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    if executed.tzinfo is None or executed.utcoffset() != timedelta(0):
        raise ValueError('UTC execution timestamp required')
    strike = decimal_field(raw, 'strike', required=True)
    if strike*1000 != (strike*1000).to_integral_value():
        raise ValueError('fractional OCC strike')
    expiry = raw.get('expiry'); date.fromisoformat(expiry)
    right = {'call':'C', 'put':'P'}.get(raw.get('option_type'))
    e = dict(ticker=raw.get('underlying_symbol'), call_put=right, expiration=expiry,
        strike=float(strike), contract_symbol=raw.get('option_chain_id'))
    contract(dict(e, occ_symbol=e['contract_symbol']))
    premium = decimal_field(raw, 'premium')
    spot = decimal_field(raw, 'underlying_price')
    for key in ('size','volume','open_interest'):
        v = raw.get(key)
        if v is not None and (type(v) is not int or not (1 if key == 'size' else 0) <= v <= 2**53-1):
            raise ValueError('integer contracts required: '+key)
    for key in ('is_agg','canceled'):
        if raw.get(key) is not None and type(raw[key]) is not bool:
            raise ValueError('boolean required: '+key)
    simple = raw.get('is_agg') is False
    source_id = cohort + ':UW_OPTION_TRADES:' + event
    e.update(source='UW_OPTION_TRADES', source_id=source_id, evidence_id=event,
        provider_event_id=event, observed_at=stamp, spot_observed_at=None,
        spot_price=float(spot) if spot is not None else None,
        premium_decimal=raw.get('premium'), premium_usd=float(premium) if premium is not None and simple else None,
        size=raw.get('size') if simple else None, volume=raw.get('volume'),
        open_interest=raw.get('open_interest'), complex_trade=None, corrected=None,
        is_agg=raw.get('is_agg'), canceled=raw.get('canceled'),
        reported_side=raw.get('tags'),
        premium_definition='single_print_usd' if simple else 'UNKNOWN',
        size_definition='single_print_contracts' if simple else 'UNKNOWN',
        volume_definition='aggregate_contract_session')
    return e
