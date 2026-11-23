"""TEST ONLY: synthetic values using documented REST fields, not market proof."""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


def trade(now):
    return dict(id='TEST-original-id', executed_at=now.isoformat(),
        option_chain_id='AAPL261002C00300000', underlying_symbol='AAPL',
        option_type='call', expiry='2026-10-02', strike='300',
        premium='150000.123456789', size=600, volume=800, open_interest=0,
        underlying_price='250.25', is_agg=False, canceled=False, tags=['ask_side'])


class Schema(unittest.TestCase):
    def test_replay_of_prior_version_after_changed_observation_is_idempotent(self):
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles, realdata_research
        with tempfile.TemporaryDirectory() as directory:
            db = AnalystDatabase(Path(directory)/'TEST.sqlite')
            profile = research_profiles.create(db, 'TEST replay')
            now = datetime.now(timezone.utc); raw = trade(now)
            grant = dict(mode='REAL_DATA_RESEARCH', authorized=True,
                profile_version=profile['version_id'], evidence_cohort='TEST')
            def transport(*a, **kw):
                return dict(status=200, source='TEST_FIXTURE', received_at=now.isoformat(), body={'data':[dict(raw)]})
            def invoke(): return realdata_research.run_once(db, grant, transport=transport, now=now)
            first = invoke()
            raw['canceled'] = True
            invoke()
            raw['canceled'] = False
            self.assertEqual(invoke(), first)

    def test_documented_types_unknowns_and_contract_consistency(self):
        from plugins.analyst_trader.uw_option_trades import canonicalize_trade
        raw = trade(datetime.now(timezone.utc))
        for field, value in [('size',True), ('size',1.1), ('volume','800'),
                             ('open_interest',False), ('premium',150000),
                             ('premium','NaN'), ('is_agg',0), ('canceled','false'),
                             ('option_chain_id','AAPL261002P00300000'),
                             ('executed_at','2026-09-23'), ('id','')]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                canonicalize_trade(dict(raw, **{field:value}), 'TEST')
        for flag in (True, None):
            e = canonicalize_trade(dict(raw, is_agg=flag), 'TEST')
            self.assertIsNone(e['premium_usd'])
            self.assertIsNone(e['size'])
        for field in ('volume','open_interest','premium','underlying_price','is_agg','canceled'):
            missing = dict(raw); missing.pop(field)
            e = canonicalize_trade(missing, 'TEST')
            key = {'underlying_price':'spot_price','premium':'premium_usd'}.get(field,field)
            self.assertIsNone(e[key])
        e = canonicalize_trade(raw, 'TEST')
        self.assertEqual(e['open_interest'], 0)
        self.assertEqual(e['reported_side'], ['ask_side'])

    def test_public_caller_keeps_unknown_and_excluded_observations(self):
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles, realdata_research
        with tempfile.TemporaryDirectory() as directory:
            db = AnalystDatabase(Path(directory)/'TEST.sqlite')
            profile = research_profiles.create(db, 'TEST unknowns')
            now = datetime.now(timezone.utc)
            grant = dict(mode='REAL_DATA_RESEARCH', authorized=True,
                profile_version=profile['version_id'], evidence_cohort='TEST')
            rows = []
            for flag in ('is_agg','canceled'):
                for value in (True, None):
                    rows.append(dict(trade(now), id='TEST-'+flag+str(value), **{flag:value}))
            rows.append(dict(trade(now), id='T'*240))
            rows.append(dict(trade(now), id='TEST-future', executed_at='2099-01-01T00:00:00Z'))
            def transport(*a, **kw):
                return dict(status=200, source='TEST_FIXTURE', received_at=now.isoformat(), body={'data':rows})
            result = realdata_research.run_once(db, grant, transport=transport, now=now)
            for row in result['records']:
                expected = 'CHRONOLOGY_INVALID' if row['provider_event_id'] == 'TEST-future' else 'SCHEMA_VALID'
                self.assertEqual(row['observation_status'], expected)
                self.assertEqual(row['baseline_status'], 'INCOMPLETE')
                self.assertEqual(row['enhanced_status'], 'UNKNOWN')
                self.assertFalse(row['execution_authorized'])
                self.assertIsNone(row['evidence']['spot_observed_at'])
            self.assertIn('observed_at:stale_or_future', result['records'][-1]['baseline_reasons'])
            with db._get_connection() as c:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM realdata_research_records').fetchone()[0], len(rows))

    def test_actual_cli_retains_documented_observation_without_qualification(self):
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles, realdata_cli
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'profile.sqlite'
            profile = research_profiles.create(AnalystDatabase(source), 'TEST schema')
            with sqlite3.connect(source) as c: c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            raw = trade(datetime.now(timezone.utc))
            fixture = root/'response.json'; dest = root/'research.sqlite'
            def invoke():
                fixture.write_text(json.dumps(dict(status=200, source='TEST_FIXTURE',
                    received_at=datetime.now(timezone.utc).isoformat(), body={'data':[raw]})))
                return realdata_cli.main(['--authorize-research', '--profile-db', str(source),
                    '--profile-version', profile['version_id'], '--research-db', str(dest),
                    '--test-response', str(fixture)])['records'][0]
            row = invoke()
            self.assertEqual(row['provider_event_id'], raw['id'])
            self.assertEqual(row['observation_status'], 'SCHEMA_VALID')
            self.assertEqual(row['evidence']['premium_decimal'], raw['premium'])
            self.assertEqual(row['evidence']['observed_at'], raw['executed_at'])
            self.assertIsNone(row['evidence']['spot_observed_at'])
            self.assertIsNone(row['evidence']['complex_trade'])
            self.assertIsNone(row['evidence']['corrected'])
            self.assertEqual(row['baseline_status'], 'INCOMPLETE')
            self.assertFalse(row['market_proof'])
            self.assertEqual(row['request_provenance']['path'], '/api/option-trades')
            self.assertEqual(row['request_provenance']['params'], dict(limit='20', include_agg_trades='false', min_premium='50000', min_size='500', volume_greater_oi='true', min_dte='1', max_dte='14', is_otm='true'))
            raw['canceled'] = True
            changed = invoke()
            self.assertEqual(changed['observation_revision'], 'CHANGED_OBSERVATION')
            self.assertIn(row['raw_source_hash'], changed['prior_raw_versions'])
            self.assertNotEqual(changed['baseline_status'], 'QUALIFIED')
            with sqlite3.connect(dest) as c:
                saved = [json.loads(r[0]) for r in c.execute('SELECT payload_json FROM realdata_research_records')]
            self.assertEqual(len(saved), 2)
            self.assertEqual(saved[0], row)
