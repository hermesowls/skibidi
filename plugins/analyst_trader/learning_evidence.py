"""Point-in-time observation validation shared by learning consumers; no I/O."""
import json
import math
from datetime import datetime, timezone


def aware_time(value):
    """Require explicit timezone; date-only cutoffs are midnight UTC."""
    if not isinstance(value, str):
        raise ValueError('timestamp required')
    if len(value) == 10:
        value += 'T00:00:00+00:00'
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('aware timestamp required')
    return result.astimezone(timezone.utc)


def observed_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def observed_mark_path(bars, *, first_seen, received_at, metric='close'):
    """Descriptive completed-minute marks, NOT fills, P&L or horizon labels.

    Basis is the first completed bar wholly after availability; no interpolation.
    Close is the provider's last fill aggregate, not an executable quote.
    """
    from datetime import timedelta
    if metric not in ('close', 'avg_price'):
        raise ValueError('Explicit close or volume-weighted avg_price required')
    cutoff, receipt = aware_time(first_seen), aware_time(received_at)
    marks = {}
    invalid = 0
    conflicts = set()
    for bar in bars:
        try:
            t = aware_time(bar['start_time'])
            n = observed_number(bar.get(metric))
            if n is None or n <= 0:
                invalid += 1
                continue
            if t <= cutoff or t + timedelta(minutes=1) > receipt:
                continue
            if t in marks and marks[t] != n:
                conflicts.add(t)
            marks[t] = n
        except (KeyError, ValueError, TypeError, AttributeError):
            invalid += 1
    points = sorted((t,n) for t,n in marks.items() if t not in conflicts)
    result = dict(status='UNKNOWN', metric=metric, first_seen_at=first_seen,
        available_at=received_at, completed_bars=len(points), invalid_bars=invalid,
        conflicting_minutes=len(conflicts), trade_pnl=None, horizon_outcome='UNKNOWN',
        interpretation='Observed completed-minute mark range; not continuous MFE/MAE',
        coverage='UNKNOWN')
    if len(points) < 2:
        return result
    basis = points[0][1]
    result.update(status='OBSERVED_MARK_PATH', basis_at=points[0][0].isoformat(),
        basis_price=basis, last_at=points[-1][0].isoformat(), last_price=points[-1][1],
        observed_change_pct=(points[-1][1]/basis-1)*100,
        observed_min_price=min(n for _,n in points), observed_max_price=max(n for _,n in points),
        coverage=('GAPPED_OBSERVED_MARKS' if any((b[0]-a[0]).total_seconds()!=60 for a,b in zip(points,points[1:])) else 'CONTIGUOUS_OBSERVED_MINUTES'))
    return result


def baseline_learning_summary(observations, snapshots):
    """Saved captured-cohort description, contract weighted; never learned edge.

    Latest receipt per contract only: overlapping snapshots are not independent
    samples. Existing mark paths use conservative latest linked first-seen.
    Missing raw eligibility diagnostics remain unknown, not baseline passes.
    """
    from statistics import fmean
    baseline = [r for r in observations
        if r['record'].get('raw_threshold_diagnostics', {}).get('failures') == []
        and r['record'].get('raw_threshold_diagnostics', {}).get('unknown') == []]
    contracts = {r['contract'] for r in baseline}
    latest = {}
    for s in snapshots:
        if s['contract'] not in contracts:
            continue
        key = (aware_time(s['received_at']), s['id'])
        previous = latest.get(s['contract'])
        if previous is None or key > (aware_time(previous['received_at']), previous['id']):
            latest[s['contract']] = s
    covered = {c:s for c,s in latest.items()
        if s['observed_mark_path']['status'] == 'OBSERVED_MARK_PATH'}
    changes = [s['observed_mark_path']['observed_change_pct'] for s in covered.values()]
    return dict(version='CAPTURED-BASELINE-DESCRIPTIVE-v1',
        captured_observation_count=len(observations), baseline_observation_count=len(baseline),
        baseline_contract_count=len(contracts),
        eligibility_unknown_or_failed_count=len(observations)-len(baseline),
        policy_hashes=sorted({r['record']['policy_hash'] for r in baseline if r['record'].get('policy_hash')}),
        covered_contract_count=len(covered),
        covered_observation_count=sum(r['contract'] in covered for r in baseline),
        pending_contracts=sorted(contracts-covered.keys()),
        completed_bars_latest_per_contract=sum(s['observed_mark_path']['completed_bars'] for s in latest.values()),
        observed_change_pct_mean=fmean(changes) if changes else None,
        selected_snapshot_ids=[latest[c]['id'] for c in sorted(latest)],
        weighting='ONE_LATEST_RECEIPT_PER_CONTRACT_NOT_INDEPENDENT_EVENTS',
        coverage='CAPTURED_BASELINE_ONLY_MARKET_DISCOVERY_COMPLETENESS_UNKNOWN',
        interpretation='Descriptive option marks after first availability; unequal observed windows, not returns from execution',
        horizon_approval='PENDING', horizon_outcome='UNKNOWN', trade_pnl=None,
        validated_edge=False, out_of_sample_validation='NOT_PERFORMED', execution_authorized=False)


def validate_outcome_config(config, anchors=()):
    """Finite integer elapsed horizons and locally/UTC representable targets."""
    from datetime import timedelta, timezone
    if (not isinstance(config, dict) or set(config) != {'version', 'minutes', 'metric'}
            or not isinstance(config['version'], str) or not config['version'].strip()
            or config['metric'] not in ('close', 'avg_price')
            or not isinstance(config['minutes'], list) or not config['minutes']
            or any(type(n) is not int or not 0 < n <= 5258964959 for n in config['minutes'])
            or sorted(set(config['minutes'])) != config['minutes']):
        raise ValueError('Invalid outcome configuration')
    try:
        for anchor in anchors:
            at = aware_time(anchor)
            for n in config['minutes']:
                target = at + timedelta(minutes=n)
                target.astimezone(timezone.utc)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError('Outcome target is not datetime-representable') from exc


def research_outcomes(observations, snapshots, configurations, *, as_of=None):
    """Reproducible descriptive horizons; no trained model or trading authority.

    Horizons are elapsed minutes from the first wholly post-discovery minute.
    An exact target minute is required; never interpolate across absent marks.
    Overlapping receipts are one path, conflicting marks are excluded.
    """
    import hashlib
    from datetime import timedelta
    cutoff = aware_time(as_of) if as_of else None
    configs = [x for x in configurations if cutoff is None or aware_time(x['received_at']) <= cutoff]
    config = max(configs, key=lambda x:(aware_time(x['received_at']), x['id'])) if configs else None
    configuration_status = 'UNKNOWN_HORIZON'
    if config:
        try:
            validate_outcome_config(config['config'], [config['received_at']] +
                [r['first_seen_at'] for r in observations] +
                [b['start_time'] for s in snapshots for b in s['bars']])
            configuration_status = 'CONFIGURED'
        except (ValueError, TypeError, KeyError, OverflowError):
            configuration_status = 'INVALID_CONFIGURATION'
    usable = config if configuration_status == 'CONFIGURED' else None
    candidates = []
    for row in observations:
        first = aware_time(row['first_seen_at'])
        if cutoff is not None and first > cutoff:
            continue
        sources = [s for s in snapshots if s['contract'] == row['contract']
            and (cutoff is None or aware_time(s['received_at']) <= cutoff)]
        sources.sort(key=lambda s:(aware_time(s['received_at']), s['id']))
        bars = []
        for s in sources:
            for b in s['bars']:
                try:
                    if aware_time(b['start_time']) + timedelta(minutes=1) <= aware_time(s['received_at']):
                        bars.append(b)
                except (ValueError, KeyError, TypeError):
                    continue
        receipt = max([first] + [aware_time(s['received_at']) for s in sources])
        metric = usable['config']['metric'] if usable else 'close'
        path = observed_mark_path(bars, first_seen=row['first_seen_at'], received_at=receipt.isoformat(), metric=metric)
        # Use the same conflict/completion rules as the shared observed path.
        values, conflicts = {}, set()
        for b in bars:
            try:
                t, n = aware_time(b['start_time']), observed_number(b.get(metric))
                if t <= first or n is None or n <= 0:
                    continue
                if t in values and values[t] != n:
                    conflicts.add(t)
                values[t] = n
            except (ValueError, KeyError, TypeError):
                continue
        points = sorted((t,n) for t,n in values.items() if t not in conflicts)
        outcomes = []
        for minutes in usable['config']['minutes'] if usable else []:
            outcome = dict(minutes=minutes, eligible=bool(points), status='PENDING',
                mark_return_pct=None, trade_pnl=None, coverage='UNKNOWN', target_at=None,
                reason='NO_COMPLETED_POST_FIRST_SEEN_BASIS')
            if points:
                basis, price = points[0]
                target = basis + timedelta(minutes=minutes)
                segment = [b for b in bars if aware_time(b['start_time']) <= target]
                measured = observed_mark_path(segment, first_seen=row['first_seen_at'], received_at=receipt.isoformat(), metric=metric)
                outcome.update(target_at=target.isoformat(), basis_at=basis.isoformat(), basis_price=price,
                    reason='EXACT_TARGET_MARK_UNAVAILABLE', coverage=measured['coverage'])
                if target in dict(points):
                    outcome.update(status='COMPLETED', reason=None, target_price=dict(points)[target],
                        mark_return_pct=(dict(points)[target]/price-1)*100)
            outcomes.append(outcome)
        provenance = [dict(id=s['id'], raw_hash=s['raw_hash'], received_at=s['received_at'], contract_identity=s['contract_identity']) for s in sources]
        inputs = dict(event_id=row['event_id'], raw_hash=row['raw_hash'], first_seen_at=row['first_seen_at'],
            config_id=config['id'] if config else None, sources=provenance, as_of=as_of)
        candidates.append(dict(contract=row['contract'], inputs=inputs,
            input_sha256=hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest(),
            baseline_diagnostics=row['record'].get('raw_threshold_diagnostics'),
            status=configuration_status, outcomes=outcomes,
            observed_mark_path=path, priority=dict(version='COVERAGE-HEURISTIC-v1',
                kind='EVIDENCE_COVERAGE_HEURISTIC_NOT_LEARNED_EDGE',
                score=2 if not points else (1 if any(o['status']=='PENDING' for o in outcomes) else 0),
                rationale='Missing evidence first; retention independent of priority'),
            identity_confidence=sorted({s['contract_identity'] for s in sources}) or ['UNKNOWN']))
    return dict(version='DESCRIPTIVE-HORIZONS-v1', configuration=config, configuration_status=configuration_status, candidates=candidates,
        interpretation='Observed option mark returns, not trade P&L; elapsed minutes, no interpolation',
        adaptive_ranking=dict(status='INSUFFICIENT_SAMPLE', validation='QUALIFIED_TIME_ORDERED_VALIDATION_NOT_PERFORMED',
            validated_edge=False, model_performance=None), execution_authorized=False, activation=False)


def observed_outcome(row, as_of):
    """A label alone (including an expected WIN) is not outcome measurement."""
    try:
        metrics=row.get('quant_metrics_json') or {}
        if isinstance(metrics,str): metrics=json.loads(metrics)
        e=metrics['outcome_evidence']
        if (e['status']!='observed' or not e['evidence_id'] or e['source_id']!=row['flow_id']
            or e['label']!=row['final_outcome']
            or e['contract']!={k:row[k] for k in ('ticker','strike','call_put','expiration')}
            or not aware_time(row['trade_timestamp'])<=aware_time(e['observed_at'])<=as_of):
            return None
        return e['label']
    except (KeyError,ValueError,TypeError):
        return None


def qualified_oi(row, as_of, *, context='XNYS_REGULAR'):
    """Validate observed next-session OI, never infer a provider update.

    TEST_LEGACY is an explicit caller-only compatibility seam, not a field an
    incoming provider row can opt into. The normal path requires observed_at
    on both observations and verifies the immediate maintained-calendar open.
    """
    try:
        if context not in ('XNYS_REGULAR', 'TEST_LEGACY'):
            return None
        metrics = row.get('quant_metrics_json') or {}
        if isinstance(metrics, str):
            metrics = json.loads(metrics)
        e = metrics['oi_evidence']
        from zoneinfo import ZoneInfo
        trade_at = aware_time(row['trade_timestamp'])
        if (e['flow_id'] != row['flow_id'] or e['session_timezone'] != 'America/New_York'
                or trade_at.astimezone(ZoneInfo(e['session_timezone'])).date().isoformat() != e['session']
                or aware_time(e['initial']['available_at']) > trade_at):
            return None
        if not e['source'] or not e['session_evidence_id']:
            return None
        if e['contract'] != {k: row[k] for k in ('ticker', 'strike', 'call_put', 'expiration')}:
            return None
        a, b = e['initial'], e['next']
        if not e['session'] < e['next_session'] or a['session'] != e['session'] or b['session'] != e['next_session']:
            return None
        opening = aware_time(e['next_open_at'])
        if opening.date().isoformat() != e['next_session'] or opening > as_of:
            return None
        if context != 'TEST_LEGACY':
            from .session_calendar import next_session, check_coverage
            check_coverage(as_of)
            session, following, actual_open = next_session(trade_at)
            if (e['session'], e['next_session'], opening) != (session, following, actual_open):
                return None
            if not opening <= aware_time(b['observed_at']) <= aware_time(b['available_at']) <= as_of:
                return None
            if not aware_time(a['observed_at']) <= aware_time(a['available_at']) <= trade_at <= as_of:
                return None
        for obs, key in ((a, 'initial_oi'), (b, 'next_day_oi')):
            n = observed_number(obs['value'])
            if n is None or n < 0 or not n.is_integer() or n != row.get(key) or not obs['evidence_id']:
                return None
            if aware_time(obs['available_at']) > as_of:
                return None
        if aware_time(a['available_at']) >= aware_time(b['available_at']):
            return None
        return a['value'], b['value']
    except (KeyError, ValueError, TypeError, ImportError, OverflowError):
        return None
