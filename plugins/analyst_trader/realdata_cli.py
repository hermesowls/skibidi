"""Manual run-once research CLI; never a dashboard authentication mechanism.

python -m plugins.analyst_trader.realdata_cli --authorize-research \
  --profile-db EXPLICIT --profile-version EXACT --research-db SEPARATE \
  (--test-response TEST_ENVELOPE.json | --live-request)

Live mode prompts for a token without reading env/config. Its existence is not
Stage3 approval. No scheduler, sender, monitor, order or HTTP server is wired.
"""
import argparse
import json
from .realdata_research import run_once
from .realdata_store import ResearchStore


def research_main(argv=None, *, process_factory=None):
    """Explicit UW research control; Discord/Skylit remain disconnected."""
    from pathlib import Path
    import importlib.util
    import os
    from . import research_watchlist as rw
    p = argparse.ArgumentParser(description='Bounded UW research controls; no orders or recurring approval implied')
    p.add_argument('command', choices=['status', 'configure-horizons', 'update-request', 'cycle', 'migrate-ledger', 'recovery-status', 'release-rate-limit'])
    p.add_argument('--provider', choices=['uw', 'finviz'], default='uw')
    p.add_argument('--operator')
    p.add_argument('--review-decision', choices=['unknown-quota-reviewed', 'auth-repair-intent-reviewed', 'legacy-evidence-reviewed'])
    p.add_argument('--release-id')
    p.add_argument('--receipt-reference')
    p.add_argument('--reason')
    p.add_argument('--operator-decision', choices=['allow-new-cycle'])
    p.add_argument('--root')
    p.add_argument('--cohort', choices=['TEST', 'REAL_DATA_RESEARCH'], required=True)
    p.add_argument('--authorize-research', action='store_true')
    p.add_argument('--request-budget', type=int, choices=range(0, 3))
    p.add_argument('--version')
    p.add_argument('--minutes', nargs='+', type=int)
    p.add_argument('--metric', choices=['close', 'avg_price'])
    p.add_argument('--received-at')
    p.add_argument('--update-json')
    p.add_argument('--test-response')
    p.add_argument('--profile-db')
    p.add_argument('--profile-version')
    p.add_argument('--test-followup')
    p.add_argument('--date')
    p.add_argument('--now')
    p.add_argument('--context-json')
    p.add_argument('--run-id')
    p.add_argument('--uw-live', action='store_true')
    p.add_argument('--cboe-live', action='store_true')
    p.add_argument('--finviz-live', action='store_true')
    p.add_argument('--recover-only', action='store_true')
    p.add_argument('--stages', nargs='+', choices=['discovery','followup','underlying','quotes'])
    p.add_argument('--window-start')
    p.add_argument('--window-end')
    p.add_argument('--max-rows', type=int, default=20, choices=range(1,101))
    p.add_argument('--timeout', type=float, default=10)

    a = p.parse_args(argv)
    if a.cohort == 'TEST' and not a.root:
        raise ValueError('TEST requires an explicit isolated root')
    root = Path(a.root).expanduser().absolute() if a.root else rw.canonical_root()
    db = root/a.cohort/'watchlist.sqlite'
    sources = dict(discovery='DISCONNECTED', followup='DISCONNECTED', discord='DISCONNECTED', skylit='DISCONNECTED')
    if a.command == 'status':
        return dict(status='AVAILABLE' if db.exists() else 'NOT_INITIALIZED', sources=sources,
                    requests=0, execution_authorized=False,
                    watchlist=rw.read_watchlist(db) if db.exists() else None)
    if not a.authorize_research:
        raise ValueError('Explicit research authorization required')
    def document(path):
        with open(path, 'rb') as f:
            raw = f.read(1048577)
        if len(raw) > 1048576:
            raise ValueError('Input exceeds one MiB bound')
        return json.loads(raw)
    if a.command == 'configure-horizons':
        return rw.configure_outcomes(db, dict(version=a.version, minutes=a.minutes, metric=a.metric),
                                     received_at=a.received_at, evidence_cohort=a.cohort)
    if a.provider == 'finviz':
        if (a.command not in ('recovery-status', 'release-rate-limit', 'migrate-ledger') or not a.root
                or a.uw_live or a.cboe_live or a.finviz_live or a.now):
            raise ValueError('Explicit offline Finviz recovery selection required')
        path=Path(os.environ.get('HERMES_HOME',Path.home()/'.hermes'))/'scripts/flowseeker_unified_ingestion.py'
        spec=importlib.util.spec_from_file_location('finviz_recovery_coordinator',path)
        coordinator=importlib.util.module_from_spec(spec); spec.loader.exec_module(coordinator)
        from .research_finviz import operator_recovery
        return operator_recovery(db.parent/'finviz-cycle-state.json', coordinator, a)
    if a.finviz_live:
        from datetime import datetime, timezone
        import re
        if (a.command != 'cycle' or a.uw_live or a.cboe_live or a.stages != ['quotes'] or not a.root
                or a.test_response or a.test_followup or a.context_json or a.now
                or not a.run_id or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',a.run_id)
                or a.request_budget not in (0,1) or not 0 < a.timeout <= 30):
            raise ValueError('Explicit isolated Elite quote authorization required')
        start,end=rw.timestamp(a.window_start),rw.timestamp(a.window_end)
        if (not a.recover_only and not start <= datetime.now(timezone.utc) <= end) or not 0 < (end-start).total_seconds() <= 300:
            raise ValueError('Current bounded Elite window required')
        if (process_factory is None) != (a.cohort == 'REAL_DATA_RESEARCH'):
            raise ValueError('Elite transport cohort mismatch')
        if not db.exists(): return dict(status='NOT_INITIALIZED',requests=0,execution_authorized=False)
        path=Path(os.environ.get('HERMES_HOME',Path.home()/'.hermes'))/'scripts/flowseeker_unified_ingestion.py'
        spec=importlib.util.spec_from_file_location('finviz_cli_coordinator',path)
        coordinator=importlib.util.module_from_spec(spec); spec.loader.exec_module(coordinator)
        from .research_finviz import cycle
        return cycle(db,args=a,coordinator=coordinator,process_factory=process_factory)
    if a.cboe_live:
        from datetime import datetime, timezone
        import re
        if (a.command != 'cycle' or a.uw_live or a.stages != ['underlying'] or not a.root
                or a.test_response or a.test_followup or a.context_json or a.now
                or not a.run_id or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',a.run_id)
                or a.request_budget is None or not 0 < a.timeout <= 30 or not a.date):
            raise ValueError('Explicit isolated CBOE cycle authorization required')
        datetime.strptime(a.date,'%Y-%m-%d')
        start,end=rw.timestamp(a.window_start),rw.timestamp(a.window_end)
        if (not a.recover_only and not start <= datetime.now(timezone.utc) <= end) or not 0 < (end-start).total_seconds() <= 300:
            raise ValueError('Current bounded CBOE window required')
        if (process_factory is None) != (a.cohort == 'REAL_DATA_RESEARCH'):
            raise ValueError('CBOE transport cohort mismatch')
        if not db.exists():
            return dict(status='NOT_INITIALIZED',requests=0,execution_authorized=False)
        path=Path(os.environ.get('HERMES_HOME',Path.home()/'.hermes'))/'scripts/flowseeker_unified_ingestion.py'
        spec=importlib.util.spec_from_file_location('cboe_cli_coordinator',path)
        coordinator=importlib.util.module_from_spec(spec); spec.loader.exec_module(coordinator)
        from .research_underlying import cboe_cycle
        return cboe_cycle(db,args=a,coordinator=coordinator,process_factory=process_factory)
    if a.command == 'cycle' and a.uw_live:
        if a.test_response or a.test_followup or a.context_json or a.now:
            raise ValueError('Live selection rejects fixtures and caller clocks')
        if a.request_budget == 0:
            return dict(status='SKIPPED_DISCONNECTED', sources=sources, requests=0, execution_authorized=False)
        from datetime import datetime, timezone
        if (not a.root or not a.stages or not a.profile_db or not a.profile_version
                or a.request_budget is None or not 0 < a.timeout <= 30
                or not a.window_start or not a.window_end or not a.date):
            raise ValueError('Explicit root/profile/stages/budget/date/time window required')
        import re
        if not a.run_id or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', a.run_id):
            raise ValueError('Explicit bounded unique run ID required')
        start, end = rw.timestamp(a.window_start), rw.timestamp(a.window_end)
        if not start <= datetime.now(timezone.utc) <= end or not 0 < (end-start).total_seconds() <= 300:
            raise ValueError('Authorization window must be current and at most 300 seconds')
        if (process_factory is None) != (a.cohort == 'REAL_DATA_RESEARCH'):
            raise ValueError('Actual transport boundary/cohort mismatch')
        # No credential files, dotenv loading or prompt. Missing is presence-only.
        if set(a.stages) == {'underlying'} and a.cohort == 'REAL_DATA_RESEARCH':
            sources['underlying'] = 'BLOCKED_OHLC_SCHEMA_UNVERIFIED'
            return dict(status='BLOCKED_FINVIZ_ADAPTER_UNQUALIFIED', sources=sources,
                        requests=0, execution_authorized=False)
        token = 'TEST_BOUNDARY' if process_factory else (os.environ.get('UNUSUAL_WHALES_API_KEY') or os.environ.get('UW_API_KEY'))
        if not token:
            return dict(status='MISSING_CREDENTIAL', credential_present=False, requests=0, execution_authorized=False)
    if a.command == 'cycle' and not a.uw_live:
        count = int(bool(a.test_response)) + int(bool(a.test_followup))
        if a.request_budget is None or a.request_budget != count:
            raise ValueError('Explicit exact fixture request budget required; live adapters DISCONNECTED')
        if (count or a.context_json) and a.cohort != 'TEST':
            raise ValueError('TEST fixture cannot write REAL cohort')
        if a.test_response and not (a.profile_db and a.profile_version):
            raise ValueError('Explicit saved profile and version required')
        if a.test_followup and not (a.date and a.now):
            raise ValueError('Explicit followup date and clock required')
        if not count and not a.context_json:
            return dict(status='SKIPPED_DISCONNECTED', sources=sources, requests=0, execution_authorized=False)
    path = Path(os.environ.get('HERMES_HOME', Path.home()/'.hermes'))/'scripts/flowseeker_unified_ingestion.py'
    spec = importlib.util.spec_from_file_location('research_cli_coordinator', path)
    coordinator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coordinator)
    if a.command == 'migrate-ledger':
        from .research_recovery import migrate
        return migrate(root/a.cohort/'uw-cycle-state.json', coordinator)
    if a.command in ('recovery-status', 'release-rate-limit'):
        from .research_recovery import recovery
        return recovery(root/a.cohort/'uw-cycle-state.json', coordinator, a)
    grant = dict(authorized=True, evidence_cohort=a.cohort)
    if a.command == 'update-request':
        return coordinator.run_research_request_update(root=root, grant=grant, update=document(a.update_json))
    requests = 0
    if a.uw_live:
        from .realdata_transport import BoundedUWTransport, BoundedUWIntradayTransport
        # Root-wide lock and retained run ledger: never reset consumed sends.
        destination = root/a.cohort
        state_path = destination/'uw-cycle-state.json'
        for target in (destination, state_path, state_path.with_suffix('.lock')):
            if any(x.is_symlink() for x in (target,*target.parents)) or (target.is_file() and target.stat().st_nlink != 1):
                raise ValueError('Unsafe cycle destination')
        destination.mkdir(parents=True, exist_ok=True)
        with coordinator.run_lock(state_path.with_suffix('.lock')):
            ledger = coordinator.load_state(state_path)
            from .research_recovery import validate
            validate(ledger)
            if state_path.exists() and not ledger:
                raise ValueError('Incompatible empty ledger')
            # Old one-shot ledgers lack sufficient stop provenance: preserve and
            # fail closed rather than guessing that an earlier 429 has cleared.
            if 'authorization' in ledger and 'runs' not in ledger:
                return dict(status='LEGACY_REVIEW_REQUIRED', requests=0, execution_authorized=False)
            runs = ledger.setdefault('runs', {})
            authorization = dict(root=str(root), cohort=a.cohort,
                profile_db=a.profile_db, profile_version=a.profile_version, stages=a.stages,
                request_budget=a.request_budget, window_start=a.window_start, window_end=a.window_end,
                date=a.date, max_rows=a.max_rows, timeout=a.timeout)
            if a.run_id in runs and runs[a.run_id]['authorization'] != authorization:
                raise ValueError('Run ID parameter conflict')
            replay = a.run_id in runs
            state = runs.setdefault(a.run_id, dict(authorization=authorization, attempts=0, claims=[]))
            def save():
                coordinator.save_state(state_path, ledger)
            save()  # Reserve identity before recovery; interruption consumes it.
            def claim():
                if replay or ledger.get('provider_stop') or state.get('stopped') or state['attempts'] >= a.request_budget or not start <= datetime.now(timezone.utc) <= end:
                    raise ValueError('Consumed, blocked or expired research authorization')
                state['attempts'] += 1
                state['claims'].append(dict(attempt=state['attempts'], status='SEND_OUTCOME_UNKNOWN'))
                state['status'] = 'SEND_OUTCOME_UNKNOWN'
                save()
            def received(response):
                if isinstance(response, dict) and response.get('status') == 429:
                    # A new ID never clears a provider stop. Explicit reviewed
                    # rearm is intentionally separate; no timer-based retries.
                    ledger['provider_stop'] = dict(status='RATE_LIMITED_REVIEW_REQUIRED',
                        run_id=a.run_id, retry_after=response.get('retry_after'),
                        observed_at=datetime.now(timezone.utc).isoformat(), received_at=response.get('received_at'))
                    state['claims'][-1]['status'] = 'RATE_LIMITED'
                    save()
            discovery = BoundedUWTransport(token, process_factory=process_factory, before_send=claim, after_response=received)
            followup = BoundedUWIntradayTransport(token, process_factory=process_factory, before_send=claim, after_response=received)
            from .research_underlying import run as underlying
            discovery_grant = dict(grant, mode='REAL_DATA_RESEARCH', profile_version=a.profile_version)
            followup_grant = dict(grant, source=followup.identity)
            # Prior records/responses always recover before any further send.
            if (destination/'research.sqlite').exists():
                coordinator.run_research_once(root=root, profile_source=a.profile_db, grant=discovery_grant,
                    transport=discovery, recover_only=True)
            if db.exists():
                if 'underlying' in ledger or 'underlying' in a.stages:
                    underlying(db, ledger=ledger, save=save, cohort=a.cohort,
                        end_date=a.date, max_requests=0, timeout=a.timeout)
                recovery = coordinator.run_research_followup(root=root, grant=followup_grant, transport=followup,
                    date=a.date, max_requests=0)
                if recovery['status'] == 'RATE_LIMITED':
                    ledger.setdefault('provider_stop', dict(status='RATE_LIMITED_REVIEW_REQUIRED', run_id=a.run_id))
                    state.update(stopped=True, status='RATE_LIMITED')
                    save()
            if replay or ledger.get('provider_stop') or state['attempts'] or state.get('stopped'):
                return dict(status='RATE_LIMITED' if ledger.get('provider_stop') else state.get('status','CONSUMED'),requests=0,attempts=state['attempts'],execution_authorized=False)
            try:
                # Finviz underlying is blocked pending a qualified adapter.
                # Only whale/options stages can consume UW request claims.
                for stage in dict.fromkeys(a.stages):
                    remaining = a.request_budget-state['attempts']
                    if not remaining or ledger.get('provider_stop'):
                        break
                    if stage == 'discovery':
                        result = coordinator.run_research_once(root=root, profile_source=a.profile_db, grant=discovery_grant,
                            transport=discovery, max_rows=a.max_rows, timeout_seconds=a.timeout)
                    elif stage == 'followup' and db.exists():
                        result = coordinator.run_research_followup(root=root, grant=followup_grant, transport=followup,
                            date=a.date, max_requests=remaining, timeout_seconds=a.timeout)
                    elif stage == 'underlying' and db.exists():
                        result = underlying(db, ledger=ledger, save=save, cohort=a.cohort,
                            end_date=a.date, max_requests=remaining, timeout=a.timeout)
                    else:
                        continue
                    sources[stage] = result['status']
                state['status'] = 'RATE_LIMITED' if ledger.get('provider_stop') else 'CONSUMED'
            except Exception:
                state['status'] = 'FAILED_NO_RETRY'
            finally:
                state['stopped'] = True
                save()
            return dict(status=state['status'], requests=state['attempts'], sources=sources,
                execution_authorized=False, watchlist=rw.read_watchlist(db) if db.exists() else None)
    if a.test_response:
        response = document(a.test_response)
        if response.get('source') != 'TEST_FIXTURE':
            raise ValueError('Declared TEST_FIXTURE required')
        result = coordinator.run_research_once(root=root, profile_source=a.profile_db,
            grant=dict(grant, mode='REAL_DATA_RESEARCH', profile_version=a.profile_version),
            transport=lambda *args, **kwargs: response, now=rw.timestamp(a.now) if a.now else None)
        requests += result['requests']; sources['discovery'] = 'TEST_FIXTURE'
    if a.test_followup:
        response = document(a.test_followup)
        if response.get('source') != 'TEST_FIXTURE' or response.get('evidence_cohort') != 'TEST':
            raise ValueError('Declared TEST followup required')
        response['raw_body'] = json.dumps(response.pop('body')).encode()
        result = coordinator.run_research_followup(root=root, grant=dict(grant, source='TEST_TRANSPORT'),
            transport=lambda *args, **kwargs: response, date=a.date, now=a.now, max_requests=1)
        requests += result['requests']; sources['followup'] = result['status']
    if a.context_json:
        coordinator.run_research_context(root=root, grant=grant, source='discord',
            artifact=a.context_json, received_at=a.received_at)
        sources['discord'] = 'DISCONNECTED_SAVED_TEST_REPLAY'
    return dict(status='TEST_RESEARCH_ONLY', sources=sources, requests=requests,
                execution_authorized=False, watchlist=rw.read_watchlist(db))


def main(argv=None):
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'research':
        return research_main(argv[1:])
    p = argparse.ArgumentParser(description='Explicit bounded research-only run; never trade or publish')
    p.add_argument('--authorize-research', action='store_true', required=True)
    p.add_argument('--profile-db', required=True)
    p.add_argument('--profile-version', required=True)
    p.add_argument('--research-db', required=True)
    p.add_argument('--max-rows', type=int, default=20, choices=range(1, 101))
    p.add_argument('--timeout', type=float, default=10)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--test-response')
    mode.add_argument('--live-request', action='store_true')
    args = p.parse_args(argv)
    if not 0 < args.timeout <= 30:
        raise ValueError('Timeout must be finite 0..30 seconds')
    db = ResearchStore(args.research_db, args.profile_db, args.profile_version)
    if args.test_response:
        with open(args.test_response, 'rb') as f:
            data = f.read(1048577)
        if len(data) > 1048576:
            raise ValueError('TEST envelope exceeds bounds')
        response = json.loads(data)
        if not isinstance(response, dict) or response.get('source') != 'TEST_FIXTURE':
            raise ValueError('Only declared TEST fixture accepted')
        def transport(*a, **kw):
            return response
        cohort = 'TEST'
    else:
        from getpass import getpass
        from .realdata_transport import BoundedUWTransport
        transport = BoundedUWTransport(getpass('UW token (research-only single request): '))
        cohort = 'REAL_DATA_RESEARCH'
    grant = dict(mode='REAL_DATA_RESEARCH', authorized=True,
                 profile_version=args.profile_version, evidence_cohort=cohort)
    return run_once(db, grant, transport=transport, now=None,
                    max_rows=args.max_rows, timeout_seconds=args.timeout)


if __name__ == '__main__':
    result = main()
    print(json.dumps(result, default=str))
