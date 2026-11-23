"""Read-only full-history dashboard statistics, not a learning/policy promotion.

Step3 owns economic derivation and correction precedence. This view deliberately
keeps legacy/test/observed cohorts separate and never imports learning samples.
"""
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from typing import Any
from .learning_store import _derive, aware_time as parse_cutoff


def aware_time(value):
    # Learning cutoffs permit dates; event/mark observations must not invent a
    # midnight timezone for date-only evidence.
    if not isinstance(value, str) or len(value) <= 10:
        raise ValueError('Explicit aware observation timestamp required')
    return parse_cutoff(value)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def mark_evidence(holding, cutoff):
    """Historical estimates may be retained, never described as current after 60s."""
    try:
        at = aware_time(holding.get('last_price_updated_at'))
        if at > cutoff:
            return 'unknown', 'mark unavailable at snapshot'
    except (ValueError, TypeError, AttributeError):
        return 'unknown', 'mark timestamp invalid or unavailable'
    if not all(finite(holding.get(k)) for k in ('market_value', 'unrealized_pnl')):
        return 'unknown', 'mark economics unavailable'
    return ('stale' if (cutoff-at).total_seconds() > 60 else 'fresh'), None


def aggregate(samples):
    valid = [s for s in samples if finite(s.get('gross_pnl'))]
    closed = [s for s in valid if s['status'] == 'resolved']
    net_closed = [s for s in closed if finite(s.get('net_pnl'))]
    excluded = len(samples) - len(valid)
    unknown_costs = sum(s.get('costs') is None for s in valid)
    basis = sum(s['basis'] for s in valid)
    gross = sum(s['gross_pnl'] for s in valid) if valid else None
    net = sum(s['net_pnl'] for s in valid) if valid and not unknown_costs else None
    reasons = defaultdict(int)
    for s in samples:
        if s not in valid:
            reasons[s['status']] += 1
    open_samples = [s for s in samples if s['holding_status'] in ('OPEN', 'TRIMMED')]
    marks = [s['estimated_unrealized_pnl'] for s in open_samples if finite(s.get('estimated_unrealized_pnl'))]
    return dict(holding_count=len(samples), eligible_count=len(valid), excluded_count=excluded,
        excluded_reasons=dict(reasons), open_count=len(open_samples), closed_count=len(closed),
        unknown_cost_count=unknown_costs, known_gross_subtotal=gross,
        gross_realized_pnl=gross if not excluded else None,
        net_realized_pnl=net if not excluded else None,
        initial_economic_basis=basis if valid and not excluded else None,
        gross_return_pct=gross/basis*100 if gross is not None and basis and not excluded else None,
        net_return_pct=net/basis*100 if net is not None and basis and not excluded else None,
        gross_win_rate_pct=sum(s['gross_pnl'] > 0 for s in closed)/len(closed)*100 if closed else None,
        net_win_rate_pct=sum(s['net_pnl'] > 0 for s in net_closed)/len(net_closed)*100 if net_closed else None,
        net_closed_count=len(net_closed), gross_wins=sum(s['gross_pnl'] > 0 for s in closed),
        estimated_unrealized_pnl=sum(marks) if len(marks) == len(open_samples) and open_samples else (0.0 if samples and not open_samples else None),
        unknown_mark_count=len(open_samples)-len(marks),
        stale_mark_count=sum(s.get('mark_freshness') == 'stale' for s in open_samples),
        mark_policy='Historical nonexecutable estimates retained; older than 60s stale, not current. Invalid/future timestamps excluded.',
        mark_status='estimated_nonexecutable' if marks else 'unknown',
        outcome_basis='one terminal holding; gross and observed-cost net denominators separate')


def statistics(db, portfolio_id=None):
    conn = db._get_connection()
    samples = []
    snapshot_at = datetime.now(timezone.utc)
    try:
        conn.execute('BEGIN')
        query = 'SELECT * FROM portfolio_holdings'
        params = ()
        if portfolio_id is not None:
            query += ' WHERE portfolio_id=?'
            params = (portfolio_id,)
        for row in conn.execute(query, params).fetchall():
            h = dict(row)
            sample: dict[str, Any]
            def one(sql, params):
                row = conn.execute(sql, params).fetchone()
                return dict(row) if row else None
            source = one('SELECT * FROM notable_flow WHERE flow_id=?', (h['flow_id'],))
            events = [dict(e) for e in conn.execute('SELECT * FROM recorded_strategies WHERE holding_id=? ORDER BY timestamp,trace_id', (h['holding_id'],))]
            quarantine = bool(conn.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND COALESCE(is_quarantined,0)<>0', (h['flow_id'],)).fetchone())
            try:
                corrections = [json.loads(c[0]) for c in conn.execute('SELECT payload_json FROM learning_corrections WHERE holding_id=?', (h['holding_id'],))]
                if h.get('asset_type') != 'option' or not isinstance(h.get('occ_symbol'), str) or not h['occ_symbol']:
                    raise ValueError('Missing supported option-contract economic identity')
                if any(not isinstance(c, dict) or aware_time(c['observed_at']) > snapshot_at for c in corrections):
                    raise ValueError('Correction unavailable at snapshot')
                entry = next((e for e in events if e['event_type'] == 'autonomous_trade_executed'), None)
                decision = None
                if entry:
                    origin = json.loads(entry['payload_json'])
                    d = one('SELECT payload_json FROM learning_decisions WHERE decision_id=?', (origin.get('parent_trace_id'),))
                    decision = json.loads(d['payload_json']) if d else None
                raw = one('SELECT * FROM raw_messages WHERE message_id=?', (source['raw_message_id'],)) if source else None
                # Current holding economics cannot be projected backwards across
                # unavailable journal evidence. Validate both recorded availability
                # and the economic event clock; ties at the cutoff are available.
                economic = [e for e in events if e['event_type'] in (
                    'autonomous_trade_executed', 'autonomous_trade_trimmed', 'autonomous_trade_closed')]
                entry_times = None
                terminal_times = None
                for event in economic:
                    payload = json.loads(event['payload_json'])
                    times = (aware_time(event['timestamp']), aware_time(payload['timestamp']))
                    if any(t > snapshot_at for t in times):
                        raise ValueError('Economic event unavailable at snapshot')
                    if event['event_type'] == 'autonomous_trade_executed':
                        entry_times = times
                    if event['event_type'] == 'autonomous_trade_closed':
                        terminal_times = times
                for event in economic:
                    times = (aware_time(event['timestamp']), aware_time(json.loads(event['payload_json'])['timestamp']))
                    if entry_times and any(t < start for t, start in zip(times, entry_times)):
                        raise ValueError('Economic event precedes entry')
                    if terminal_times and any(t > end for t, end in zip(times, terminal_times)):
                        raise ValueError('Economic event follows terminal exit')
                sample = _derive(h, source, events, corrections, quarantine, decision, raw, include_partial=True)
                if sample.get('available_at') and aware_time(sample['available_at']) > snapshot_at:
                    raise ValueError('Outcome unavailable at snapshot')
                if sample.get('basis') is not None:
                    remaining = sample['initial_quantity'] - sample['realized_quantity']
                    if h['quantity'] != remaining or (h['status'] == 'CLOSED') != (remaining == 0):
                        raise ValueError('Holding quantity/status inconsistent with journal')
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                sample = dict(holding_id=h['holding_id'], status='invalid_evidence', cohort='paper_unknown', reason=str(exc))
            freshness, mark_reason = mark_evidence(h, snapshot_at)
            sample.update(strategy_name=h.get('strategy_name') or 'Unknown strategy',
                          portfolio_id=h['portfolio_id'], holding_status=h['status'],
                          mode='paper_options' if h['asset_type'] == 'option' else 'paper_underlying',
                          estimated_unrealized_pnl=h['unrealized_pnl'] if freshness != 'unknown' and finite(sample.get('gross_pnl')) else None,
                          estimated_market_value=h['market_value'] if freshness != 'unknown' and finite(sample.get('gross_pnl')) else None,
                          mark_freshness=freshness, mark_reason=mark_reason,
                          mark_as_of=h.get('last_price_updated_at'))
            samples.append(sample)
        groups = defaultdict(list)
        cohorts = defaultdict(list)
        for sample in samples:
            groups[sample['strategy_name']].append(sample)
            cohorts[sample['cohort']].append(sample)
        return dict(as_of=snapshot_at.isoformat(),
            provenance='committed holdings plus complete economic journal and observed corrections; read-only snapshot',
            mode='paper', history='complete', qualification='descriptive_only_not_live_qualified',
            cohort='all_explicitly_separated_below', total=aggregate(samples),
            by_strategy={k: aggregate(v) for k, v in groups.items()},
            by_archetype={k: aggregate([s for s in samples if k in s['strategy_name'].upper()])
                          for k in ('DREAM', 'GAMMA', 'EMA', 'WHALE')},
            by_cohort={k: aggregate(v) for k, v in cohorts.items()}, holdings=samples)
    finally:
        conn.rollback()
        conn.close()
