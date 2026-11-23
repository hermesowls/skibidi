"""TEST-only Elite HTTP boundary through the public research CLI."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_underlying_auto import AutomaticDaily
from plugins.analyst_trader import realdata_cli as cli

class FinvizQuotes(unittest.TestCase):
    def test_invalid_prices_bad_csv_and_recovery(self):
        from plugins.analyst_trader import research_finviz as fv
        for price in ('NaN','inf','0','-1','-',''):
            with self.subTest(price=price),tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
                db,args=AutomaticDaily().setup_case(Path(tmp))
                item=fv.store(db,('Ticker,Price\nSPY,'+price+'\n').encode(),'2026-10-01T12:00:00Z','TEST')
                self.assertIsNone(item['quotes'][0]['price'])
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); db,args=AutomaticDaily().setup_case(root)
            for raw in (b'Ticker,Other\nSPY,1\n',b'Ticker,Price\n"SPY,1',b'Ticker,Price\nSPY,1,2\n',b'Ticker,Price\nSPY,1\nSPY,2\n'):
                with self.assertRaisesRegex(ValueError,'Invalid Elite CSV'): fv.store(db,raw,'2026-10-01T12:00:00Z','TEST')
            import base64
            args[args.index('--uw-live')]='--finviz-live'; args[args.index('underlying')]='quotes'
            path=db.parent/'finviz-cycle-state.json'
            path.write_text(json.dumps(dict(cohort='TEST',receipt=dict(status=200,received_at='2026-10-01T12:00:00Z',raw_body=base64.b64encode(b'Ticker,Price\nSPY,123\n').decode()))))
            result=cli.research_main([*args,'--run-id','recover','--recover-only'],process_factory=lambda *a,**k:self.fail('send'))
            self.assertEqual(result['status'],'RECOVERED')
            self.assertIn('admitted',json.loads(path.read_text()))

    def test_http_auth_429_redirect_no_retry_or_error_leak(self):
        from plugins.analyst_trader import realdata_finviz_worker as worker
        for status in (401,403,429,307):
            sent=[]
            class Response:
                status_code=status
                def __enter__(self): return self
                def __exit__(self,*a): raise RuntimeError('TEST_SECRET')
                def iter_raw(self,**kw): self.fail('body must not be read')
            class Client:
                def __init__(self,**kw): pass
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def stream(self,*a,**kw): sent.append(1); return Response()
            with patch('httpx.Client',Client),patch('httpx.HTTPTransport',lambda **kw:None):
                result=worker.fetch('https://elite.finviz.com/export/screener?auth=TEST_SECRET',1)
            self.assertEqual(result['status'],status); self.assertEqual(sent,[1])
            self.assertNotIn('TEST_SECRET',json.dumps(result))
        with self.assertRaisesRegex(ValueError,'Invalid bounded Elite configuration'):
            worker.validate('https://elite.finviz.com.evil/export/screener?auth=TEST_SECRET',1)

    def test_public_quote_cache_and_missing(self):
        from plugins.analyst_trader import realdata_finviz_worker as worker
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); db,args=AutomaticDaily().setup_case(root)
            args[args.index('--uw-live')]='--finviz-live'
            args[args.index('underlying')]='quotes'
            sends=[]
            class Response:
                status_code=200; headers={'content-type':'text/csv'}
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def iter_raw(self,chunk_size): yield b'Ticker,Company,Price\nSPY,TEST,123.45\n'
            class Client:
                def __init__(self,**kw): assert kw['trust_env'] is False
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def stream(self,method,url,**kw):
                    assert url=='https://elite.finviz.com/export/screener?auth=TEST_SECRET&f=TEST'
                    assert kw['follow_redirects'] is False
                    sends.append(1); return Response()
            class Child:
                stdin=stdout=None
                def communicate(self,payload,timeout):
                    out=io.StringIO()
                    with patch.object(worker.sys,'stdin',type('Input',(),{'buffer':io.BytesIO(payload)})()),patch.object(worker.sys,'stdout',out),patch('httpx.Client',Client),patch('httpx.HTTPTransport',lambda **kw:None):
                        self.returncode=worker.main()
                    return out.getvalue().encode(),None
            with patch.dict(os.environ,FINVIZ_API_URL='https://elite.finviz.com/export/screener?auth=TEST_SECRET&f=TEST'):
                first=cli.research_main([*args,'--run-id','one'],process_factory=lambda *a,**kw:Child())
                second=cli.research_main([*args,'--run-id','two'],process_factory=lambda *a,**kw:Child())
            self.assertEqual(first['status'],'CAPTURED_QUOTES')
            self.assertEqual(second['status'],'CACHED_QUOTES')
            self.assertEqual(len(sends),1)
            from datetime import datetime, timezone, timedelta
            from plugins.analyst_trader import research_finviz as fv
            future=datetime.now(timezone.utc)+timedelta(seconds=6)
            class Future(datetime):
                @classmethod
                def now(cls,tz=None): return future
            with patch.dict(os.environ,FINVIZ_API_URL='https://elite.finviz.com/export/screener?auth=TEST_SECRET&f=TEST'),patch.object(fv,'datetime',Future):
                replay=cli.research_main([*args,'--run-id','one'],process_factory=lambda *a,**kw:Child())
                self.assertEqual(replay['requests'],0)
                refreshed=cli.research_main([*args,'--run-id','three'],process_factory=lambda *a,**kw:Child())
                self.assertEqual(refreshed['status'],'CAPTURED_QUOTES')
                self.assertEqual(len(sends),2)
                changed=list(args); changed[changed.index('--request-budget')+1]='0'
                for run_id,extra in [('three',[]),('one',['--recover-only']),('two',[])]:
                    with self.assertRaisesRegex(ValueError,'parameter conflict'):
                        cli.research_main([*changed,'--run-id',run_id,*extra],process_factory=lambda *a,**kw:Child())
            view=cli.research_main(['status','--root',str(root),'--cohort','TEST'])['watchlist']
            quote=view['quote_snapshots'][0]
            self.assertEqual(quote['quotes'][0]['price'],123.45)
            self.assertEqual(quote['missing_tickers'],['MSFT'])
            self.assertIsNone(quote['provider_observed_at'])
            self.assertEqual(view['source_availability']['finviz']['access_status'],'SAVED_QUOTES_ONLY')
            self.assertEqual(view['snapshot_count'],0)
            self.assertEqual(view['underlying_snapshot_count'],0)
            self.assertIsNone(view['technicals']['ema'])
            self.assertNotIn('TEST_SECRET',json.dumps(first))
            self.assertNotIn('TEST_SECRET',(db.parent/'finviz-cycle-state.json').read_text())
