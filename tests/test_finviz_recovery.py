"""Positive invariants promoted from the independent Finviz boundary probe."""
import asyncio, io, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from test_underlying_auto import AutomaticDaily
from plugins.analyst_trader import realdata_cli as cli, research_watchlist as rw, realdata_finviz_worker as worker

class Recovery(unittest.TestCase):
 def test_unknown_send_and_legacy_preservation(self):
  import base64
  for legacy in (False,True):
   with self.subTest(legacy=legacy),tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as temp:
    db,args=AutomaticDaily().setup_case(Path(temp))
    args[args.index('--uw-live')]='--finviz-live'; args[args.index('underlying')]='quotes'
    path=db.parent/'finviz-cycle-state.json'
    if legacy:
     raw=json.dumps(dict(cohort='TEST',receipt=dict(status=200,received_at='2026-10-01T12:00:00Z',raw_body=base64.b64encode(b'Ticker,Price\nSPY,123\n').decode()))).encode()
     path.write_bytes(raw)
     result=cli.research_main([*args,'--run-id','one','--recover-only'],process_factory=lambda *a,**k:self.fail('send'))
     self.assertEqual(result['status'],'RECOVERED')
     self.assertEqual(base64.b64decode(json.loads(path.read_text())['legacy']['original_base64']),raw)
     self.assertEqual(cli.research_main([*args,'--run-id','two'],process_factory=lambda *a,**k:self.fail('send'))['status'],'LEGACY_REVIEW_REQUIRED')
    else:
     sends=[]
     def failed(*a,**k): sends.append(1); raise RuntimeError('TEST_SECRET')
     with patch.dict(os.environ,FINVIZ_API_URL='https://elite.finviz.com/export/screener?auth=TEST_SECRET'):
      first=cli.research_main([*args,'--run-id','one'],process_factory=failed)
      second=cli.research_main([*args,'--run-id','two'],process_factory=failed)
      recovery=cli.research_main([*args,'--run-id','two','--recover-only'],process_factory=failed)
     self.assertEqual(first['status'],'FAILED_NO_RETRY'); self.assertEqual(sends,[1])
     self.assertEqual(second['requests'],0); self.assertEqual(recovery['status'],'HELD')
     self.assertNotIn('TEST_SECRET',path.read_text())

 def test_public_boundaries(self):
  for code,raw,retry in [(401,b'',None),(403,b'',None),(429,b'','0'),(429,b'',None),(429,b'','Thu, 01 Oct 2020 12:00:00 GMT'),(307,b'',None),(200,b'Ticker,Other\nSPY,1\n',None),(200,b'Ticker,Price\nSPY,123\n',None)]:
   with self.subTest(code=code,raw=raw,retry=retry), tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as temp:
    root=Path(temp); db,args=AutomaticDaily().setup_case(root)
    args[args.index('--uw-live')]='--finviz-live'; args[args.index('underlying')]='quotes'
    before=rw.read_watchlist(db); sends=[]
    class Response:
     status_code=code; headers={'content-type':'text/csv','retry-after':retry}
     def __enter__(self): return self
     def __exit__(self,*a):
      if code!=200: raise RuntimeError('TEST_SECRET')
     def iter_raw(self,**kw):
      assert code==200
      yield raw
    class Client:
     def __init__(self,**kw): assert kw['trust_env'] is False
     def __enter__(self): return self
     def __exit__(self,*a): pass
     def stream(self,method,url,**kw):
      assert url=='https://elite.finviz.com/export/screener?auth=TEST_SECRET'
      assert not kw['follow_redirects']; sends.append(1); return Response()
    class Child:
     stdin=stdout=None
     def communicate(self,payload,timeout):
      out=io.StringIO()
      with patch.object(worker.sys,'stdin',type('Input',(),{'buffer':io.BytesIO(payload)})()),patch.object(worker.sys,'stdout',out),patch('httpx.Client',Client),patch('httpx.HTTPTransport',lambda **kw:None): self.returncode=worker.main()
      return out.getvalue().encode(),None
    with patch.dict(os.environ,FINVIZ_API_URL='https://elite.finviz.com/export/screener?auth=TEST_SECRET'):
     first=cli.research_main([*args,'--run-id','one'],process_factory=lambda *a,**k:Child())
     results=[first]
     for extra in (['--run-id','two'],['--run-id','three','--recover-only']):
      results.append(cli.research_main([*args,*extra],process_factory=lambda *a,**k:Child()))
    self.assertEqual(sends,[1])
    state=(db.parent/'finviz-cycle-state.json').read_text()
    self.assertNotIn('TEST_SECRET',state+json.dumps(results))
    from hermes_cli import web_server
    with patch.object(rw,'canonical_path',return_value=db): view=asyncio.run(web_server.api_research_watchlist())
    self.assertEqual(view['mode'],'TEST')
    self.assertEqual(view['snapshot_count'],before['snapshot_count'])
    self.assertEqual(view['underlying_snapshot_count'],before['underlying_snapshot_count'])
    self.assertEqual(view['technicals'],before['technicals'])
    saved=json.loads(state)
    if code!=200:
     self.assertEqual(first['status'],'HTTP_REJECTED_REVIEW_REQUIRED')
     self.assertEqual(results[2]['status'],'HELD')
     self.assertEqual(saved['runs']['one']['receipt']['retry_after'],retry)
     self.assertEqual(saved['provider_stop']['retry_after'],retry)
    elif b'Other' in raw:
     self.assertEqual([r['status'] for r in results],['QUARANTINED']*3)
     self.assertTrue(saved['runs']['one']['receipt']['raw_body'])
    else:
     self.assertEqual(first['status'],'CAPTURED_QUOTES')
     self.assertEqual(results[2]['status'],'NO_PENDING_RECOVERY')
     self.assertEqual(view['quote_snapshots'][0]['quotes'][0]['price'],123)
