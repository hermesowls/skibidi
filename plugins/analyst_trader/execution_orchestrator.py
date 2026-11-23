"""Research evidence display; no qualified classifier or execution authorization.

The recovered weighting formula was not a calibrated success model. Caller pass
flags and is_calibrated are not calibration evidence. Until an independently
qualified evidence/calibration consumer exists, no grade or probability is issued.
This does not replace the strategy with another invented strategy.
"""
from datetime import datetime, timezone
import math


class ExecutionOrchestrator:
    def evaluate_dream_setup(self, ticker, price, ofi_info, alpha_info,
                             gex_info, ta_info, event_info):
        from plugins.analyst_trader.quant_storage_cache import observed_l2
        ticker = ticker.upper()
        valid_price = (type(price) in (int, float) and math.isfinite(price) and price > 0)
        # L2 has an existing explicit schema/provenance contract. Other inputs
        # have no qualified verifier: never promote their booleans to facts.
        l2_valid = isinstance(ofi_info, dict) and observed_l2(ofi_info, ticker)
        checklist = []
        for key, info in [('flow', ofi_info), ('gex', gex_info), ('ta', ta_info),
                          ('events', event_info), ('social', event_info)]:
            valid = key == 'flow' and l2_valid
            checklist.append({'id': key, 'passed': False,
                'status': 'observed_research_only' if valid else 'unavailable',
                'data_breakdown': {k: info[k] for k in ('dataset_source', 'schema', 'observed_at',
                    'ofi_score', 'hawkes_intensity', 'queue_depletion_velocity') if k in info} if valid else {},
                'reason': 'STRATEGY_NOT_QUALIFIED' if valid else 'UNVERIFIED_EVIDENCE'})
        return {'ticker': ticker, 'current_price': price if valid_price else None,
            'hurdle_passed': False, 'is_a_plus_dream_setup': False,
            'setup_grade': 'D NO TRADE / DATA UNAVAILABLE OR VETOED',
            'execution_bias': 'FAIL_CLOSED_INVALID_PRICE_OR_UNVERIFIED_EVIDENCE',
            'status': 'DATA_UNAVAILABLE_OR_VETOED', 'execution_authorized': False,
            'checklist': checklist, 'checklist_passed_count': 0, 'checklist_total': len(checklist),
            'conviction_score': None, 'p_success': None, 'brier_score': None,
            'gex_regime': None, 'target_node': None, 'expected_arrival_display': None,
            'calibration_status': 'unavailable',
            'reason': 'No qualified non-L2 evidence verifier or calibrated success model; caller flags are insufficient'}
