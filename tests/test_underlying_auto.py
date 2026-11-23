"""Finviz-only policy through public callers; no provider requests."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from plugins.analyst_trader import realdata_cli as cli, research_watchlist as rw

class CboeCycle(unittest.TestCase):
    def test_oversized_ledger_preserved_without_send(self):
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); db,args=AutomaticDaily().setup_case(root)
            args[args.index('--uw-live')]='--cboe-live'
            path=db.parent/'cboe-cycle-state.json'
            raw=b' '*(8*1024*1024+1); path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'CBOE ledger exceeds'):
                cli.research_main([*args,'--run-id','one'],process_factory=lambda *a,**k:self.fail('send'))
            self.assertEqual(path.read_bytes(),raw)

    def test_rate_limit_recovery_and_archive_before_admission(self):
        import base64
        from email.utils import format_datetime
        for kind in ('429','expired429','unknown429','archive','failure','stale','403','zero'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
                root=Path(tmp); db,args=AutomaticDaily().setup_case(root)
                args[args.index('--uw-live')]='--cboe-live'
                sent=[]; now=datetime.now(timezone.utc)
                if kind=='stale': now-=timedelta(days=2)
                raw=b'{"symbol":"MSFT","data":[]}'
                class Child:
                    stdin=stdout=None
                    def communicate(self,payload,timeout):
                        sent.append(json.loads(payload)['ticker'])
                        self.returncode=1 if kind=='failure' else 0
                        return json.dumps(dict(status=429 if '429' in kind else 200,provider='CBOE',source='CBOE_HISTORY',evidence_cohort='REAL_DATA_RESEARCH',received_at=now.isoformat(),raw_body=base64.b64encode(raw).decode(),retry_after='0' if kind=='expired429' else None if kind=='unknown429' else format_datetime(now+timedelta(seconds=120),usegmt=True))).encode(),None
                factory=lambda *a,**kw:Child()
                if kind=='zero':
                    args[args.index('--request-budget')+1]='0'
                    result=cli.research_main([*args,'--run-id','zero'],process_factory=factory)
                    self.assertEqual(result['status'],'NO_WORK'); self.assertEqual(sent,[])
                    continue
                if kind=='403':
                    class Rejected(Child):
                        def communicate(self,payload,timeout):
                            body,_=super().communicate(payload,timeout)
                            value=json.loads(body); value['status']=403
                            return json.dumps(value).encode(),None
                    result=cli.research_main([*args,'--run-id','rejected'],process_factory=lambda *a,**kw:Rejected())
                    self.assertEqual(result['status'],'HTTP_REJECTED')
                    self.assertEqual(result['outcomes'][0]['http_status'],403)
                    continue
                if kind=='archive':
                    with patch.object(rw,'store_cboe_capture',side_effect=RuntimeError('simulated archive-before-import interruption')):
                        cli.research_main([*args,'--run-id','one'],process_factory=factory)
                    self.assertEqual(rw.read_watchlist(db)['underlying_snapshot_count'],0)
                    # Recovery must not need a fresh send window or resend.
                    expired=datetime.now(timezone.utc)+timedelta(days=1)
                    class Future(datetime):
                        @classmethod
                        def now(cls,tz=None): return expired
                    with patch('datetime.datetime',Future):
                        recovered=cli.research_main([*args,'--run-id','one','--recover-only'],process_factory=factory)
                    self.assertEqual(recovered['status'],'RECOVERED')
                    self.assertEqual(rw.read_watchlist(db)['underlying_snapshot_count'],1)
                    with patch.object(rw,'store_cboe_capture',side_effect=AssertionError('Admitted receipt replayed')):
                        cli.research_main([*args,'--run-id','one','--recover-only'],process_factory=factory)
                else:
                    cli.research_main([*args,'--run-id','one'],process_factory=factory)
                    cli.research_main([*args,'--run-id','one'],process_factory=factory)
                path=root/'TEST/cboe-cycle-state.json'
                saved=json.loads(path.read_text())
                self.assertEqual(len(saved['runs']['one']['claims']),1)
                self.assertEqual(len(sent),1)
                if kind=='429':
                    self.assertIsNotNone(saved['provider_stop']['resume_after'])
                    cli.research_main([*args,'--run-id','two'],process_factory=factory)
                    self.assertEqual(len(sent),1)
                if kind=='stale':
                    cli.research_main([*args,'--run-id','two'],process_factory=factory)
                    cli.research_main([*args,'--run-id','three'],process_factory=factory)
                    self.assertEqual(sent,['MSFT','SPY','MSFT'])
                if kind in ('expired429','unknown429'):
                    cli.research_main([*args,'--run-id','two'],process_factory=factory)
                    self.assertEqual(len(sent),2 if kind=='expired429' else 1)
                    if kind=='expired429':
                        history=json.loads(path.read_text())['stop_history']
                        self.assertEqual(history[0]['run_id'],'one')
                if kind=='archive':
                    self.assertEqual(saved['runs']['one']['receipts'][0]['evidence_cohort'],'TEST')
                changed=list(args); changed[changed.index('--request-budget')+1]='2'
                with self.assertRaises(ValueError): cli.research_main([*changed,'--run-id','one'],process_factory=factory)

    def test_public_cboe_capture_reader_fairness_and_cache(self):
        import io
        from plugins.analyst_trader import realdata_cboe_worker as worker
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); db,args=AutomaticDaily().setup_case(root)
            args[args.index('--uw-live')]='--cboe-live'
            uw=root/'TEST/uw-cycle-state.json'; uw.write_bytes(b'{"preserve":"UW"}')
            sends=[]
            raw=b'{"symbol":"MSFT","timestamp":"11:00:09","data":[{"date":"2026-09-29","open":10,"high":11,"low":9,"close":10,"volume":100}]}'
            class Response:
                status_code=200; headers={}
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def iter_raw(self,chunk_size): yield raw
            class Client:
                def __init__(self,**kw): assert kw['trust_env'] is False
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def stream(self,method,url,**kw):
                    assert url.startswith('https://cdn-api.cboe.com/')
                    assert '/api/stock/' not in url and 'Authorization' not in kw['headers']
                    sends.append(url); return Response()
            class Child:
                stdin=stdout=None
                def communicate(self,payload,timeout):
                    out=io.StringIO()
                    with patch.object(worker.sys,'stdin',type('Input',(),{'buffer':io.BytesIO(payload)})()),patch.object(worker.sys,'stdout',out),patch('httpx.Client',Client),patch('httpx.HTTPTransport',lambda **kw:None):
                        self.returncode=worker.main()
                    return out.getvalue().encode(),None
            factory=lambda *a,**kw:Child()
            first=cli.research_main([*args,'--run-id','cboe-one'],process_factory=factory)
            self.assertEqual(first['requests'],1)
            view=cli.research_main(['status','--root',str(root),'--cohort','TEST'])['watchlist']
            item=view['underlying_technicals'][0]
            self.assertEqual(item['ticker'],'MSFT')
            self.assertEqual(item['status'],'CAPTURED_UNQUALIFIED')
            self.assertIsNone(item['ema']); self.assertEqual(item['adjustment_status'],'UNKNOWN')
            self.assertEqual(view['snapshot_count'],0)
            self.assertEqual(cli.research_main([*args,'--run-id','cboe-one'],process_factory=factory)['requests'],0)
            cli.research_main([*args,'--run-id','cboe-two'],process_factory=factory)
            self.assertTrue(sends[1].endswith('/SPY.json'))
            # Old-date/symbol-mismatched captures cannot suppress a new authorized attempt.
            cli.research_main([*args,'--run-id','cboe-three'],process_factory=factory)
            self.assertEqual(len(sends),3)
            self.assertEqual(uw.read_bytes(),b'{"preserve":"UW"}')
            with rw.connection(db) as c:
                rows=c.execute('SELECT raw_body FROM snapshots').fetchall()
                self.assertEqual([bytes(r[0]) for r in rows],[raw,raw,raw])

class AutomaticDaily(unittest.TestCase):
    def setup_case(self, root):
        now=datetime.now(timezone.utc)
        source=root/'seed.json'
        source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id=str(i),received_at=now.isoformat(),evidence={'contract_symbol':s},raw={}) for i,s in enumerate(['SPY261016C00700000','SPY261016C00710000','MSFT261016C00500000'])]}))
        db=root/'TEST/watchlist.sqlite'; rw.seed(db,source)
        args=['cycle','--root',str(root),'--cohort','TEST','--authorize-research','--uw-live','--request-budget','1','--stages','underlying','--profile-db',str(source),'--profile-version','TEST','--date','2026-09-29','--window-start',(now-timedelta(seconds=1)).isoformat(),'--window-end',(now+timedelta(seconds=90)).isoformat()]
        return db,args

    def test_public_cycle_blocks_and_preserves_historical_spy(self):
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); db,args=self.setup_case(root)
            raw=b'{"data":[{"date":"2026-09-24","open":"600","high":"602","low":"599","close":"601","volume":100,"market_time":"r"}]}'
            rw.store_underlying_daily(db,'SPY',raw,received_at='2026-09-25T00:00:00Z',end_date='2026-09-24',evidence_cohort='TEST')
            before=rw.read_watchlist(db)
            def forbidden(*a,**kw): raise AssertionError('No process/provider call allowed')
            result=cli.research_main([*args,'--run-id','one'],process_factory=forbidden)
            self.assertEqual(result['requests'],0)
            self.assertEqual(result['sources']['underlying'],'BLOCKED_OHLC_SCHEMA_UNVERIFIED')
            self.assertEqual(cli.research_main([*args,'--run-id','one'],process_factory=forbidden)['requests'],0)
            cli.research_main([*args,'--run-id','two'],process_factory=forbidden)
            after=rw.read_watchlist(db)
            self.assertEqual(after['observations'],before['observations'])
            self.assertEqual(after['underlying_technicals'],before['underlying_technicals'])
            with rw.connection(db) as c: self.assertEqual(c.execute('SELECT raw_body FROM snapshots').fetchone()[0],raw)
            ledger=json.loads((root/'TEST/uw-cycle-state.json').read_text())
            queue=ledger['underlying']
            self.assertEqual(queue['provider'],'FINVIZ_ELITE')
            self.assertEqual(set(queue['tickers']),{'SPY','MSFT'})
            self.assertEqual(queue['tickers']['SPY']['history_status'],'HISTORICAL_OTHER_PROVIDER_ONLY')
            self.assertEqual(queue['tickers']['MSFT']['history_status'],'MISSING')
            self.assertTrue(all(run['attempts']==0 for run in ledger['runs'].values()))
            availability=after['source_availability']['finviz']
            self.assertEqual(availability['role'],'UNDERLYING_TA_AND_QUOTES_ONLY')
            self.assertFalse(availability['live_verified'])
            self.assertEqual(availability['access_status'],'ADAPTER_UNQUALIFIED')

    def test_legacy_queue_is_preserved_without_recovery_or_send(self):
        from plugins.analyst_trader.research_underlying import run
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            db,_=self.setup_case(Path(tmp))
            ledger={'underlying':{'provider':'UW','cohort':'TEST','tickers':{'SPY':{'pending':{'raw_body':'preserve-exactly'}}}}}
            before=json.dumps(ledger)
            result=run(db,ledger=ledger,save=lambda:None,cohort='TEST',end_date='2026-09-29',max_requests=1)
            self.assertEqual(result['status'],'PROVIDER_POLICY_REVIEW_REQUIRED')
            self.assertEqual(json.dumps(ledger),before)

    def test_direct_coordinator_has_no_uw_stock_collection(self):
        spec=importlib.util.spec_from_file_location('policy_coord',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        coord=importlib.util.module_from_spec(spec); spec.loader.exec_module(coord)
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); db,_=self.setup_case(root)
            with patch.object(coord,'load_env',side_effect=AssertionError('No credentials')):
                for cohort in ('TEST','REAL_DATA_RESEARCH'):
                    result=coord.run_research_underlying(root=root,grant=dict(authorized=True,evidence_cohort=cohort),ticker='SPY',end_date='2026-09-29')
                    self.assertEqual(result['status'],'BLOCKED_FINVIZ_ADAPTER_UNQUALIFIED')
                    self.assertEqual(result['requests'],0)
            self.assertFalse((db.parent/'underlying-daily-one-shot').exists())

    def test_underlying_only_does_not_require_uw_credentials(self):
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); db,args=self.setup_case(root)
            args[args.index('TEST')]='REAL_DATA_RESEARCH'
            # Empty REAL root must still report the Finviz blocker, not UW auth.
            with patch.dict(os.environ,{},clear=True):
                result=cli.research_main([*args,'--run-id','real-no-send'])
            self.assertEqual(result['status'],'BLOCKED_FINVIZ_ADAPTER_UNQUALIFIED')
            self.assertEqual(result['requests'],0)
