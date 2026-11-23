"""Watchlist underlying capture queue and retained legacy Finviz blocker.

CBOE capture is explicit and provider-isolated. Unknown regular-session and
adjustment semantics prevent TA admission; no UW stock fallback is available.
"""
from . import research_watchlist as rw


def cboe_cycle(db, *, args, coordinator, process_factory=None):
    """Provider-isolated fair capture queue; cached captures are NOT qualified TA."""
    import base64
    from datetime import datetime, timezone, timedelta
    from pathlib import Path
    from .realdata_transport import BoundedCBOEHistoryTransport
    path=Path(db).parent/'cboe-cycle-state.json'
    for target in (path,path.with_suffix('.lock')):
        if any(x.is_symlink() for x in (target,*target.parents)) or (target.exists() and target.stat().st_nlink!=1):
            raise ValueError('Unsafe CBOE state target')
    with coordinator.run_lock(path.with_suffix('.lock')):
        import json
        if path.exists():
            with path.open('rb') as handle: raw=handle.read(8*1024*1024+1)
            if len(raw)>8*1024*1024: raise ValueError('CBOE ledger exceeds eight MiB; retained for review')
            ledger=json.loads(raw)
        else: ledger={}
        binding=dict(provider='CBOE',cohort=args.cohort,version=1)
        if ledger and ledger.get('binding')!=binding:
            raise ValueError('CBOE ledger binding mismatch')
        ledger.setdefault('binding',binding)
        runs=ledger.setdefault('runs',{})
        items=ledger.setdefault('tickers',{})
        authorization=dict(date=args.date,budget=args.request_budget,timeout=args.timeout,
                           start=args.window_start,end=args.window_end)
        if args.run_id in runs and runs[args.run_id]['authorization']!=authorization:
            raise ValueError('Run ID parameter conflict')
        replay=args.run_id in runs
        if getattr(args,'recover_only',False) and not replay:
            raise ValueError('Recovery requires an existing bound run')
        # Retain every claim/receipt; capacity exhaustion is not permission to prune.
        if not replay and (len(runs)>=128 or len(json.dumps(ledger).encode())>4*1024*1024):
            return dict(status='CBOE_LEDGER_CAPACITY_REVIEW_REQUIRED',requests=0,execution_authorized=False)
        state=runs.setdefault(args.run_id,dict(authorization=authorization,claims=[],receipts=[]))
        def save(): coordinator.save_state(path,ledger)
        save()
        view=rw.read_watchlist(db)
        if view['mode']!=args.cohort: raise ValueError('CBOE cohort mismatch')
        # Recover raw responses before any send; snapshot identity is idempotent.
        recovered=0
        for prior in runs.values():
            for receipt in prior['receipts']:
                if receipt['status']==200 and not receipt.get('admitted_snapshot_id'):
                    if recovered>=2:
                        return dict(status='RECOVERY_PENDING',requests=0,execution_authorized=False)
                    if not isinstance(receipt.get('raw_body'),str) or len(receipt['raw_body'])>1398104:
                        raise ValueError('Oversized saved CBOE receipt')
                    summary=rw.store_cboe_capture(db,receipt['ticker'],base64.b64decode(receipt['raw_body'],validate=True),
                        received_at=receipt['received_at'],end_date=receipt['end_date'],evidence_cohort=args.cohort)
                    items[receipt['ticker']]=dict(received_at=receipt['received_at'],end_date=receipt['end_date'],
                        snapshot_id=summary['id'],status=summary['status'],summary=summary,cache_status='CAPTURE_ONLY_NOT_QUALIFIED_TA')
                    receipt['admitted_snapshot_id']=summary['id']; recovered+=1; save()
        save()
        if getattr(args,'recover_only',False):
            return dict(status='RECOVERED',requests=0,execution_authorized=False)
        now=datetime.now(timezone.utc)
        stop=ledger.get('provider_stop')
        if stop and (not stop.get('resume_after') or now < rw.timestamp(stop['resume_after'])):
            return dict(status='CBOE_RATE_LIMITED',requests=0,execution_authorized=False)
        if replay:
            return dict(status='CONSUMED',requests=0,execution_authorized=False)
        if stop:
            ledger.setdefault('stop_history',[]).append(stop)
            del ledger['provider_stop']; save()
        tickers=sorted({s[:-15] for s in view['contracts']})
        cursor=ledger.get('cursor','')
        order=[t for t in tickers if t>cursor]+[t for t in tickers if t<=cursor]
        from .session_calendar import calendar, check_coverage
        check_coverage(now)
        schedule=calendar().schedule
        completed=schedule[schedule['close'] <= now]
        expected=completed.index[-1].strftime('%Y-%m-%d') if len(completed) else None
        outcomes=[]
        cached_count=0
        for ticker in order:
            if len(state['claims'])>=args.request_budget: break
            cached=items.get(ticker,{})
            age=(now-rw.timestamp(cached['received_at'])).total_seconds() if cached.get('received_at') else None
            summary=cached.get('summary',{})
            defects={'SYMBOL_MISMATCH_OR_MISSING','MALFORMED_OR_UNSUPPORTED_SCHEMA','INVALID_OHLCV_ROWS','DUPLICATE_DATES'}
            if (expected is not None and summary.get('last_date')==expected and cached.get('end_date')==args.date
                    and age is not None and 0<=age<86400 and summary.get('raw_bars',0)>0
                    and not defects.intersection(summary.get('reason','').split(';'))):
                cached_count+=1
                continue
            def claim():
                clock=datetime.now(timezone.utc)
                if not rw.timestamp(args.window_start)<=clock<=rw.timestamp(args.window_end):
                    raise ValueError('Expired CBOE authorization')
                state['claims'].append(dict(ticker=ticker,claimed_at=clock.isoformat(),status='SEND_OUTCOME_UNKNOWN'))
                ledger['cursor']=ticker; save()
            def received(response):
                receipt=dict(response,ticker=ticker,end_date=args.date)
                if process_factory is not None:
                    receipt.update(source='TEST_FIXTURE',evidence_cohort='TEST')
                state['receipts'].append(receipt)
                if response.get('status')==429:
                    retry=response.get('retry_after')
                    seconds=int(retry) if isinstance(retry,str) and retry.isdecimal() and len(retry)<=10 else None
                    anchor=rw.timestamp(response['received_at'])
                    resume=(anchor+timedelta(seconds=seconds)).isoformat() if seconds is not None else None
                    if seconds is None and isinstance(retry,str) and len(retry)<=64:
                        from email.utils import parsedate_to_datetime
                        try:
                            parsed=parsedate_to_datetime(retry)
                            if parsed.tzinfo is not None: resume=parsed.isoformat()
                        except (ValueError,TypeError,OverflowError): pass
                    ledger['provider_stop']=dict(run_id=args.run_id,received_at=response['received_at'],retry_after=retry,
                        resume_after=resume)
                save()
            transport=BoundedCBOEHistoryTransport(process_factory=process_factory,before_send=claim,after_response=received)
            try:
                response=transport(ticker,timeout=args.timeout)
                outcomes.append(dict(ticker=ticker,http_status=response['status'],status='CAPTURED_UNQUALIFIED' if response['status']==200 else 'HTTP_REJECTED'))
                if response['status']==200:
                    summary=rw.store_cboe_capture(db,ticker,response['raw_body'],received_at=response['received_at'],
                        end_date=args.date,evidence_cohort=args.cohort)
                    items[ticker]=dict(received_at=response['received_at'],end_date=args.date,snapshot_id=summary['id'],
                        status=summary['status'],summary=summary,cache_status='CAPTURE_ONLY_NOT_QUALIFIED_TA')
                    state['receipts'][-1]['admitted_snapshot_id']=summary['id']
                save()
            except Exception:
                state['failure']='FAILED_NO_RETRY'; save(); break
            if ledger.get('provider_stop'): break
        status='HTTP_REJECTED' if any(o['status']=='HTTP_REJECTED' for o in outcomes) else 'CAPTURED_UNQUALIFIED' if outcomes else 'CACHED_UNQUALIFIED' if cached_count else 'NO_WORK'
        return dict(status='CBOE_RATE_LIMITED' if ledger.get('provider_stop') else state.get('failure',status),
            outcomes=outcomes,requests=len(state['claims']),provider='CBOE',execution_authorized=False,watchlist=rw.read_watchlist(db))


def run(db, *, ledger, save, cohort, end_date, max_requests, timeout=10):
    view = rw.read_watchlist(db)
    if view['mode'] != cohort:
        raise ValueError('Daily watchlist cohort mismatch')
    binding = dict(provider='FINVIZ_ELITE', cohort=cohort, timeframe='1d',
                   policy='FINVIZ_UNDERLYING_ONLY_NO_UW_FALLBACK')
    queue = ledger.setdefault('underlying', dict(binding, cursor=0, tickers={}))
    if any(queue.get(k) != v for k,v in binding.items()):
        # Preserve old attempts/raw bytes without interpreting them as permission.
        return dict(status='PROVIDER_POLICY_REVIEW_REQUIRED', requests=0)
    for ticker in sorted({s[:-15] for s in view['contracts']}):
        item = queue['tickers'].setdefault(ticker, dict(status='QUEUED', last_attempt=0))
        histories = [s for s in view['underlying_technicals'] if s['ticker']==ticker]
        item.update(provider='FINVIZ_ELITE', requested_end_date=end_date,
            history_status='HISTORICAL_OTHER_PROVIDER_ONLY' if histories else 'MISSING',
            acquisition_status='BLOCKED_OHLC_SCHEMA_UNVERIFIED',
            provider_observed_at=None, received_at=None, delay_status='UNKNOWN',
            market_session='UNKNOWN', stale_status='UNAVAILABLE', cache_status='NO_QUALIFIED_FINVIZ_HISTORY',
            quote_status='UNAVAILABLE', attempt_budget=max_requests,
            baseline_rejection=False)
    save()
    return dict(status='BLOCKED_OHLC_SCHEMA_UNVERIFIED', provider='FINVIZ_ELITE',
        requests=0, queued=len(queue['tickers']), execution_authorized=False)
