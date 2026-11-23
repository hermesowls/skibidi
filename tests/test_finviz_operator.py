"""Offline public operator recovery; only worker HTTP/process boundaries injected."""
import base64, io, json, os, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from test_underlying_auto import AutomaticDaily
from plugins.analyst_trader import realdata_cli as cli, research_finviz as fv, realdata_finviz_worker as worker

class Operator(unittest.TestCase):
 def test_legacy_review_lock_and_corruption(self):
  import fcntl
  for code,retry in [(200,None),(429,None),(401,None),(429,'bad')]:
   with self.subTest(code=code,retry=retry),tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
    root=Path(tmp); db,args=AutomaticDaily().setup_case(root); path=db.parent/'finviz-cycle-state.json'
    raw=json.dumps(dict(cohort='TEST',receipt=dict(status=code,retry_after=retry,received_at='2026-10-01T12:00:00Z',raw_body=base64.b64encode(b'Ticker,Price\nSPY,123\n').decode())),indent=3).encode()
    path.write_bytes(raw)
    common=['--provider','finviz','--root',str(root),'--cohort','TEST','--authorize-research']
    status=cli.research_main(['recovery-status',*common])
    if retry=='bad':
     self.assertEqual(status['status'],'EVIDENCE_HOLD'); self.assertEqual(path.read_bytes(),raw); continue
    op=['--run-id',status['stop']['run_id'],'--release-id','migration','--receipt-reference',status['receipt_reference'],'--operator','TEST operator','--reason','TEST evidence reviewed','--operator-decision','allow-new-cycle','--review-decision','legacy-evidence-reviewed']
    with path.with_suffix('.lock').open('a') as lock:
     fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
     with self.assertRaises((RuntimeError,BlockingIOError)): cli.research_main(['migrate-ledger',*common,*op])
    self.assertEqual(cli.research_main(['migrate-ledger',*common,*op])['status'],'MIGRATED')
    self.assertEqual(cli.research_main(['migrate-ledger',*common,*op])['status'],'MIGRATION_REPLAY')
    saved=json.loads(path.read_text()); self.assertEqual(base64.b64decode(saved['legacy']['original_base64']),raw)
    self.assertEqual(saved['legacy']['sha256'],fv.rw.digest(raw))
    status=cli.research_main(['recovery-status',*common])
    release=['release-rate-limit',*common,'--run-id',status['stop']['run_id'],'--release-id','release','--receipt-reference',status['receipt_reference'],'--operator','TEST operator','--reason','TEST reviewed','--operator-decision','allow-new-cycle']
    with self.assertRaisesRegex(ValueError,'review'): cli.research_main(release)
    review='auth-repair-intent-reviewed' if code==401 else 'legacy-evidence-reviewed'
    self.assertEqual(cli.research_main([*release,'--review-decision',review])['status'],'RELEASED')
    self.assertEqual(json.loads(path.read_text())['runs'][status['stop']['run_id']]['receipt'],json.loads(raw)['receipt'])
    args[args.index('--uw-live')]='--finviz-live'; args[args.index('underlying')]='quotes'
    sends=[]
    class Child:
     stdin=stdout=None
     def communicate(self,payload,timeout):
      sends.append(1); self.returncode=0
      return json.dumps(dict(status=200,received_at=datetime.now(timezone.utc).isoformat(),raw_body=base64.b64encode(b'Ticker,Price\nSPY,124\n').decode())).encode(),None
    with patch.dict(os.environ,FINVIZ_API_URL='https://elite.finviz.com/export/screener?auth=TEST_SECRET'):
     self.assertEqual(cli.research_main([*args,'--run-id','fresh'],process_factory=lambda *a,**k:Child())['status'],'CAPTURED_QUOTES')
    self.assertEqual(sends,[1]); self.assertEqual(base64.b64decode(json.loads(path.read_text())['legacy']['original_base64']),raw)
  with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
   root=Path(tmp); db,args=AutomaticDaily().setup_case(root); path=db.parent/'finviz-cycle-state.json'
   valid=dict(cohort='TEST',receipt=dict(status=200,received_at='2026-10-01T12:00:00Z',raw_body=''))
   conflicting=dict(valid,provider_stop=dict(status='SEND_OUTCOME_UNKNOWN'))
   duplicate=json.dumps(valid).replace('"cohort": "TEST"','"cohort": "REAL_DATA_RESEARCH", "cohort": "TEST"').encode()
   for raw in (b'{',b'{"cohort":"TEST","status":"CONSUMED"}',duplicate,json.dumps(conflicting).encode()):
    path.write_bytes(raw)
    self.assertEqual(cli.research_main(['migrate-ledger','--provider','finviz','--root',str(root),'--cohort','TEST','--authorize-research'])['status'],'EVIDENCE_HOLD')
    self.assertEqual(path.read_bytes(),raw)

 def test_unknown_auth_and_capacity(self):
  for code in (429,401,403):
   with self.subTest(code=code),tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
    root=Path(tmp); db,args=AutomaticDaily().setup_case(root); path=db.parent/'finviz-cycle-state.json'
    args[args.index('--uw-live')]='--finviz-live'; args[args.index('underlying')]='quotes'
    class Child:
     stdin=stdout=None
     def communicate(self,payload,timeout):
      self.returncode=0
      return json.dumps(dict(status=code,received_at=datetime.now(timezone.utc).isoformat(),raw_body='',retry_after=None)).encode(),None
    with patch.dict(os.environ,FINVIZ_API_URL='https://elite.finviz.com/export/screener?auth=TEST_SECRET'):
     cli.research_main([*args,'--run-id','one'],process_factory=lambda *a,**k:Child())
    common=['--provider','finviz','--root',str(root),'--cohort','TEST','--authorize-research']
    status=cli.research_main(['recovery-status',*common])
    release=['release-rate-limit',*common,'--run-id','one','--release-id','release','--receipt-reference',status['receipt_reference'],'--operator','TEST','--reason','Reviewed intent, not verified access','--operator-decision','allow-new-cycle']
    before=path.read_bytes()
    corrupt=json.loads(before); corrupt['provider_stop']['retry_after']='0'
    path.write_text(json.dumps(corrupt))
    self.assertEqual(cli.research_main(['recovery-status',*common])['status'],'EVIDENCE_HOLD')
    path.write_bytes(before)
    with self.assertRaisesRegex(ValueError,'review'): cli.research_main(release)
    self.assertEqual(path.read_bytes(),before)
    required='unknown-quota-reviewed' if code==429 else 'auth-repair-intent-reviewed'
    self.assertEqual(cli.research_main([*release,'--review-decision',required])['status'],'RELEASED')
    path.write_bytes(b' '*1500001)
    self.assertEqual(cli.research_main(['recovery-status',*common])['status'],'CAPACITY_HOLD')

 def test_release_lifecycle(self):
  with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
   root=Path(tmp); db,args=AutomaticDaily().setup_case(root)
   args[args.index('--uw-live')]='--finviz-live'; args[args.index('underlying')]='quotes'
   now=datetime.now(timezone.utc); codes=[429,200,429]; sends=[]
   class Clock(datetime):
    @classmethod
    def now(cls,tz=None): return now
   class Response:
    headers={'content-type':'text/csv','retry-after':'10'}
    def __init__(self): self.status_code=codes[len(sends)-1]
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def iter_raw(self,**kw): yield b'Ticker,Price\nSPY,123\n'
   class Client:
    def __init__(self,**kw): pass
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def stream(self,*a,**kw): sends.append(1); return Response()
   class Child:
    stdin=stdout=None
    def communicate(self,payload,timeout):
     out=io.StringIO()
     with patch.object(worker.sys,'stdin',type('Input',(),{'buffer':io.BytesIO(payload)})()),patch.object(worker.sys,'stdout',out),patch('httpx.Client',Client),patch('httpx.HTTPTransport',lambda **kw:None): self.returncode=worker.main()
     return out.getvalue().encode(),None
   common=['--provider','finviz','--root',str(root),'--cohort','TEST','--authorize-research']
   with patch.dict(os.environ,FINVIZ_API_URL='https://elite.finviz.com/export/screener?auth=TEST_SECRET'),patch.object(fv,'datetime',Clock):
    self.assertEqual(cli.research_main([*args,'--run-id','one'],process_factory=lambda *a,**k:Child())['requests'],1)
    status=cli.research_main(['recovery-status',*common])
    release=['release-rate-limit',*common,'--run-id','one','--release-id','release1','--receipt-reference',status['receipt_reference'],'--operator','TEST operator','--reason','Reviewed TEST quota','--operator-decision','allow-new-cycle']
    with self.assertRaisesRegex(ValueError,'deadline'): cli.research_main(release)
    now+=timedelta(seconds=11)
    self.assertEqual(cli.research_main(release)['status'],'RELEASED')
    self.assertEqual(cli.research_main(release)['status'],'RELEASE_REPLAY')
    with self.assertRaisesRegex(ValueError,'conflict'): cli.research_main([*release,'--reason','changed'])
    self.assertEqual(cli.research_main([*args,'--run-id','two'],process_factory=lambda *a,**k:Child())['status'],'CAPTURED_QUOTES')
    now+=timedelta(seconds=6)
    self.assertEqual(cli.research_main([*args,'--run-id','three'],process_factory=lambda *a,**k:Child())['requests'],1)
    self.assertEqual(cli.research_main(release)['status'],'RELEASE_REPLAY')
    self.assertEqual(cli.research_main(['recovery-status',*common])['stop']['run_id'],'three')
    self.assertEqual(cli.research_main([*args,'--run-id','four'],process_factory=lambda *a,**k:Child())['requests'],0)
   saved=json.loads((db.parent/'finviz-cycle-state.json').read_text())
   self.assertEqual(len(sends),3); self.assertFalse(saved['operations']['release1']['authenticated_authority'])
   self.assertEqual(saved['runs']['one']['attempts'],1)
