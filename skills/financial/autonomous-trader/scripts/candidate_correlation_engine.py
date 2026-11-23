#!/usr/bin/env python3
"""Exploratory descriptions of observed candidates, never inferred trade outcomes."""
import json
import math
import sqlite3
from datetime import datetime, timezone
from plugins.analyst_trader.learning_evidence import qualified_oi, observed_outcome
from pathlib import Path
from typing import Any, Dict, Optional
from plugins.analyst_trader.db import AnalystDatabase, get_db_path
from hermes_constants import get_hermes_home


def generate_occ_symbol(ticker: str, expiration: str, call_put: str, strike: float) -> Optional[str]:
    """Return a canonical identity only when all contract fields are available."""
    import re
    if not isinstance(ticker, str) or not re.fullmatch('[A-Z]{1,6}', ticker):
        return None
    if call_put not in ('C', 'P') or isinstance(strike, bool):
        return None
    try:
        expiry = datetime.strptime(expiration, '%Y-%m-%d')
        from decimal import Decimal
        mills = Decimal(str(strike)) * 1000
        if not mills.is_finite() or mills <= 0 or mills > 99999999 or mills != mills.to_integral_value():
            return None
    except (ValueError, TypeError, ArithmeticError):
        return None
    return f'{ticker:<6}{expiry:%y%m%d}{call_put}{int(mills):08d}'


def _observed(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


class CandidateCorrelationEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(get_db_path())
        self.db = AnalystDatabase(Path(self.db_path))

    def run_candidate_correlation_audit(self) -> Dict[str, Any]:
        if not Path(self.db_path).is_file():
            return {'status': 'unavailable', 'reason': 'Database does not exist'}
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            records = [dict(r) for r in conn.execute('''SELECT n.* FROM notable_flow n
                WHERE COALESCE(n.is_quarantined,0)=0 AND NOT EXISTS (
                    SELECT 1 FROM flow_candidate_analytics a WHERE a.flow_id=n.flow_id
                    AND COALESCE(a.is_quarantined,0)<>0)''')]
        wins = losses = scratches = runners = partials = high_total = high_wins = 0
        strategies = {}
        for r in records:
            outcome = r.get('final_outcome') or 'MONITORING'
            measured_outcome = observed_outcome(r, datetime.now(timezone.utc))
            # WIN_TP1 is a partial lifecycle state, not a resolved holding.
            win = measured_outcome in ('WIN_TP2', 'WIN_RUNNER_7X')
            loss = measured_outcome in ('STOP_LOSS', 'LOSS', 'LOSS_STOP', 'LOSS_STOP_HIT', 'CLOSED_LOSS')
            scratch = measured_outcome in ('SCRATCH', 'BREAKEVEN_STOP', 'CLOSED_BREAKEVEN')
            resolved = win or loss or scratch
            wins += int(win); losses += int(loss); scratches += int(scratch)
            runners += int(win); partials += int(outcome == 'WIN_TP1')
            mfe = _observed(r.get('mfe_max_gain_pct'))
            mae = _observed(r.get('mae_max_drawdown_pct'))
            entry = _observed(r.get('entry_contract_price'))
            if entry is not None and entry <= 0:
                entry = None
            ratio = _observed(r.get('vol_to_oi_ratio'))
            oi_pair = qualified_oi(r, datetime.now(timezone.utc))
            initial, next_oi = oi_pair if oi_pair is not None else (None, None)
            change = (next_oi - initial) / initial * 100 if initial is not None and initial > 0 and next_oi is not None else None
            peak = _observed(entry * (1 + mfe / 100)) if entry is not None and mfe is not None else None
            trough = _observed(entry * (1 - mae / 100)) if entry is not None and mae is not None else None
            name = r.get('strategy_name') or 'UNKNOWN'
            stats = strategies.setdefault(name, {'total_candidates': 0, 'resolved_candidates': 0, 'wins': 0, 'mfe_values': []})
            stats['total_candidates'] += 1; stats['resolved_candidates'] += int(resolved); stats['wins'] += int(win)
            if mfe is not None:
                stats['mfe_values'].append(mfe)
            if resolved and ratio is not None and ratio >= 2.5:
                high_total += 1; high_wins += int(win)
            self.db.save_flow_candidate_analytics({
                'analytics_id': 'fca_' + r['flow_id'], 'flow_id': r['flow_id'], 'ticker': r['ticker'],
                'contract_symbol': generate_occ_symbol(r['ticker'], r.get('expiration'), r.get('call_put'), r.get('strike')),
                'flow_tier': 'UNCLASSIFIED', 'conviction_score': _observed(r.get('flow_score')),
                'entry_price': entry, 'peak_price': peak, 'trough_price': trough, 'mfe_pct': mfe, 'mae_pct': mae,
                'intraday_vol': _observed(r.get('intraday_volume')), 'initial_oi': initial, 'next_day_oi': next_oi,
                'oi_change_pct': change, 'is_overnight_hold': None, 'outcome_label': outcome,
                'correlations_json': {'classification': 'exploratory_unvalidated', 'vol_to_oi_ratio': ratio,
                    'strategy_name': name, 'case_study_autopsy': 'Observed fields only. Missing observations remain unknown. Aggregate OI cannot identify whether a particular whale held overnight.'}})
        resolved_count = wins + losses + scratches
        attribution = {}
        for name, values in strategies.items():
            excursions = values.pop('mfe_values')
            n = values['resolved_candidates']
            attribution[name] = {**values, 'win_rate_pct': round(values['wins']/n*100,1) if n else None,
                'avg_mfe_pct': round(sum(excursions)/len(excursions),1) if excursions else None,
                'mfe_observation_count': len(excursions), 'classification': 'exploratory_unvalidated'}
        result = {'total_candidates_analyzed': len(records), 'total_candidates': len(records),
            'resolved_candidates': resolved_count, 'unresolved_candidates': len(records)-resolved_count,
            'overall_win_rate_pct': round(wins/resolved_count*100,1) if resolved_count else None,
            'high_vol_oi_win_rate_pct': round(high_wins/high_total*100,1) if high_total else None,
            'high_vol_oi_resolved_count': high_total, 'total_runners_detected': runners,
            'total_tp1_trims': partials, 'total_scratches': scratches, 'total_stops': losses,
            'overnight_holds_detected': None, 'strategy_attribution': attribution,
            'classification': 'exploratory_unvalidated',
            'key_learnings': ['Descriptive counts only; no calibrated probability, causal inference or validated trading edge.'],
            'timestamp': datetime.now().isoformat()}
        directory = get_hermes_home() / 'strategy_memory'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f'correlation_report_{datetime.now():%Y%m%d}.json').write_text(json.dumps(result, indent=2))
        return result


if __name__ == '__main__':
    print(json.dumps(CandidateCorrelationEngine().run_candidate_correlation_audit(), indent=2))
