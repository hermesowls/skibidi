import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from plugins.analyst_trader import research_watchlist as watch
from plugins.analyst_trader import realdata_transport as transport

class CboeHistory(unittest.TestCase):
    def test_bounded_public_route_worker_and_rejections(self):
        self.assertTrue(hasattr(transport, 'BoundedCBOEHistoryTransport'), 'Missing bounded CBOE adapter')
        from plugins.analyst_trader import realdata_cboe_worker as worker
        for status in (200, 307, 403, 429):
            with self.subTest(status=status):
                sends=[]; claims=[]; receipts=[]
                raw=b'{"unqualified_raw":true}'
                class Response:
                    status_code=status
                    headers={'retry-after':'120'}
                    def __enter__(self): return self
                    def __exit__(self,*a): pass
                    def iter_raw(self,chunk_size):
                        if status != 200: raise AssertionError('Rejection body must not be read')
                        yield raw
                class Client:
                    def __init__(self,**kw):
                        assert kw['trust_env'] is False
                    def __enter__(self): return self
                    def __exit__(self,*a): pass
                    def stream(self,method,url,**kw):
                        sends.append(url)
                        assert method=='GET'
                        assert url=='https://cdn-api.cboe.com/api/global/delayed_quotes/charts/historical/AAOI.json'
                        assert kw['follow_redirects'] is False
                        assert 'Authorization' not in kw['headers']
                        return Response()
                class Child:
                    stdin=stdout=None
                    def communicate(self,payload,timeout):
                        out=io.StringIO()
                        with patch.object(worker.sys,'stdin',type('Input',(),{'buffer':io.BytesIO(payload)})()),patch.object(worker.sys,'stdout',out),patch('httpx.Client',Client),patch('httpx.HTTPTransport',lambda **kw:None):
                            self.returncode=worker.main()
                        return out.getvalue().encode(),None
                tr=transport.BoundedCBOEHistoryTransport(process_factory=lambda *a,**kw:Child(),before_send=lambda:claims.append(1),after_response=receipts.append)
                result=tr('AAOI',timeout=10)
                self.assertEqual(len(sends),1)
                self.assertEqual(len(claims),1)
                self.assertEqual(len(receipts),1)
                self.assertEqual(result['status'],status)
                self.assertEqual(result['raw_body'],raw if status==200 else b'')
                self.assertEqual(result['source'],'TEST_FIXTURE')
                self.assertEqual(result['provider'],'CBOE')
                self.assertEqual(result['evidence_cohort'],'TEST')
                self.assertEqual(result['qualification'],'UNVERIFIED_SCHEMA_SESSION_ADJUSTMENT')

    def test_http_date_retry_after_preserved(self):
        from plugins.analyst_trader import realdata_cboe_worker as worker
        class Response:
            status_code=429; headers={'retry-after':'Fri, 02 Oct 2026 00:00:00 GMT'}
            def __enter__(self): return self
            def __exit__(self,*a): pass
        class Client:
            def __init__(self,**kw): pass
            def __enter__(self): return self
            def __exit__(self,*a): pass
            def stream(self,*a,**kw): return Response()
        with patch('httpx.Client',Client),patch('httpx.HTTPTransport',lambda **kw:None):
            self.assertEqual(worker.fetch('AAOI',10)['retry_after'],Response.headers['retry-after'])

    def test_invalid_request_never_claims_or_spawns(self):
        def forbidden(*a, **kw):
            raise AssertionError('Invalid request crossed boundary')
        tr=transport.BoundedCBOEHistoryTransport(process_factory=forbidden, before_send=forbidden)
        for ticker, timeout in [('aaoi',10), ('AAOI/../SPY',10), ('AAOI',True), ('AAOI',float('nan')), ('AAOI',31)]:
            with self.subTest(ticker=ticker, timeout=timeout), self.assertRaises(ValueError):
                tr(ticker,timeout=timeout)

    def test_body_bounds_and_rejection_close_failure(self):
        from plugins.analyst_trader import realdata_cboe_worker as worker
        for kind in ('compressed','length','stream','close429'):
            sends=[]
            class Response:
                status_code=429 if kind=='close429' else 200
                headers={'content-encoding':'gzip'} if kind=='compressed' else {'content-length':'1048577'} if kind=='length' else {}
                def __enter__(self): return self
                def __exit__(self,*a):
                    if kind=='close429': raise OSError('close failed')
                def iter_raw(self,chunk_size):
                    if kind=='close429': raise AssertionError('Rejection body read')
                    yield b'x'*1048577
            class Client:
                def __init__(self,**kw): pass
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def stream(self,*a,**kw):
                    sends.append(1)
                    return Response()
            with self.subTest(kind=kind), patch('httpx.Client',Client), patch('httpx.HTTPTransport',lambda **kw:None):
                if kind=='close429':
                    self.assertEqual(worker.fetch('AAOI',10)['status'],429)
                else:
                    with self.assertRaises(ValueError): worker.fetch('AAOI',10)
                self.assertEqual(len(sends),1)

class Daily(unittest.TestCase):
    def test_historical_worker_serialization_and_artifact_replay(self):
        self.assertTrue(hasattr(transport, 'BoundedUWDailyTransport'), 'Missing daily bounded adapter')
        from plugins.analyst_trader import realdata_daily_worker as worker
        spec=importlib.util.spec_from_file_location('daily_coord',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        coord=importlib.util.module_from_spec(spec); spec.loader.exec_module(coord)
        for kind in ('valid','429','compressed','oversized','bad_json','larger'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as td:
                root=Path(td); source=root/'seed.json'
                source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id='TEST',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':'SPY260925C00700000'},raw={})]}))
                db=root/'TEST/watchlist.sqlite'; watch.seed(db,source)
                raw=json.dumps({'data':[dict(date='2026-09-24',open='600',high='602',low='599',close='601',volume=100,market_time=mt) for mt in ('pr','po','r')]}).encode()
                sends=[]
                class Response:
                    status_code=429 if kind=='429' else 200
                    headers={'retry-after':'120'} if kind=='429' else {'content-encoding':'gzip'} if kind=='compressed' else {}
                    def __enter__(self): return self
                    def __exit__(self,*a): pass
                    def iter_raw(self,chunk_size):
                        if kind=='429': raise AssertionError('Error body read')
                        yield b'x'*1048577 if kind=='oversized' else b'bad' if kind=='bad_json' else raw
                class Client:
                    def __init__(self,*a,**kw): pass
                    def __enter__(self): return self
                    def __exit__(self,*a): pass
                    def stream(self,method,url,**kw):
                        sends.append(url)
                        assert method=='GET' and url.endswith('/api/stock/SPY/ohlc/1d')
                        assert kw['params']==dict(timeframe='1Y',end_date='2026-09-24',limit=2500 if kind=='larger' else 500)
                        return Response()
                class Child:
                    stdin=stdout=None
                    def communicate(self,payload,timeout):
                        out=io.StringIO()
                        with patch.object(worker.sys,'stdin',type('Input',(),{'buffer':io.BytesIO(payload)})()),patch.object(worker.sys,'stdout',out),patch.object(worker.sys,'stderr',io.StringIO()),patch('httpx.Client',Client),patch('httpx.HTTPTransport',lambda **kw:None):
                            self.returncode=worker.main()
                        return out.getvalue().encode(),None
                tr=transport.BoundedUWDailyTransport('TEST_SECRET',process_factory=lambda *a,**kw:Child())
                # Historical worker compatibility only, not an authorized collection path.
                if kind in ('compressed','oversized'):
                    with self.assertRaises(ValueError):
                        tr('/api/stock/SPY/ohlc/1d',params=dict(timeframe='1Y',end_date='2026-09-24',limit=500),timeout=30)
                    self.assertEqual(len(sends),1)
                    continue
                first=tr('/api/stock/SPY/ohlc/1d',params=dict(timeframe='1Y',end_date='2026-09-24',limit=2500 if kind=='larger' else 500),timeout=30)
                self.assertEqual(len(sends),1)
                if kind=='bad_json':
                    artifact=root/'invalid.json'; artifact.write_bytes(first['raw_body'])
                    with self.assertRaises(ValueError):
                        coord.run_research_underlying(root=root,grant=dict(authorized=True,evidence_cohort='TEST'),ticker='SPY',end_date='2026-09-24',artifact=artifact,received_at=first['received_at'])
                    self.assertEqual(watch.read_watchlist(db)['underlying_snapshot_count'],0)
                if kind in ('valid','larger'):
                    artifact=root/'historical.json'; artifact.write_bytes(first['raw_body'])
                    coord.run_research_underlying(root=root,grant=dict(authorized=True,evidence_cohort='TEST'),ticker='SPY',end_date='2026-09-24',artifact=artifact,received_at=first['received_at'])
                if kind in ('valid','larger'):
                    with watch.connection(db) as c:
                        row=c.execute('SELECT raw_body FROM snapshots').fetchone()
                    self.assertEqual(row[0],raw)
                    ta=watch.read_watchlist(db)['underlying_technicals'][0]
                    self.assertEqual(ta['underlying_completed_bars'],1)
                    self.assertEqual(ta['excluded_extended_session_bars'],2)
                    self.assertEqual(ta['raw_bars'],3)
                    self.assertEqual(ta['evidence_cohort'],'TEST')
                    self.assertIsNone(ta['ema'])
                if kind=='429': self.assertEqual(first['retry_after'],'120')

    def test_daily_limit_bounds(self):
        from plugins.analyst_trader.realdata_daily_worker import validate_request
        for limit in (500,2500):
            validate_request('/api/stock/SPY/ohlc/1d',dict(timeframe='1Y',end_date='2026-09-24',limit=limit),30)
        for limit in (0,2501,True,'2500',2500.0,1000):
            with self.assertRaises(ValueError):
                validate_request('/api/stock/SPY/ohlc/1d',dict(timeframe='1Y',end_date='2026-09-24',limit=limit),30)
