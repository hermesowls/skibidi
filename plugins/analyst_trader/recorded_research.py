"""Display-only validation of saved research; never resolve current profiles."""
import math


def _finite_display_number(value, scale=1):
    """Reject numbers that cannot be represented by the display formatter."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and math.isfinite(value * scale)
    except OverflowError:
        return False


def display_candidate(value):
    result = dict(value) if isinstance(value, dict) else {}
    for key in ('profile_name', 'decision_id', 'source_id', 'policy_version', 'policy_hash',
                'origin', 'baseline_status', 'enhanced_status', 'novelty', 'calendar_zone', 'reported_side'):
        if not isinstance(result.get(key), str) or not result[key]:
            result[key] = 'Unknown'
    for key in ('baseline_reasons', 'enhancement_unknowns'):
        v = result.get(key)
        if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
            result[key] = ['Unknown']
    v = result.get('filter_provenance')
    if not isinstance(v, dict) or any(not isinstance(k, str) or not isinstance(x, str) for k, x in v.items()):
        result['filter_provenance'] = None
    for key in ('otm_fraction', 'max_otm_fraction'):
        if key not in result or (key == 'max_otm_fraction' and result[key] is None):
            continue
        v = result[key]
        if not _finite_display_number(v, scale=100):
            result.pop(key)
    dte = result.get('dte')
    if type(dte) is not int or not _finite_display_number(dte):
        result['dte'] = 'Unknown'
    if not isinstance(result.get('evidence'), dict):
        result['evidence'] = {}
    return result
