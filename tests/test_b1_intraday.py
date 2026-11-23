"""B1 positive HTTP -> worker main -> transport -> durable public caller gate."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from plugins.analyst_trader import realdata_intraday_worker as worker
from plugins.analyst_trader.realdata_transport import BoundedUWIntradayTransport
from plugins.analyst_trader import research_watchlist as watch


class B1(unittest.TestCase):
    def test_visible_429_survives_every_bad_body_without_second_send(self):
        spec = importlib.util.spec_from_file_location('b1_coordinator', Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        coordinator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(coordinator)
        for kind in ('compressed', 'oversized_header', 'oversized_stream', 'malformed', 'schema', 'read_error', 'stall', 'close_error', 'unsafe_retry'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as td:
                root = Path(td)
                source = root/'seed.json'
                source.write_text(json.dumps({'records':[dict(mode='TEST', provider_event_id='TEST', received_at='2026-09-24T16:00:00Z', evidence={'contract_symbol':'AAOI260925C00100000'}, raw={})]}))
                db = root/'TEST/watchlist.sqlite'
                watch.seed(db, source)
                sends, reads, outputs = [], [], []
                class Response:
                    status_code = 429
                    headers = {'retry-after': '120'}
                    def __enter__(self): return self
                    def __exit__(self, *args):
                        if kind == 'close_error': raise OSError('TEST_SECRET close failure')
                    def iter_raw(self, chunk_size):
                        reads.append(1)
                        if kind in ('read_error', 'stall'):
                            raise TimeoutError('TEST_SECRET must never escape')
                        yield (b'x' * (worker.BODY_CAP + 1) if kind == 'oversized_stream' else b'not-json' if kind == 'malformed' else b'{"data":null}')
                if kind == 'compressed': Response.headers = {'retry-after':'120', 'content-encoding':'gzip'}
                if kind == 'oversized_header': Response.headers = {'retry-after':'120', 'content-length':str(worker.BODY_CAP + 1)}
                if kind == 'unsafe_retry': Response.headers = {'retry-after':'TEST_SECRET\r\nInjected: yes'}
                class Client:
                    def __init__(self, *args, **kwargs): pass
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def stream(self, *args, **kwargs): sends.append(1); return Response()
                class Child:
                    stdin = stdout = None
                    def communicate(self, payload, timeout):
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch.object(worker.sys, 'stdin', type('Input', (), {'buffer':io.BytesIO(payload)})()), patch.object(worker.sys, 'stdout', stdout), patch.object(worker.sys, 'stderr', stderr), patch('httpx.Client', Client), patch('httpx.HTTPTransport', lambda **kw: None):
                            self.returncode = worker.main()
                        outputs.append(stdout.getvalue()+stderr.getvalue())
                        return stdout.getvalue().encode(), None
                transport = BoundedUWIntradayTransport('TEST_SECRET', process_factory=lambda *a, **kw: Child())
                def run():
                    return coordinator.run_research_followup(root=root, grant=dict(authorized=True, evidence_cohort='TEST', source='TEST_TRANSPORT'), transport=transport, date='2026-09-24', now='2026-09-24T17:00:00Z', max_requests=1, min_interval_seconds=0)
                first, second = run(), run()
                state = json.loads((db.parent/'followup-state.json').read_text())
                self.assertEqual(len(sends), 1)
                self.assertEqual(first['status'], 'RATE_LIMITED')
                self.assertEqual(second['requests'], 0)
                self.assertTrue(state['rate_limited'])
                claim = state['claims'][0]
                self.assertEqual(claim['http_status'], 429)
                self.assertEqual(claim['retry_after'], None if kind == 'unsafe_retry' else '120')
                self.assertEqual(claim['status'], 'RATE_LIMITED')
                self.assertEqual(claim['body_status'], 'NOT_READ_HTTP_ERROR')
                self.assertNotIn('raw_body', claim)
                self.assertNotIn('raw_hash', claim)
                self.assertEqual(reads, [])  # Even a stalled rejection body cannot lose known headers.
                self.assertNotIn('TEST_SECRET', json.dumps(state) + ''.join(outputs))
                self.assertEqual(claim['evidence_cohort'], 'TEST')
                self.assertEqual(claim['source'], 'TEST_FIXTURE')
