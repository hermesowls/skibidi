"""Actual OS-worker gate; run with stage2_worker_guard.py, not unguarded pytest."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import stage2_worker_guard as guard
from plugins.analyst_trader.realdata_transport import BoundedUWTransport

PARAMS = {'limit':'1','include_agg_trades':'false'}
TOKEN = 'TEST-DUMMY-CREDENTIAL'

class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.assertIn('WORKER_SANDBOX', os.environ, 'use dedicated sandbox runner')
        self.root = Path(os.environ['WORKER_SANDBOX'])
        self.children = []

    def factory(self, scenario, delay=0):
        def start(command, **kwargs):
            self.assertEqual(command, [sys.executable,'-I','-B',str(guard.WORKER)])
            child = guard.spawn([sys.executable,'-I','-B',str(guard.FIXTURE),scenario,str(self.root)], **kwargs)
            self.children.append(child)
            if delay: time.sleep(delay)
            return child
        return start

    def call(self, scenario, timeout=3, delay=0):
        return BoundedUWTransport(TOKEN, process_factory=self.factory(scenario,delay))('/api/option-trades',params=PARAMS,timeout=timeout)

    def tearDown(self):
        for child in self.children:
            self.assertIsNotNone(child.poll(), 'child still running')
            with self.assertRaises(ChildProcessError): os.waitpid(child.pid, os.WNOHANG)
            with self.assertRaises(ProcessLookupError): os.kill(child.pid,0)
            self.assertTrue(child.stdin.closed)
            self.assertTrue(child.stdout.closed)
            denials = self.root/('denials-'+str(child.pid))
            if denials.exists(): self.assertEqual(json.loads(denials.read_text()), [])

    def test_actual_entrypoint_stub_success_is_test_only_single_attempt(self):
        result = self.call('ok')
        self.assertEqual(result['source'],'TEST_FIXTURE')
        self.assertEqual(result['body'],{'data':[{}]})
        self.assertEqual(len(self.children),1)
        self.assertEqual((self.root/('attempts-'+str(self.children[0].pid))).read_text().splitlines(),['TEST HTTP boundary'])

    def test_targeted_params_survive_actual_worker_process(self):
        params = dict(limit='20', include_agg_trades='false', min_premium='50000', min_size='500', volume_greater_oi='true', min_dte='1', max_dte='14', is_otm='true')
        result = BoundedUWTransport(TOKEN, process_factory=self.factory('ok'))('/api/option-trades', params=params, timeout=3)
        self.assertEqual(result['source'], 'TEST_FIXTURE')
        self.assertEqual(json.loads((self.root/('params-'+str(self.children[0].pid))).read_text()), params)
        self.assertEqual(len(self.children), 1)

    def test_actual_entrypoint_body_overflow_status_and_secret_error(self):
        for scenario in ('overflow','status','error'):
            with self.subTest(scenario=scenario):
                with self.assertRaisesRegex(ValueError,'UW worker failed; no retry') as caught:
                    self.call(scenario)
                self.assertNotIn(TOKEN,str(caught.exception))
                pid = self.children[-1].pid
                self.assertEqual((self.root/('attempts-'+str(pid))).read_text().splitlines(),['TEST HTTP boundary'])
                self.assertTrue((self.root/('closed-'+str(pid))).exists())
                self.assertEqual((self.root/('stderr-'+str(pid))).read_text(), 'Bounded UW worker failed; no retry\n')
        self.assertEqual(len(self.children),3)

    def test_watchdog_reaps_deliberately_hung_fixture(self):
        started = time.monotonic()
        with self.assertRaisesRegex(ValueError,'worker killed; no retry'):
            self.call('hang',timeout=.5)
        self.assertLess(time.monotonic()-started,2)
        self.assertEqual(len(self.children),1)
        self.assertEqual(self.children[0].returncode,-signal.SIGKILL)
        self.assertTrue((self.root/('started-'+str(self.children[0].pid))).exists())

    def test_flooding_fixture_has_no_pipe_deadlock(self):
        started = time.monotonic()
        with self.assertRaisesRegex(ValueError,'deadline'):
            self.call('flood',timeout=.25)
        self.assertLess(time.monotonic()-started,2)
        self.assertEqual(self.children[0].returncode,-signal.SIGKILL)

    def test_output_limit_rejects_completed_fixture(self):
        with self.assertRaisesRegex(ValueError,'output exceeds bounds'):
            self.call('output')

    def test_startup_elapsed_is_not_given_fresh_budget(self):
        started = time.monotonic()
        with self.assertRaisesRegex(ValueError,'deadline'):
            self.call('hang',timeout=.1,delay=.25)
        self.assertLess(time.monotonic()-started,.7)
        self.assertEqual(self.children[0].returncode,-signal.SIGKILL)

    def test_unmodified_production_entrypoint_invalid_input_fails_closed(self):
        child = guard.spawn([sys.executable,'-I','-B',str(guard.WORKER)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env={},close_fds=True)
        self.children.append(child)
        out,_ = child.communicate(b'{"token":"TEST-DUMMY-CREDENTIAL","limit":0,"timeout":1}',timeout=3)
        child.stdin.close(); child.stdout.close()
        self.assertEqual(child.returncode,1)
        self.assertEqual(out,b'')

    def test_real_research_rejects_actual_fixture_worker_provenance(self):
        import sqlite3
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles
        from plugins.analyst_trader.realdata_store import ResearchStore
        from plugins.analyst_trader.realdata_research import run_once
        source = self.root/'profiles.sqlite'
        profile = research_profiles.create(AnalystDatabase(source),'TEST worker lifecycle')
        with sqlite3.connect(source) as c: c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        db = ResearchStore(self.root/'research.sqlite',source,profile['version_id'])
        grant = dict(mode='REAL_DATA_RESEARCH',authorized=True,profile_version=profile['version_id'],evidence_cohort='REAL_DATA_RESEARCH')
        transport = BoundedUWTransport(TOKEN,process_factory=self.factory('ok'))
        with self.assertRaisesRegex(ValueError,'not real observations'):
            run_once(db,grant,transport=transport,now=None,timeout_seconds=3)
        with sqlite3.connect(db.path) as c:
            self.assertEqual(c.execute("SELECT name FROM sqlite_master WHERE name='realdata_research_records'").fetchall(),[])

    def test_actual_child_cleanup_after_communication_error(self):
        def factory(command, **kwargs):
            child = self.factory('hang')(command, **kwargs)
            def broken(*args, **kw): raise OSError('TEST communication failure')
            child.communicate = broken
            return child
        with self.assertRaisesRegex(OSError,'TEST communication failure'):
            BoundedUWTransport(TOKEN,process_factory=factory)('/api/option-trades',params=PARAMS,timeout=1)
        self.assertEqual(self.children[0].returncode,-signal.SIGKILL)

    def test_kernel_network_policy_denied_without_creating_socket(self):
        import ctypes
        library = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
        self.assertEqual(library.sandbox_check(os.getpid(),b'network-outbound',0),1)
        self.assertEqual(library.sandbox_check(os.getpid(),b'network-inbound',0),1)

    def test_kill_failure_is_not_misreported_as_reaped(self):
        class FailedKill:
            stdin = stdout = None
            def communicate(self,*args,**kwargs): raise subprocess.TimeoutExpired('TEST',.1)
            def kill(self): raise PermissionError('TEST kill denied')
        with self.assertRaisesRegex(PermissionError,'kill denied'):
            BoundedUWTransport(TOKEN,process_factory=lambda *a,**kw: FailedKill())('/api/option-trades',params=PARAMS,timeout=.1)
