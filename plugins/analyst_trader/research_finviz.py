"""Private Elite quote snapshots, never candles, option evidence or public export.

Explicit per-run bounded captures share a five-second minimum send interval.
Provider stops survive new IDs; only explicit audited operator recovery releases them.
"""
import base64
import csv
import io
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from . import research_watchlist as rw
from .realdata_transport import BoundedCBOEHistoryTransport
from .realdata_finviz_worker import validate


def store(db, raw, received_at, cohort):
    rw.timestamp(received_at)
    view=rw.read_watchlist(db)
    if view['mode']!=cohort: raise ValueError('Elite cohort mismatch')
    if len(raw)>1048576: raise ValueError('CSV bound exceeded')
    try:
        reader=csv.reader(io.StringIO(raw.decode('utf-8-sig')),strict=True)
        header=next(reader)
        if len(header)!=len(set(header)) or not {'Ticker','Price'}<=set(header): raise ValueError()
        rows={}
        for index,row in enumerate(reader):
            if index>=10000 or len(row)!=len(header): raise ValueError()
            item=dict(zip(header,row)); ticker=item['Ticker']
            if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,9}',ticker) or ticker in rows: raise ValueError()
            try:
                price=float(item['Price'])
                if not math.isfinite(price) or price<=0: price=None
            except ValueError: price=None
            rows[ticker]=price
    except (ValueError,UnicodeError,csv.Error,StopIteration):
        raise ValueError('Invalid Elite CSV') from None
    tickers=sorted({s[:-15] for s in view['contracts']})
    quotes=[dict(ticker=t,price=rows[t],status='AVAILABLE' if rows[t] is not None else 'INVALID_PRICE') for t in tickers if t in rows]
    sid=rw.digest((rw.digest(raw)+received_at+cohort).encode())
    summary=dict(id=sid,provider='FINVIZ_ELITE',evidence_cohort=cohort,received_at=received_at,
        provider_observed_at=None,delay_status='UNKNOWN',live_verified=False,market_session='UNKNOWN',
        quotes=quotes,missing_tickers=[t for t in tickers if t not in rows],missing_reason='WATCHLIST_TICKER_ABSENT_FROM_FILTERED_EXPORT',
        raw_rows=len(rows),raw_hash=rw.digest(raw),license='PRIVATE_PERSONAL_ONLY',status='CAPTURED_QUOTES')
    with rw.connection(db,write=True) as c:
        c.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?,?,?)',
            (sid,None,received_at,'research-quotes/finviz',rw.digest(raw),raw,json.dumps(summary,allow_nan=False)))
    return summary


def operator_recovery(path, coordinator, args):
    """Audited offline intent only; never repair credentials or send requests."""
    from .research_recovery import safe_paths, digest, deadline
    safe_paths(path, path.with_suffix('.lock'))
    result = dict(requests=0, execution_authorized=False, quota_available='UNKNOWN', authenticated_authority=False)
    with coordinator.run_lock(path.with_suffix('.lock')):
        if not path.exists(): return dict(result, status='NO_LEDGER')
        with path.open('rb') as f: raw=f.read(1500001)
        if len(raw)>1500000: return dict(result, status='CAPACITY_HOLD')
        def unique_object(pairs):
            value={}
            for key,item in pairs:
                if key in value: raise ValueError('Ambiguous duplicate ledger key')
                value[key]=item
            return value
        try:
            state=json.loads(raw,object_pairs_hook=unique_object)
            if not isinstance(state,dict) or state.get('cohort')!=args.cohort: raise ValueError()
            if 'runs' in state and not isinstance(state['runs'],dict): raise ValueError()
            if 'operations' in state and not isinstance(state['operations'],dict): raise ValueError()
            legacy='runs' not in state
            if legacy:
                original_raw=base64.b64decode(state['legacy']['original_base64'],validate=True) if 'legacy' in state else raw
                if 'legacy' in state and rw.digest(original_raw)!=state['legacy']['sha256']: raise ValueError()
                original=json.loads(original_raw,object_pairs_hook=unique_object)
                if state.get('provider_stop') or original.get('cohort')!=args.cohort: raise ValueError()
                receipt=state.get('receipt')
                if (not isinstance(receipt,dict) or type(receipt.get('status')) is not int
                        or not 100<=receipt['status']<=599): raise ValueError()
                rw.timestamp(receipt['received_at'])
                base64.b64decode(receipt['raw_body'],validate=True)
                if original.get('receipt')!=receipt: raise ValueError()
                run_id='legacy:'+rw.digest(original_raw)
                stop=dict(status='LEGACY_REVIEW_REQUIRED',run_id=run_id,receipt_reference=digest(receipt),
                    http_status=receipt['status'],retry_after=receipt.get('retry_after'),received_at=receipt['received_at'])
            else:
                stop=state.get('provider_stop')
                if stop:
                    run=state['runs'][stop['run_id']]
                    receipt=run.get('receipt')
                    if receipt:
                        if stop.get('receipt_reference')!=digest(receipt): raise ValueError()
                        if any(stop.get(a)!=receipt.get(b) for a,b in
                               (('http_status','status'),('retry_after','retry_after'),('received_at','received_at'))):
                            raise ValueError()
                    if not receipt and stop.get('status')!='SEND_OUTCOME_UNKNOWN': raise ValueError()
            allowed=deadline(stop) if stop else None
        except (ValueError,KeyError,TypeError,AttributeError):
            return dict(result,status='EVIDENCE_HOLD')
        ref=digest(dict(stop=stop,legacy_sha256=rw.digest(raw) if legacy else None))
        if args.command=='recovery-status':
            return dict(result,status='LEGACY_REVIEW_REQUIRED' if legacy else 'BLOCKED' if stop else 'NO_STOP',
                stop=stop,receipt_reference=ref,allowed_after=allowed.isoformat() if allowed else None)
        for value in (args.release_id,args.run_id):
            if not value or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',value):
                raise ValueError('Explicit operation and run ID required')
        if (not args.operator or not args.operator.strip() or len(args.operator)>200
                or not args.reason or not args.reason.strip() or len(args.reason)>2000
                or not args.receipt_reference or args.operator_decision!='allow-new-cycle'):
            raise ValueError('Explicit operator/reason/receipt and decision required')
        intent={k:getattr(args,k) for k in ('command','cohort','run_id','receipt_reference','operator','reason','operator_decision','review_decision')}
        operations=state.get('operations',{})
        if args.release_id in operations:
            if operations[args.release_id]['intent']!=intent: raise ValueError('Operation ID conflict')
            return dict(result,status='RELEASE_REPLAY' if args.command=='release-rate-limit' else 'MIGRATION_REPLAY')
        if len(operations)>=128: return dict(result,status='CAPACITY_HOLD')
        if not stop or stop['run_id']!=args.run_id or ref!=args.receipt_reference: raise ValueError('Stop receipt conflict')
        if args.command=='migrate-ledger':
            if not legacy: raise ValueError('Not a legacy ledger')
            if args.review_decision!='legacy-evidence-reviewed': raise ValueError('Explicit legacy evidence review required')
            # Preserve exact original bytes plus the full current one-shot ledger.
            state=dict(cohort=args.cohort,runs={run_id:state},legacy=dict(run_id=run_id,
                sha256=rw.digest(original_raw),original_base64=base64.b64encode(original_raw).decode()),
                provider_stop=stop,operations=operations,last_send_at=receipt['received_at'])
            status='MIGRATED'
        else:
            if legacy: raise ValueError('Explicit legacy migration required')
            if stop.get('status')=='QUARANTINED': return dict(result,status='EVIDENCE_HOLD')
            if allowed and datetime.now(timezone.utc)<allowed: raise ValueError('Retry-After deadline not elapsed')
            required=('auth-repair-intent-reviewed' if stop.get('http_status') in (401,403)
                      else 'legacy-evidence-reviewed' if stop.get('status')=='LEGACY_REVIEW_REQUIRED'
                      else 'unknown-quota-reviewed' if allowed is None else None)
            if required and args.review_decision!=required: raise ValueError('Explicit review decision required: '+required)
            state.pop('provider_stop'); status='RELEASED'
        operations[args.release_id]=dict(intent=intent,stop=stop,observed_at=datetime.now(timezone.utc).isoformat(),
            allowed_after=allowed.isoformat() if allowed else None,authenticated_authority=False,quota_available='UNKNOWN')
        state['operations']=operations
        if len(json.dumps(state,indent=2).encode())>1500000: return dict(result,status='CAPACITY_HOLD')
        coordinator.save_state(path,state)
        return dict(result,status=status,run_id=args.run_id)


def cycle(db, *, args, coordinator, process_factory=None):
    path=Path(db).parent/'finviz-cycle-state.json'
    for target in (path,path.with_suffix('.lock')):
        if any(p.is_symlink() for p in (target,*target.parents)) or (target.exists() and target.stat().st_nlink!=1):
            raise ValueError('Unsafe Elite state target')
    with coordinator.run_lock(path.with_suffix('.lock')):
        if rw.read_watchlist(db)['mode']!=args.cohort: raise ValueError('Elite cohort mismatch')
        state={}
        if path.exists():
            with path.open('rb') as f: raw=f.read(1500001)
            if len(raw)>1500000: raise ValueError('Elite ledger exceeds bound')
            state=json.loads(raw)
            if state.get('cohort')!=args.cohort: raise ValueError('Elite ledger cohort mismatch')
            if 'runs' not in state and 'legacy' not in state:
                # Same evidence-preserving pattern as research_recovery.migrate;
                # no consumed legacy claim is reset and no rearm is implied.
                state['legacy']=dict(sha256=rw.digest(raw),original_base64=base64.b64encode(raw).decode())
        def save(): coordinator.save_state(path,state)
        authorization={k:getattr(args,k) for k in ('cohort','request_budget','window_start','window_end','timeout','stages','date')}
        authorization['root']=str(Path(db).parent)
        prior=state.get('runs',{}).get(args.run_id)
        if prior and prior['authorization']!=authorization:
            raise ValueError('Run ID parameter conflict')
        recovered=0
        def recover(item):
            nonlocal recovered
            receipt=item['receipt']
            try:
                summary=store(db,base64.b64decode(receipt['raw_body'],validate=True),receipt['received_at'],args.cohort)
            except (ValueError,KeyError,TypeError):
                item['status']='QUARANTINED'
                state['provider_stop']=dict(provider='FINVIZ_ELITE',status='QUARANTINED',receipt_reference=rw.digest(json.dumps(receipt,sort_keys=True).encode()))
                save()
                return False
            item['admitted']=summary['id']; state['admitted']=summary['id']; recovered+=1; save()
            return True
        for item in state.get('runs',{}).values() if 'runs' in state else [state]:
            if item.get('receipt',{}).get('status')==200 and not item.get('admitted') and item.get('status')!='QUARANTINED':
                try:
                    recover(item)
                except Exception:
                    return dict(status='ADMISSION_PENDING',requests=0,execution_authorized=False)
        if state.get('provider_stop',{}).get('status')=='QUARANTINED':
            return dict(status='QUARANTINED',requests=0,execution_authorized=False)
        if args.recover_only:
            held=state.get('provider_stop') or (state.get('receipt') and not state.get('admitted'))
            return dict(status='RECOVERED' if recovered else 'HELD' if held else 'NO_PENDING_RECOVERY',requests=0,execution_authorized=False)
        # Existing one-shot receipts are preserved verbatim and cannot rearm.
        if state and 'runs' not in state:
            return dict(status='LEGACY_REVIEW_REQUIRED',requests=0,execution_authorized=False)
        from .research_recovery import digest
        runs=state.setdefault('runs',{})
        state['cohort']=args.cohort
        if args.run_id in runs:
            return dict(status=runs[args.run_id].get('status','CONSUMED'),requests=0,execution_authorized=False)
        if state.get('provider_stop'):
            return dict(status='CONSUMED_REVIEW_REQUIRED',requests=0,execution_authorized=False,release_status='BLOCKED_REQUIRES_REVIEWED_FINVIZ_RECOVERY')
        if len(runs)>=64:
            return dict(status='LEDGER_CAPACITY_HOLD',requests=0,execution_authorized=False)
        run=runs.setdefault(args.run_id,dict(authorization=authorization,attempts=0,claims=[]))
        save()
        if state.get('last_send_at') and (datetime.now(timezone.utc)-rw.timestamp(state['last_send_at'])).total_seconds()<5:
            run['status']='CACHED_QUOTES' if state.get('admitted') else 'MINIMUM_SPACING_HOLD'; save()
            return dict(status=run['status'],requests=0,execution_authorized=False,cache_freshness='UNKNOWN')
        if not args.request_budget: return dict(status='NO_WORK',requests=0,execution_authorized=False)
        url=os.environ.get('FINVIZ_API_URL')
        if not url: return dict(status='MISSING_CONFIGURATION',requests=0,execution_authorized=False)
        validate(url,args.timeout)
        def claim():
            if not rw.timestamp(args.window_start)<=datetime.now(timezone.utc)<=rw.timestamp(args.window_end):
                raise ValueError('Elite authorization expired')
            run.update(attempts=1,status='SEND_OUTCOME_UNKNOWN')
            run['claims'].append(dict(status='SEND_OUTCOME_UNKNOWN'))
            state['last_send_at']=datetime.now(timezone.utc).isoformat()
            state['provider_stop']=dict(provider='FINVIZ_ELITE',status='SEND_OUTCOME_UNKNOWN',run_id=args.run_id)
            save()
        def received(result):
            # Retain immutable per-run receipts; never persist configured URL.
            receipt={k:result[k] for k in ('status','received_at','raw_body')}
            receipt['retry_after']=result.get('retry_after')
            run['receipt']=receipt
            if result['status']==200:
                state.pop('provider_stop',None)
            else:
                state['provider_stop']=dict(provider='FINVIZ_ELITE',status='HTTP_REJECTED_REVIEW_REQUIRED',run_id=args.run_id,http_status=result['status'],retry_after=receipt['retry_after'],received_at=receipt['received_at'],receipt_reference=digest(receipt))
            save()
        transport=BoundedCBOEHistoryTransport(process_factory=process_factory,before_send=claim,after_response=received)
        try:
            result=transport._execute(json.dumps(dict(url=url,timeout=args.timeout)).encode(),args.timeout,'realdata_finviz_worker.py')
            if result['status']==200:
                status='CAPTURED_QUOTES' if recover(run) else 'QUARANTINED'
            else: status='HTTP_REJECTED_REVIEW_REQUIRED'
        except Exception:
            status='FAILED_NO_RETRY'
        run['status']=status; save()
        return dict(status=status,requests=run['attempts'],execution_authorized=False)
