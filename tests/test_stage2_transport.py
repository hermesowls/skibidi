"""Offline external-boundary fakes only; no sockets or worker processes."""
import json
import unittest


class Caller(unittest.TestCase):
    def test_real_mode_rejects_unconstrained_db_before_transport(self):
        from plugins.analyst_trader.realdata_research import run_once
        grant = dict(mode='REAL_DATA_RESEARCH', authorized=True,
                     profile_version='TEST', evidence_cohort='REAL_DATA_RESEARCH')
        calls = []
        with self.assertRaisesRegex(ValueError, 'dedicated'):
            run_once(object(), grant, now=None, transport=lambda *a, **kw: calls.append(1))
        self.assertEqual(calls, [])

    def test_profile_bridge_requires_standalone_snapshot(self):
        import tempfile
        from pathlib import Path
        from plugins.analyst_trader.realdata_store import ReadOnlyProfiles
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'profiles.sqlite'
            source.write_bytes(b'')
            source.with_name(source.name+'-wal').write_bytes(b'TEST pending WAL')
            with self.assertRaisesRegex(ValueError, 'snapshot'):
                ReadOnlyProfiles(source)

    def test_readonly_source_unknown_profile_and_foreign_destination(self):
        import sqlite3
        import tempfile
        from pathlib import Path
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles
        from plugins.analyst_trader.realdata_store import ReadOnlyProfiles, ResearchStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'source.sqlite'; dest = root/'dest.sqlite'
            profile = research_profiles.create(AnalystDatabase(source), 'TEST')
            # Fixture setup exports/checkpoints a standalone source before caller.
            with sqlite3.connect(source) as setup:
                setup.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            before = source.read_bytes()
            c = ReadOnlyProfiles(source)._get_connection()
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    c.execute('CREATE TABLE forbidden (x)')
            finally: c.close()
            with self.assertRaisesRegex(ValueError, 'UNKNOWN_PROFILE'):
                ResearchStore(dest, source, 'not-the-selected-profile')
            self.assertFalse(dest.exists())
            with sqlite3.connect(dest) as c: c.execute('CREATE TABLE production (x)')
            original = dest.read_bytes()
            with self.assertRaisesRegex(ValueError, 'dedicated'):
                ResearchStore(dest, source, profile['version_id'])
            self.assertEqual(dest.read_bytes(), original)
            self.assertEqual(source.read_bytes(), before)

    def test_cli_reads_exact_profile_and_only_writes_dedicated_research(self):
        import tempfile
        import sqlite3
        from pathlib import Path
        from datetime import datetime, timezone
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles, realdata_cli
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'profiles.sqlite'
            profile = research_profiles.create(AnalystDatabase(source), 'TEST exact', {'max_otm_fraction': .15})
            # Fixture setup exports/checkpoints a standalone source before caller.
            with sqlite3.connect(source) as setup:
                setup.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            before = source.read_bytes()
            fixture = root/'fixture.json'
            fixture.write_text(json.dumps(dict(status=200, source='TEST_FIXTURE',
                received_at=datetime.now(timezone.utc).isoformat(), body={'data':[{}]})))
            dest = root/'research.sqlite'
            args = ['--authorize-research', '--profile-db', str(source), '--profile-version',
                    profile['version_id'], '--research-db', str(dest), '--test-response', str(fixture)]
            result = realdata_cli.main(args)
            self.assertEqual(result['records'][0]['mode'], 'TEST')
            self.assertEqual(result['records'][0]['policy_version'], profile['version_id'])
            self.assertEqual(source.read_bytes(), before)
            with sqlite3.connect(dest) as c:
                tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables, {'research_store_identity', 'realdata_research_records'})
            for target in [source, root/'link.sqlite', root/'hard.sqlite']:
                if target.name == 'link.sqlite': target.symlink_to(source)
                if target.name == 'hard.sqlite':
                    import os
                    os.link(source, target)
                bad = list(args); bad[bad.index('--research-db')+1] = str(target)
                with self.assertRaisesRegex(ValueError, 'separate'):
                    realdata_cli.main(bad)
            self.assertEqual(source.read_bytes(), before)
            with self.assertRaises(SystemExit): realdata_cli.main(args[1:])


class Transport(unittest.TestCase):
    def test_other_communication_failure_still_kills_worker(self):
        from plugins.analyst_trader.realdata_transport import BoundedUWTransport
        calls = []
        class Process:
            def communicate(self, *a, **kw): raise OSError('TEST broken pipe')
            def kill(self): calls.append('kill')
            def wait(self, timeout): calls.append('wait')
        with self.assertRaises(OSError):
            BoundedUWTransport('TEST', process_factory=lambda *a, **kw: Process())(
                '/api/option-trades', params={'limit':'1','include_agg_trades':'false'}, timeout=1)
        self.assertEqual(calls, ['kill', 'wait'])

    def test_deadline_kills_worker_without_retry(self):
        import subprocess
        from plugins.analyst_trader.realdata_transport import BoundedUWTransport
        calls = []
        class Process:
            def communicate(self, data=None, timeout=None):
                calls.append(('communicate', timeout))
                raise subprocess.TimeoutExpired('TEST-worker', timeout)
            def kill(self): calls.append(('kill',))
            def wait(self, timeout=None): calls.append(('wait', timeout)); return -9
        def factory(*args, **kwargs):
            calls.append(('spawn', kwargs))
            return Process()
        t = BoundedUWTransport('TEST-NOT-CREDENTIAL', process_factory=factory)
        with self.assertRaisesRegex(ValueError, 'deadline'):
            t('/api/option-trades', params={'limit':'20','include_agg_trades':'false'}, timeout=.1)
        self.assertEqual([c[0] for c in calls], ['spawn','communicate','kill','wait'])
        self.assertEqual(calls[0][1]['env'], {})
        self.assertLessEqual(calls[1][1], .1)
        self.assertLessEqual(calls[-1][1], 1)

    def test_http_errors_stream_cap_and_read_timeout_stop_once(self):
        import httpx
        from plugins.analyst_trader import realdata_http_worker as worker
        for status, headers, chunks, error in [
            (401, {}, [], 'no retry'), (403, {}, [], 'no retry'),
            (429, {}, [], 'no retry'), (302, {}, [], 'no retry'),
            (200, {'content-encoding':'gzip'}, [], 'Compressed'),
            (200, {'content-length':str(worker.BODY_CAP+1)}, [], 'bounds'),
            (200, {}, [b'x'*16384]*65, 'bounds'),
            (200, {}, [httpx.ReadTimeout('TEST')], 'TEST')]:
            calls = []
            class Response:
                status_code = status
                def __enter__(self): return self
                def __exit__(self, *a): calls.append('closed')
                def iter_raw(self, chunk_size):
                    for chunk in chunks:
                        if isinstance(chunk, Exception): raise chunk
                        yield chunk
            response = Response(); response.headers = headers
            class Client:
                def stream(self, *a, **kw): calls.append('request'); return response
            with self.subTest(status=status, error=error):
                with self.assertRaisesRegex((ValueError, httpx.ReadTimeout), error):
                    worker.fetch('TEST', 1, 1, client=Client())
                self.assertEqual(calls, ['request', 'closed'])

    def test_default_client_disables_environment_and_retries(self):
        from unittest.mock import patch
        import httpx
        from plugins.analyst_trader import realdata_http_worker as worker
        class Response:
            status_code = 429
            def __enter__(self): return self
            def __exit__(self, *a): pass
        class Client:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def stream(self, *a, **kw): return Response()
        with patch.object(httpx, 'HTTPTransport') as transport, patch.object(httpx, 'Client', return_value=Client()) as client:
            with self.assertRaisesRegex(ValueError, '429'):
                worker.fetch('TEST', 1, 1)
            self.assertEqual(transport.call_args.kwargs, {'retries': 0, 'trust_env': False})
            self.assertFalse(client.call_args.kwargs['trust_env'])

    def test_stream_is_bounded_and_declared_synthetic(self):
        from plugins.analyst_trader import realdata_http_worker as worker
        seen = {}
        class Response:
            status_code = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def iter_raw(self, chunk_size):
                seen['chunk_size'] = chunk_size
                yield b'{"data":[]}'
        class Client:
            def stream(self, method, url, **kwargs):
                seen.update(kwargs, url=url)
                return Response()
        result = worker.fetch('TEST-NOT-CREDENTIAL', 20, 2, client=Client())
        self.assertEqual(seen['url'], 'https://api.unusualwhales.com/api/option-trades')
        self.assertEqual(seen['params'], {'limit':'20','include_agg_trades':'false'})
        self.assertEqual(result['source'], 'TEST_FIXTURE')
        self.assertEqual(result['body'], {'data': []})
        self.assertEqual(seen['timeout'].connect, 2)
        self.assertEqual(seen['timeout'].read, 2)
        self.assertEqual(seen['headers']['Accept-Encoding'], 'identity')
        self.assertLessEqual(seen['chunk_size'], 65536)
        self.assertFalse(seen['follow_redirects'])
