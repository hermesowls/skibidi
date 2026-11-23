"""Offline ledger recovery. Caller intent is never authenticated authority."""
import base64
import hashlib
import json
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate(ledger):
    if not isinstance(ledger, dict):
        raise ValueError('Incompatible ledger')
    if 'runs' in ledger:
        if not isinstance(ledger['runs'], dict) or 'authorization' in ledger:
            raise ValueError('Incompatible ledger')
        for run in ledger['runs'].values():
            validate_run(run)
    elif ledger:
        validate_run(ledger)


def validate_run(run):
    if (not isinstance(run, dict) or not isinstance(run.get('authorization'), dict)
            or type(run.get('attempts')) is not int or run['attempts'] < 0
            or ('claims' in run and not isinstance(run['claims'], list))):
        raise ValueError('Incompatible ledger')


def safe_paths(*paths):
    for path in paths:
        if any(x.is_symlink() for x in (path, *path.parents)) or (path.is_file() and path.stat().st_nlink != 1):
            raise ValueError('Unsafe cycle destination')


def followup_reference(state):
    return digest([c for c in state.get('claims', []) if c.get('status') == 'RATE_LIMITED'])


def followup_released(state, ledger):
    return not ledger.get('provider_stop') and any(
        r.get('followup_reference') == followup_reference(state)
        for r in ledger.get('releases', {}).values())


def deadline(stop):
    value = stop.get('retry_after')
    if value is None:
        return None
    try:
        if str(value).isdigit():
            observed = stop.get('observed_at') or stop.get('received_at')
            if not observed:
                raise ValueError('Retry-After lacks observed receipt anchor')
            from .research_watchlist import timestamp
            return timestamp(observed) + timedelta(seconds=int(value))
        result = parsedate_to_datetime(str(value))
        if result.tzinfo is None:
            raise ValueError('Naive Retry-After')
        return result
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError('Unusable Retry-After deadline; manual evidence repair required') from exc


def recovery(path, coordinator, args):
    safe_paths(path, path.with_suffix('.lock'), path.parent/'followup-state.json',
               path.parent/'followup-state.lock')
    if not path.exists():
        if args.command == 'release-rate-limit':
            raise ValueError('No retained stop')
        return dict(status='NO_LEDGER', requests=0)
    with coordinator.run_lock(path.with_suffix('.lock')):
        with coordinator.run_lock(path.parent/'followup-state.lock'):
            ledger = coordinator.load_state(path)
            validate(ledger)
            if 'runs' not in ledger:
                raise ValueError('Explicit legacy migration required')
            follow = coordinator.load_state(path.parent/'followup-state.json')
            follow_ref = followup_reference(follow) if follow.get('rate_limited') else None
            stop = ledger.get('provider_stop')
            ref = digest(dict(stop=stop, followup_reference=follow_ref))
            if args.command == 'recovery-status':
                return dict(status='BLOCKED' if stop else 'NO_STOP', requests=0,
                    stop=stop, receipt_reference=ref, allowed_after=deadline(stop).isoformat() if stop and deadline(stop) else None,
                    quota_available='UNKNOWN')
            import re
            if (not args.release_id or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',args.release_id)
                    or not args.run_id or not args.receipt_reference or not args.reason
                    or not args.reason.strip() or len(args.reason)>2000
                    or args.operator_decision != 'allow-new-cycle' or args.now):
                raise ValueError('Explicit run/receipt/release ID, reason and operator decision required; no caller clock')
            intent = dict(run_id=args.run_id,receipt_reference=args.receipt_reference,
                          reason=args.reason,operator_decision=args.operator_decision)
            releases = ledger.setdefault('releases', {})
            if args.release_id in releases:
                if releases[args.release_id]['intent'] != intent:
                    raise ValueError('Release ID conflict')
                return dict(status='RELEASE_REPLAY',requests=0,quota_available='UNKNOWN')
            if not stop or stop.get('run_id') != args.run_id or ref != args.receipt_reference:
                raise ValueError('Stop receipt conflict')
            now = datetime.now(timezone.utc)
            allowed = deadline(stop)
            for claim in follow.get('claims', []):
                if claim.get('status') == 'RATE_LIMITED':
                    claim_deadline = deadline(claim)
                    if claim_deadline and (allowed is None or claim_deadline > allowed):
                        allowed = claim_deadline
            if allowed and now < allowed:
                raise ValueError('Retry-After deadline not elapsed')
            releases[args.release_id] = dict(intent=intent, stop=stop, observed_at=now.isoformat(),
                allowed_after=allowed.isoformat() if allowed else None, followup_reference=follow_ref,
                quota_available='UNKNOWN', authenticated_authority=False)
            ledger.pop('provider_stop')
            coordinator.save_state(path,ledger)
            return dict(status='RELEASED',requests=0,quota_available='UNKNOWN',execution_authorized=False)


def migrate(path, coordinator):
    safe_paths(path, path.with_suffix('.lock'))
    if not path.exists():
        return dict(status='NO_LEGACY_LEDGER', requests=0)
    with coordinator.run_lock(path.with_suffix('.lock')):
        raw = path.read_bytes()
        ledger = coordinator.load_state(path)
        validate(ledger)
        if 'runs' in ledger:
            return dict(status='ALREADY_MIGRATED' if 'legacy' in ledger else 'NO_LEGACY_LEDGER', requests=0)
        if not ledger:
            raise ValueError('Incompatible empty ledger')
        sha = hashlib.sha256(raw).hexdigest()
        run_id = 'legacy:' + sha
        original = dict(ledger)
        ledger.clear()
        ledger.update(runs={run_id: original}, legacy=dict(run_id=run_id, sha256=sha,
            original_base64=base64.b64encode(raw).decode()), provider_stop=dict(
                status='LEGACY_REVIEW_REQUIRED', run_id=run_id, retry_after=original.get('retry_after'),
                observed_at=datetime.now(timezone.utc).isoformat()))
        coordinator.save_state(path, ledger)
        return dict(status='MIGRATED', requests=0, run_id=run_id)
