"""Independent TEST-only public-path acceptance probes; no provider access."""
import copy,json,sqlite3,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader import research_profiles,realdata_research,realdata_cli
from plugins.analyst_trader.realdata_store import ResearchStore
from test_stage2_uw_schema import trade

class Independent(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.source=self.root/'source.sqlite'
        self.profile=research_profiles.create(AnalystDatabase(self.source),'TEST independent')
        with sqlite3.connect(self.source) as c: c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self.db=ResearchStore(self.root/'research.sqlite',self.source,self.profile['version_id'])
        self.at=datetime.now(timezone.utc)
        self.grant=dict(mode='REAL_DATA_RESEARCH',authorized=True,profile_version=self.profile['version_id'],evidence_cohort='TEST')
    def invoke(self,raw=None,receipt=None,**kw):
        response=dict(status=200,source='TEST_FIXTURE',received_at=(receipt or self.at).isoformat(),body={'data':[raw or trade(self.at)]})
        return realdata_research.run_once(self.db,self.grant,transport=lambda *a,**k:response,now=self.at,**kw)
    def records_absent(self):
        with sqlite3.connect(self.db.path) as c:
            self.assertEqual(c.execute("SELECT name FROM sqlite_master WHERE name='realdata_research_records'").fetchall(),[])
    def test_execution_cannot_follow_receipt_silently(self):
        # Both clocks individually fresh: execution is after receipt, before decision.
        raw=trade(self.at-timedelta(seconds=1))
        try: result=self.invoke(raw,receipt=self.at-timedelta(seconds=2))
        except ValueError: return
        row=result['records'][0]
        print('CHRONOLOGY_REPRO',json.dumps(dict(received_at=row['received_at'],executed_at=row['evidence']['observed_at'],reasons=row['baseline_reasons'])))
        self.assertTrue(any('receipt' in r or 'chronolog' in r or 'observed_at:stale_or_future' in r for r in row['baseline_reasons']), 'Execution after receipt lacks chronology rejection/reason')
    def assert_saved(self, result):
        with sqlite3.connect(self.db.path) as c:
            saved = [json.loads(r[0]) for r in c.execute('SELECT payload_json FROM realdata_research_records')]
        self.assertEqual(saved, result['records'])

    def test_microsecond_after_receipt_retained_invalid_with_good_neighbor(self):
        receipt = self.at-timedelta(seconds=1)
        good = dict(trade(receipt), id='TEST-good')
        bad = dict(trade(receipt+timedelta(microseconds=1)), id='TEST-bad')
        bad.pop('underlying_price')
        response = dict(status=200, source='TEST_FIXTURE', received_at=receipt.isoformat(),
                        body={'data':[bad, good]})
        result = realdata_research.run_once(self.db, self.grant,
            transport=lambda *a, **k: response, now=self.at)
        invalid, valid = result['records']
        self.assertEqual(invalid['observation_status'], 'CHRONOLOGY_INVALID')
        self.assertIn('observed_at:after_receipt', invalid['baseline_reasons'])
        self.assertIn('spot_price:missing_or_invalid', invalid['baseline_reasons'])
        self.assertIn('complex_trade:unknown', invalid['baseline_reasons'])
        self.assertEqual(invalid['baseline_status'], 'INCOMPLETE')
        self.assertEqual(invalid['enhanced_status'], 'UNKNOWN')
        self.assertFalse(invalid['execution_authorized'])
        self.assertFalse(invalid['publication_authorized'])
        self.assertEqual(invalid['raw'], bad)
        self.assertEqual(invalid['evidence']['observed_at'], bad['executed_at'])
        self.assertNotEqual(invalid['evidence']['observed_at'], invalid['received_at'])
        self.assertEqual(valid['observation_status'], 'SCHEMA_VALID')
        self.assertNotIn('observed_at:after_receipt', valid['baseline_reasons'])
        self.assert_saved(result)

    def test_equal_execution_receipt_decision_is_valid(self):
        raw = trade(self.at)
        result = self.invoke(raw)
        row = result['records'][0]
        self.assertEqual(row['observation_status'], 'SCHEMA_VALID')
        self.assertNotIn('observed_at:after_receipt', row['baseline_reasons'])
        self.assertEqual(row['evidence']['observed_at'], raw['executed_at'])
        self.assert_saved(result)

    def test_timezone_equivalent_receipt_compares_instants_preserves_provider(self):
        receipt = self.at.astimezone(timezone(timedelta(hours=-7)))
        raw = trade(self.at)
        raw['executed_at'] = raw['executed_at'].replace('+00:00', 'Z')
        result = self.invoke(raw, receipt=receipt)
        row = result['records'][0]
        self.assertEqual(row['observation_status'], 'SCHEMA_VALID')
        self.assertEqual(row['evidence']['observed_at'], raw['executed_at'])
        self.assertNotIn('observed_at:after_receipt', row['baseline_reasons'])
        self.assert_saved(result)

    def test_stale_future_receipt_rejects_before_table_creation(self):
        for delta in (-10000, 0.000001):
            with self.assertRaisesRegex(ValueError, 'receipt'):
                self.invoke(receipt=self.at+timedelta(seconds=delta))
            self.records_absent()

    def test_stale_future_execution_visible_and_future_receipt_no_write(self):
        for delta in (-10000,1):
            row=self.invoke(trade(self.at+timedelta(seconds=delta)))['records'][0]
            self.assertIn('observed_at:stale_or_future',row['baseline_reasons'])
        with self.assertRaisesRegex(ValueError,'receipt'): self.invoke(receipt=self.at+timedelta(seconds=1))
    def test_invalid_bounds_no_research_table(self):
        for kw in ({'timeout_seconds':float('inf')},{'timeout_seconds':float('nan')},{'timeout_seconds':True},{'max_rows':False}):
            with self.assertRaises(ValueError): self.invoke(**kw)
        self.records_absent()
    def test_elapsed_transport_budget_rejects_before_writes(self):
        import time
        calls=[]
        def slow(*args,**kw):
            calls.append(1); time.sleep(.02)
            return dict(status=200,source='TEST_FIXTURE',received_at=self.at.isoformat(),body={'data':[]})
        with self.assertRaisesRegex(ValueError,'deadline'):
            realdata_research.run_once(self.db,self.grant,transport=slow,now=self.at,timeout_seconds=.005)
        self.assertEqual(calls,[1]); self.records_absent()
    def test_profile_hash_tamper_rejected_before_transport(self):
        self.db.profile=copy.deepcopy(self.db.profile)
        self.db.profile['profile']['kian_research']['min_premium']=1
        with self.assertRaises(ValueError): self.invoke()
        self.records_absent()
    def test_cli_missing_grant_has_no_destination_side_effect(self):
        dest=self.root/'never.sqlite'
        with self.assertRaises(SystemExit):
            realdata_cli.main(['--profile-db',str(self.source),'--profile-version',self.profile['version_id'],'--research-db',str(dest),'--test-response',str(self.root/'no.json')])
        self.assertFalse(dest.exists())
    def test_research_grant_is_not_publication_or_execution_authority(self):
        before=self.source.read_bytes()
        row=self.invoke()['records'][0]
        self.assertIs(row['publication_authorized'],False); self.assertIs(row['execution_authorized'],False)
        self.assertEqual(row['mode'],'TEST'); self.assertEqual(self.source.read_bytes(),before)
        with sqlite3.connect(self.db.path) as c:
            self.assertEqual({r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")},{'research_store_identity','realdata_research_records'})
