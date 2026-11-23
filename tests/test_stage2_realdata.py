"""Synthetic TEST transport fixtures; never Stage3 market evidence."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader import research_profiles


class RealDataResearch(unittest.TestCase):
    def test_provenance_authorization_and_request_bounds_fail_closed(self):
        from plugins.analyst_trader import realdata_research as research
        with tempfile.TemporaryDirectory() as root:
            db = AnalystDatabase(Path(root)/'research.sqlite')
            profile = research_profiles.create(db, 'TEST safety')
            now = datetime.now(timezone.utc)
            grant = dict(mode='REAL_DATA_RESEARCH', authorized=True,
                         profile_version=profile['version_id'], evidence_cohort='TEST')
            calls = []
            response = dict(status=200, source='TEST_FIXTURE', received_at=now.isoformat(), body={'data':[]})
            def transport(*args, **kwargs):
                calls.append(kwargs)
                return response
            for change in ({'mode':'paper_test'}, {'mode':'live'}, {'authorized':1},
                           {'evidence_cohort':'anything'}, {'publication_authorized':True}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    research.run_once(db, dict(grant, **change), transport=transport, now=now)
            self.assertEqual(calls, [])
            for bound in (0, 101, True):
                with self.assertRaises(ValueError):
                    research.run_once(db, grant, transport=transport, now=now, max_rows=bound)
            for timeout in (0, 31, True, float('nan')):
                with self.assertRaises(ValueError):
                    research.run_once(db, grant, transport=transport, now=now, timeout_seconds=timeout)
            self.assertEqual(calls, [])
            for status in (401, 403, 429, 500):
                response['status'] = status
                before = len(calls)
                with self.assertRaisesRegex(ValueError, 'no retry'):
                    research.run_once(db, grant, transport=transport, now=now)
                self.assertEqual(len(calls), before+1)
            response['status'] = 200
            with self.assertRaisesRegex(ValueError, 'provenance'):
                research.run_once(db, dict(grant, evidence_cohort='REAL_DATA_RESEARCH'), transport=transport, now=now)
            response['source'] = 'cache'
            with self.assertRaisesRegex(ValueError, 'provenance'):
                research.run_once(db, grant, transport=transport, now=now)
            response['source'] = 'TEST_FIXTURE'
            response['received_at'] = '2020-01-01T00:00:00+00:00'
            with self.assertRaisesRegex(ValueError, 'Stale'):
                research.run_once(db, grant, transport=transport, now=now)
            response['received_at'] = now.isoformat()
            response['body'] = {'data':[{}]*21}
            with self.assertRaisesRegex(ValueError, 'bounds'):
                research.run_once(db, grant, transport=transport, now=now)
            with db._get_connection() as c:
                self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='realdata_research_records'").fetchone())

    def test_malformed_alert_is_visible_and_never_qualifies(self):
        from plugins.analyst_trader import realdata_research as research
        with tempfile.TemporaryDirectory() as root:
            db = AnalystDatabase(Path(root)/'research.sqlite')
            profile = research_profiles.create(db, 'TEST malformed')
            now = datetime.now(timezone.utc)
            response = dict(status=200, source='TEST_FIXTURE', received_at=now.isoformat(), body={'data':[{}]})
            grant = dict(mode='REAL_DATA_RESEARCH', authorized=True,
                         profile_version=profile['version_id'], evidence_cohort='TEST')
            result = research.run_once(db, grant, transport=lambda *a, **k:response, now=now)
            row = result['records'][0]
            self.assertEqual(row['baseline_status'], 'INCOMPLETE')
            self.assertTrue(row['baseline_reasons'][0].startswith('malformed_alert:'))
            self.assertFalse(row['execution_authorized'])
            with db._get_connection() as c:
                import sqlite3
                with self.assertRaises(sqlite3.IntegrityError):
                    c.execute('DELETE FROM realdata_research_records')

    def test_public_run_preserves_test_provenance_and_selected_profile(self):
        from plugins.analyst_trader import realdata_research as research
        with tempfile.TemporaryDirectory() as root:
            db = AnalystDatabase(Path(root)/'research.sqlite')
            profile = research_profiles.create(db, 'TEST exact saved default')
            now = datetime.now(timezone.utc)
            calls = []
            # Only field names present in the inspected historical UW mirror.
            raw = dict(ticker='AAPL', option_type='CALL', strike='300', expiry='2026-10-02',
                       total_premium='150000', total_size=600, volume=800, open_interest=100)
            def transport(path, *, params, timeout):
                calls.append((path, params, timeout))
                return dict(status=200, source='TEST_FIXTURE', received_at=now.isoformat(),
                            body={'data':[raw]})
            grant = dict(mode='REAL_DATA_RESEARCH', authorized=True,
                         profile_version=profile['version_id'], evidence_cohort='TEST')
            with db._get_connection() as c:
                tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                counts = {t:c.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0] for t in tables}
            result = research.run_once(db, grant, transport=transport, now=now)
            with db._get_connection() as c:
                self.assertEqual(counts, {t:c.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0] for t in tables})
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], '/api/option-trades')
            candidate = result['records'][0]
            self.assertEqual(candidate['mode'], 'TEST')
            self.assertEqual(candidate['policy_version'], profile['version_id'])
            self.assertEqual(candidate['baseline_status'], 'INCOMPLETE')
            self.assertEqual(candidate['observation_status'], 'MALFORMED')
            self.assertIsNone(candidate['provider_event_id'])
            self.assertFalse(candidate['execution_authorized'])
            self.assertFalse(candidate['publication_authorized'])
            self.assertIsNone(profile['profile']['kian_research']['max_otm_fraction'])
            self.assertEqual(candidate['enhanced_status'], 'UNKNOWN')
            with db._get_connection() as c:
                saved = c.execute('SELECT payload_json FROM realdata_research_records').fetchall()
                self.assertEqual(len(saved), 1)
                self.assertEqual(json.loads(saved[0][0]), candidate)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM notable_flow').fetchone()[0], 0)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM learning_decisions').fetchone()[0], 0)
            again = research.run_once(db, grant, transport=transport, now=now)
            self.assertEqual(result, again)
            self.assertEqual(research_profiles.select(db, profile['version_id']), profile)
