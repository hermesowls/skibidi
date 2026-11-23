"""TEST external-boundary fixtures; never live market evidence."""
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from plugins.analyst_trader import realdata_http_worker as worker
from plugins.analyst_trader.realdata_transport import BoundedUWTransport
from plugins.analyst_trader.realdata_research import run_once
from plugins.analyst_trader import research_profiles
from plugins.analyst_trader.db import AnalystDatabase
from test_stage2_uw_schema import trade

PARAMS = dict(limit='20', include_agg_trades='false', min_premium='50000',
              min_size='500', volume_greater_oi='true', min_dte='1', max_dte='14', is_otm='true')

class Targeted(unittest.TestCase):
    def exercise(self, changes=None, raw_changes=None):
        seen = []
        class Response:
            status_code = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def iter_raw(self, chunk_size):
                yield json.dumps({'data':[raw]}).encode()
        class Client:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def stream(self, method, url, **kw):
                seen.append(kw['params'])
                return Response()
        class Process:
            returncode = 0
            stdin = None
            stdout = None
            def communicate(self, payload, timeout):
                output = io.StringIO()
                stdin = type('Input', (), {'buffer':io.BytesIO(payload)})()
                with patch.object(worker.sys, 'stdin', stdin), patch.object(worker.sys, 'stdout', output), patch('httpx.Client', return_value=Client()), patch('httpx.HTTPTransport'):
                    self.returncode = worker.main()
                return output.getvalue().encode(), None
        with tempfile.TemporaryDirectory() as tmp:
            db = AnalystDatabase(Path(tmp)/'TEST.sqlite')
            profile = research_profiles.create(db, 'TEST exact', changes or {})
            raw = trade(datetime.now(timezone.utc)); raw.pop('is_agg'); raw['underlying_price'] = None
            raw.update(raw_changes or {})
            grant = dict(mode='REAL_DATA_RESEARCH', authorized=True, profile_version=profile['version_id'], evidence_cohort='TEST')
            result = run_once(db, grant, now=None, transport=BoundedUWTransport('TEST', process_factory=lambda *a, **k: Process()), timeout_seconds=30)
            row = result['records'][0]
            self.assertEqual(row['request_provenance']['params'], seen[0])
            self.assertEqual(row['profile_content_hash'], profile['content_hash'])
            self.assertEqual(row['baseline_status'], 'INCOMPLETE')
            self.assertIsNone(row['evidence']['is_agg'])
            self.assertEqual(row['evidence']['spot_price'], None if raw['underlying_price'] is None else float(raw['underlying_price']))
            self.assertFalse(row['execution_authorized'])
            self.assertEqual(result['requests'], 1)
            self.assertEqual(len(seen), 1)
            self.assertEqual(profile['profile']['kian_research']['max_age_seconds'], 120)
        return seen[0], row

    def test_default_caller_transport_worker_httpx_exact_filters(self):
        params, row = self.exercise()
        self.assertEqual(params, PARAMS)

    def test_exact_saved_profile_values_not_hardcoded(self):
        params, row = self.exercise(dict(min_premium=75000.5, min_size=750, dte_min=2, dte_max=9, max_otm_fraction=.12, otm_required=False))
        self.assertEqual(params, dict((k,v) for k,v in dict(PARAMS, min_premium='75000.5', min_size='750', min_dte='2', max_dte='9').items() if k != 'is_otm'))
        self.assertEqual(row['max_otm_fraction'], .12)
        self.assertNotIn('max_otm_fraction', params)

    def test_raw_failures_visible_without_qualifying_missing_evidence(self):
        _, row = self.exercise(raw_changes=dict(premium='49999.99', size=499, volume=100, open_interest=100))
        self.assertEqual(row['raw_threshold_diagnostics']['failures'], ['premium', 'size', 'volume_gt_oi'])
        self.assertIn('otm', row['raw_threshold_diagnostics']['unknown'])
        self.assertEqual(row['discovery_status'], 'PROVIDER_FILTERED_CANDIDATE')
        self.assertFalse(row['raw_threshold_diagnostics']['qualifies'])

    def test_allowlist_rejects_bad_values_at_both_boundaries(self):
        invalid = [dict(PARAMS, **change) for change in (
            {'page':'1'}, {'older_than':'123'}, {'max_otm_fraction':'.1'},
            {'min_premium':'NaN'}, {'min_premium':'-1'}, {'min_premium':50000},
            {'min_size':'0'}, {'min_size':'1.1'}, {'min_size':str(2**63)},
            {'min_dte':'-1'}, {'max_dte':'0'}, {'limit':'101'},
            {'volume_greater_oi':'false'}, {'is_otm':'false'}, {'include_agg_trades':'true'})]
        invalid.append({k:v for k,v in PARAMS.items() if k != 'min_size'})
        for params in invalid:
            with self.subTest(params=params):
                with self.assertRaises(ValueError):
                    BoundedUWTransport('TEST', process_factory=lambda *a, **k: self.fail('spawned'))('/api/option-trades', params=params, timeout=1)
                with self.assertRaises(ValueError):
                    worker.fetch('TEST', 20, 1, params=params, client=object())

    def test_raw_exact_boundaries_and_local_cap_never_qualify(self):
        _, row = self.exercise(dict(max_otm_fraction=.12), dict(premium='50000', size=500, volume=101, open_interest=100, underlying_price='250'))
        checks = row['raw_threshold_diagnostics']['checks']
        self.assertTrue(checks['premium'])
        self.assertTrue(checks['size'])
        self.assertTrue(checks['volume_gt_oi'])
        self.assertFalse(checks['otm'])
        self.assertFalse(row['raw_threshold_diagnostics']['qualifies'])
        self.assertIsNone(row['evidence']['spot_observed_at'])

    def test_documented_zero_dte_and_local_row_hard_bound(self):
        worker.validate_params(dict(PARAMS, min_dte='0', max_dte='0', limit='100'))
        from plugins.analyst_trader.realdata_research import raw_threshold_diagnostics
        now = datetime(2026, 9, 24, 0, 30, tzinfo=timezone.utc)
        raw = trade(now)
        # New York is still Sept 23: expiry Oct 2 is nine calendar days.
        p = dict(min_premium=50000, min_size=500, calendar_zone='America/New_York', dte_min=9, dte_max=9, otm_required=True, max_otm_fraction=None)
        self.assertTrue(raw_threshold_diagnostics(raw, p, now)['checks']['dte'])
        p['dte_max'] = 8
        self.assertFalse(raw_threshold_diagnostics(raw, p, now)['checks']['dte'])
