"""TEST-only outcome configuration through public canonical storage/reader."""
import json
from pathlib import Path
import tempfile
import unittest
from plugins.analyst_trader import research_watchlist as rw

class Outcomes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.db = self.root/'TEST/watchlist.sqlite'
        source = self.root/'seed.json'
        source.write_text(json.dumps({'records':[dict(mode='TEST', provider_event_id=str(i), received_at='2026-09-24T16:00:00Z', evidence={'contract_symbol':c}, raw={}, raw_threshold_diagnostics={'failures':[], 'unknown':[]}) for i,c in enumerate(['AAOI260925C00100000','SPY260925C00600000'])]}))
        rw.seed(self.db, source)

    def marks(self):
        bars = [dict(start_time=f'2026-09-24T16:0{i}:00Z', close=p) for i,p in [(1,2),(2,3),(4,4),(5,99)]]
        rw.store_snapshot(self.db, 'AAOI260925C00100000', json.dumps({'data':bars}).encode(), received_at='2026-09-24T16:05:00Z', evidence_cohort='TEST')

    def test_explicit_config_public_reader_complete_pending_and_baseline(self):
        self.marks()
        baseline = rw.read_watchlist(self.db)
        config = dict(version='TEST-horizons-v1', minutes=[1,3,5], metric='close')
        rw.configure_outcomes(self.db, config, received_at='2026-09-24T16:05:00Z', evidence_cohort='TEST')
        result = rw.read_watchlist(self.db)
        self.assertEqual(result['mode'], 'TEST')
        self.assertEqual(result['observations'], baseline['observations'])
        self.assertEqual(result['snapshot_count'], 1)
        outcomes = result['outcome_research']
        self.assertEqual(len(outcomes['candidates']), 2)
        a,b = outcomes['candidates']
        self.assertEqual([x['status'] for x in a['outcomes']], ['COMPLETED','COMPLETED','PENDING'])
        self.assertEqual(a['outcomes'][1]['mark_return_pct'], 100)
        self.assertEqual(a['outcomes'][1]['coverage'], 'GAPPED_OBSERVED_MARKS')
        self.assertEqual(a['outcomes'][0]['mark_return_pct'], 50)
        self.assertTrue(all(x['status']=='PENDING' for x in b['outcomes']))
        self.assertEqual(outcomes['adaptive_ranking']['status'], 'INSUFFICIENT_SAMPLE')
        self.assertEqual(a['priority']['kind'], 'EVIDENCE_COVERAGE_HEURISTIC_NOT_LEARNED_EDGE')
        before = self.db.read_bytes()
        rw.configure_outcomes(self.db, config, received_at='2026-09-24T16:05:00Z', evidence_cohort='TEST')
        self.assertEqual(before, self.db.read_bytes())

    def test_overlap_offsets_conflicts_and_no_lookahead(self):
        self.marks()
        rw.configure_outcomes(self.db, dict(version='TEST-v1', minutes=[1,3,5], metric='close'), received_at='2026-09-24T16:00:00Z', evidence_cohort='TEST')
        def candidate(asof=None):
            return rw.read_watchlist(self.db, outcome_as_of=asof)['outcome_research']['candidates'][0]
        self.assertEqual(candidate('2026-09-24T16:04:59Z')['observed_mark_path']['completed_bars'], 0)
        before = candidate()
        bars = [dict(start_time='2026-09-24T12:01:00-04:00',close=2),dict(start_time='2026-09-24T16:02:00Z',close=3),dict(start_time='2026-09-24T16:04:00Z',close=4)]
        rw.store_snapshot(self.db,'AAOI260925C00100000',json.dumps({'data':bars}).encode(),received_at='2026-09-24T12:05:00-04:00',evidence_cohort='TEST')
        self.assertEqual(candidate()['observed_mark_path']['completed_bars'],before['observed_mark_path']['completed_bars'])
        self.assertEqual(candidate()['outcomes'],before['outcomes'])
        bars[1]['close']=9
        rw.store_snapshot(self.db,'AAOI260925C00100000',json.dumps({'data':bars}).encode(),received_at='2026-09-24T16:06:00Z',evidence_cohort='TEST')
        self.assertEqual(candidate()['outcomes'][0]['status'],'PENDING')
        self.assertEqual(candidate()['observed_mark_path']['conflicting_minutes'],1)
        self.assertEqual(candidate('2026-09-24T16:05:00Z')['outcomes'],before['outcomes'])

    def test_default_unknown_and_config_validation_atomic(self):
        self.marks()
        self.assertTrue(all(c['status']=='UNKNOWN_HORIZON' for c in rw.read_watchlist(self.db)['outcome_research']['candidates']))
        config=dict(version='TEST-v1',minutes=[1],metric='close')
        rw.configure_outcomes(self.db,config,received_at='2026-09-24T16:00:00Z',evidence_cohort='TEST')
        before=self.db.read_bytes()
        for invalid in [dict(config,minutes=[2]),dict(config,minutes=[True]),dict(config,minutes=[]),dict(config,metric='fill'),dict(config,minutes=[2,1])]:
            with self.assertRaises(ValueError):
                rw.configure_outcomes(self.db,invalid,received_at='2026-09-24T16:05:00Z',evidence_cohort='TEST')
            self.assertEqual(before,self.db.read_bytes())

    def test_unrepresentable_horizons_rejected_before_write(self):
        self.marks()
        before = self.db.read_bytes()
        for minutes in [10**20, True, 1.0, float('inf'), '1', None, 0, -1]:
            with self.assertRaises(ValueError):
                rw.configure_outcomes(self.db, dict(version='bad', minutes=[minutes], metric='close'), received_at='2026-09-24T17:00:00Z', evidence_cohort='TEST')
            self.assertEqual(before, self.db.read_bytes())
        for receipt in ['9999-12-31T23:59:00Z', '9999-12-31T23:00:00-01:00']:
            with self.assertRaises(ValueError):
                rw.configure_outcomes(self.db, dict(version='overflow', minutes=[1], metric='close'), received_at=receipt, evidence_cohort='TEST')
            self.assertEqual(before, self.db.read_bytes())

    def test_last_representable_minute_is_accepted(self):
        self.marks()
        out = rw.configure_outcomes(self.db, dict(version='boundary',minutes=[1],metric='close'),
            received_at='9999-12-31T23:58:00Z', evidence_cohort='TEST')
        self.assertEqual(out['outcome_research']['configuration_status'],'CONFIGURED')
        self.assertEqual(out['observation_count'],2)

    def test_invalid_stored_config_retains_candidates_and_can_recover(self):
        self.marks()
        config = dict(version='old-bad', minutes=[10**20], metric='close')
        raw = json.dumps(config).encode()
        summary = dict(id='bad', config=config, received_at='2026-09-24T17:00:00Z')
        with rw.connection(self.db, write=True) as c:
            c.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)', ('bad',None,summary['received_at'],'research-outcome-config',rw.digest(raw),raw,json.dumps(summary)))
        out = rw.read_watchlist(self.db)['outcome_research']
        self.assertEqual(out['configuration_status'], 'INVALID_CONFIGURATION')
        self.assertEqual(len(out['candidates']), 2)
        self.assertTrue(all(x['status']=='INVALID_CONFIGURATION' and not x['outcomes'] for x in out['candidates']))
        rw.configure_outcomes(self.db, dict(version='repaired',minutes=[1],metric='close'), received_at='2026-09-24T18:00:00Z', evidence_cohort='TEST')
        self.assertEqual(rw.read_watchlist(self.db)['outcome_research']['configuration_status'], 'CONFIGURED')

    def test_api_preserves_test_label_and_low_priority_outcomes(self):
        import asyncio
        from unittest.mock import patch
        from hermes_cli import web_server
        self.marks()
        rw.configure_outcomes(self.db,dict(version='TEST-v1',minutes=[1],metric='close'),received_at='2026-09-24T16:00:00Z',evidence_cohort='TEST')
        with patch.object(rw,'canonical_path',return_value=self.db):
            result=asyncio.run(web_server.api_research_watchlist())
        self.assertEqual(result['outcome_research']['evidence_cohort'],'TEST')
        a,b=result['outcome_research']['candidates']
        self.assertEqual(a['priority']['score'],0)
        self.assertEqual(b['priority']['score'],2)
        self.assertEqual(a['outcomes'][0]['status'],'COMPLETED')
        self.assertEqual(result['observation_count'],2)
