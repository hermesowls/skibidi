"""TEST-only fixtures: no provider, messaging, broker or production data."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plugins.analyst_trader.db import AnalystDatabase
from flow_ingestion_engine import FlowIngestionEngine

class ClusterTests(unittest.TestCase):
    def test_cluster_excludes_parent_and_analytics_quarantine(self):
        from datetime import datetime, timezone
        from whale_filter_criteria import WhaleFilterEngine
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
            for name,flag in [('valid',0),('parent',1),('linked',0)]:
                db.save_notable_flow({'flow_id':'TEST-'+name,'ticker':'TEST','strike':100,'call_put':'C','expiration':'2026-10-16','premium_usd':250000,'trade_timestamp':datetime.now(timezone.utc).isoformat(),'is_quarantined':flag})
            db.save_flow_candidate_analytics({'analytics_id':'TEST-analytics','flow_id':'TEST-linked','ticker':'TEST'})
            with db._get_connection() as conn:
                conn.execute("UPDATE flow_candidate_analytics SET is_quarantined=1 WHERE analytics_id='TEST-analytics'")
            count,premium,rows=WhaleFilterEngine(str(path)).check_multi_whale_cluster_memory('TEST')
            self.assertEqual((count,premium),(1,250000))
            self.assertEqual([r['flow_id'] for r in rows],['TEST-valid'])

class PriceUpdaterTests(unittest.TestCase):
    def test_long_put_mark_uses_premium_return_through_real_updater(self):
        from plugins.analyst_trader.price_updater import UnusualWhalesPriceUpdater
        with tempfile.TemporaryDirectory() as tmp:
            db=AnalystDatabase(Path(tmp)/'TEST.db')
            db.create_position('TEST-put','TEST-analyst','TEST-channel','TEST','option','put',2,strike=100,expiration='2026-10-16')
            updater=UnusualWhalesPriceUpdater(db, offline=True)
            with patch.object(updater,'fetch_unusual_whales_contracts_for_ticker',return_value=[{'option_symbol':'TEST261016P00100000','last_price':3}]):
                result=updater.update_open_positions_mark_to_market(force=True)
            self.assertEqual(result['positions_updated'],1)
            position = db.get_position('TEST-put'); assert position is not None
            self.assertEqual(position['roi_pct'],50)
            self.assertEqual(updater.fetch_unusual_whales_contracts_for_ticker('TEST'),[])
            self.assertIsNone(updater.fetch_alpaca_stock_price('TEST'))

    def test_contract_match_requires_full_identity_and_finite_price(self):
        from plugins.analyst_trader.price_updater import UnusualWhalesPriceUpdater
        with tempfile.TemporaryDirectory() as tmp:
            updater=UnusualWhalesPriceUpdater(AnalystDatabase(Path(tmp)/'TEST.db'), offline=True)
            bad=['OTHER261016P00100000','TEST271016P00100000','TEST261016C00100000','TEST261016P00100001']
            for symbol in bad:
                self.assertIsNone(updater.find_contract_price([{'option_symbol':symbol,'last_price':3}],'TEST',100,'put','2026-10-16'))
            for price in (True,float('nan'),float('inf'),-1,0):
                self.assertIsNone(updater.find_contract_price([{'option_symbol':'TEST261016P00100000','last_price':price}],'TEST',100,'put','2026-10-16'))
            self.assertIsNone(updater.find_contract_price([{'option_symbol':'TEST261016P00100000','last_price':3}],'TEST',100,'put',None))

class JournalTests(unittest.TestCase):
    def test_concurrent_replay_and_insert_failure_do_not_ack_missing_events(self):
        from concurrent.futures import ThreadPoolExecutor
        from plugins.analyst_trader.strategy_logger import log_event
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
            payload={'trace_id':'TEST-concurrent','ticker':'TEST','correlation_id':'TEST-flow','policy_version':'TEST-v1'}
            with ThreadPoolExecutor(max_workers=4) as pool:
                receipts=list(pool.map(lambda _:log_event('TEST-event',payload,db_path=str(path)),range(4)))
            self.assertEqual(receipts,['TEST-concurrent']*4)
            self.assertEqual(len(db.list_recorded_strategies()),1)
            with db._get_connection() as conn:
                conn.execute("CREATE TRIGGER TEST_journal_fault BEFORE INSERT ON recorded_strategies BEGIN SELECT RAISE(ABORT,'TEST-injected'); END")
            self.assertIsNone(log_event('TEST-event',dict(payload,trace_id='TEST-fault'),db_path=str(path)))
            self.assertEqual(len(db.list_recorded_strategies()),1)

    def test_explicit_id_replay_is_one_receipt_and_conflict_is_not_acknowledged(self):
        from plugins.analyst_trader.strategy_logger import log_event
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
            payload={'trace_id':'TEST-event','ticker':'TEST','policy_version':'TEST-v1','parent_trace_id':'TEST-decision'}
            self.assertEqual(log_event('TEST-entry',payload,db_path=str(path)),'TEST-event')
            self.assertEqual(log_event('TEST-entry',payload,db_path=str(path)),'TEST-event')
            self.assertIsNone(log_event('TEST-conflict',dict(payload,ticker='OTHER'),db_path=str(path)))
            self.assertEqual(len(db.list_recorded_strategies()),1)

class EconomicLineageTests(unittest.TestCase):
    def test_unequal_tranches_preserve_economic_return_for_learner_accessor(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AnalystDatabase(Path(tmp)/'TEST.db')
            db.create_position('TEST-position','TEST-analyst','TEST-channel','TEST','option','put',2,strike=100,expiration='2026-10-16')
            db.update_position_trim_or_close('TEST-position',4,'TRIMMED',0.25,exit_message_id='TEST-trim')
            db.update_position_trim_or_close('TEST-position',1,'CLOSED',exit_message_id='TEST-close')
            stored=db.get_position('TEST-position'); assert stored is not None
            listed=db.list_positions(analyst_name='TEST-analyst',status='CLOSED')[0]
            self.assertEqual(stored['realized_pnl'],-25)
            self.assertEqual(listed['roi_pct'],stored['roi_pct'])
            self.assertEqual(listed['roi_pct'],-12.5)
            self.assertEqual([t['quantity'] for t in listed['trims']],[0.25,0.75])
            self.assertEqual(listed['weighted_exit_price'],1.75)

class IsolationTests(unittest.TestCase):
    def test_empty_profile_does_not_discover_checkout_secrets(self):
        import os
        import discord_poster
        import flow_ingestion_engine
        with patch.dict(os.environ):
            os.environ.pop('DISCORD_BOT_TOKEN',None)
            self.assertEqual(discord_poster.get_discord_token(),'')
            self.assertEqual(flow_ingestion_engine.get_discord_token(),'')

class TruthfulScannerTests(unittest.TestCase):
    def test_unavailable_scanners_do_not_insert_provider_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AnalystDatabase(Path(tmp)/'TEST.db')
            engine = FlowIngestionEngine(db)
            with patch('flow_ingestion_engine.download_and_cache_chart', return_value=None):
                flowseeker = engine.ingest_flowseeker_scanner_feeds()
                whales = engine.ingest_unusual_whales_feeds()
            with db._get_connection() as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM notable_flow').fetchone()[0], 0)
            self.assertEqual(flowseeker['status'], 'unavailable')
            self.assertEqual(whales['status'], 'unavailable')

class CorrelationTests(unittest.TestCase):
    def test_resolved_loss_win_zero_and_partial_denominators(self):
        from candidate_correlation_engine import CandidateCorrelationEngine
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
            for name,outcome in [('winner','WIN_TP2'),('loser','STOP_LOSS'),('partial','WIN_TP1'),('censored','CENSORED')]:
                db.save_notable_flow({'flow_id':'TEST-'+name,'ticker':'TEST','strike':150,'call_put':'C','expiration':'2026-10-16','premium_usd':250000,'final_outcome':outcome,'trade_timestamp':'TEST-'+name})
            with db._get_connection() as conn:
                # STEP3: zero is observed only with explicit TEST contract/session evidence;
                # the original bare-number fixture could not establish OI provenance.
                import json
                oi = {'source':'TEST-observed','contract':{'ticker':'TEST','strike':150,'call_put':'C','expiration':'2026-10-16'},
                      'session':'2026-09-17','next_session':'2026-09-18','session_evidence_id':'TEST-calendar',
                      'next_open_at':'2026-09-18T13:30:00Z',
                      'initial':{'value':0,'session':'2026-09-17','available_at':'2026-09-17T13:30:00Z','evidence_id':'TEST-oi-1'},
                      'next':{'value':0,'session':'2026-09-18','available_at':'2026-09-18T13:30:00Z','evidence_id':'TEST-oi-2'}}
                # TEST-only provider observations, never manufactured by production.
                oi['initial']['observed_at']='2026-09-17T13:30:00Z'
                oi['next']['observed_at']='2026-09-18T13:30:00Z'
                for index, (name,outcome) in enumerate([('winner','WIN_TP2'),('loser','STOP_LOSS'),('partial','WIN_TP1'),('censored','CENSORED')]):
                    oi['flow_id']='TEST-'+name; oi['session_timezone']='America/New_York'
                    measured={'source_id':'TEST-'+name,'status':'observed','evidence_id':'TEST-measured-'+name,
                              'label':outcome,'observed_at':'2026-09-18T20:00:00Z','contract':oi['contract']}
                    conn.execute('UPDATE notable_flow SET initial_oi=0,next_day_oi=0,mfe_max_gain_pct=0,mae_max_drawdown_pct=0,quant_metrics_json=?,trade_timestamp=? WHERE flow_id=?',
                                 (json.dumps({'oi_evidence':oi,'outcome_evidence':measured}),f'2026-09-17T15:00:0{index}Z','TEST-'+name))
            result=CandidateCorrelationEngine(str(path)).run_candidate_correlation_audit()
            self.assertEqual((result['resolved_candidates'],result['unresolved_candidates'],result['overall_win_rate_pct']),(2,2,50))
            with db._get_connection() as conn:
                self.assertTrue(all(tuple(r)==(0,0,0) for r in conn.execute('SELECT initial_oi,next_day_oi,mfe_pct FROM flow_candidate_analytics')))

    def test_legacy_schema_accepts_unknown_without_losing_existing_evidence(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST-legacy.db'; db=AnalystDatabase(path)
            with sqlite3.connect(path) as conn:
                sql=conn.execute("SELECT sql FROM sqlite_master WHERE name='flow_candidate_analytics'").fetchone()[0]
                conn.execute('DROP TABLE flow_candidate_analytics')
                conn.execute(sql.replace('entry_price REAL,','entry_price REAL NOT NULL,'))
                conn.execute("INSERT INTO flow_candidate_analytics(analytics_id,flow_id,ticker,flow_tier,entry_price,outcome_label,created_at,updated_at) VALUES ('TEST-existing','TEST-flow','TEST','TEST',2,'MONITORING','TEST','TEST')")
            db=AnalystDatabase(path)
            db.save_flow_candidate_analytics({'analytics_id':'TEST-new','flow_id':'TEST-flow','ticker':'TEST','entry_price':None})
            with db._get_connection() as conn:
                rows=conn.execute('SELECT analytics_id,entry_price FROM flow_candidate_analytics ORDER BY analytics_id').fetchall()
                self.assertEqual([tuple(r) for r in rows],[('TEST-existing',2),('TEST-new',None)])

    def test_unknown_is_not_a_loss_or_a_quote(self):
        from candidate_correlation_engine import CandidateCorrelationEngine
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path); db.init_db()
            db.save_notable_flow({'flow_id':'TEST-unknown','ticker':'TEST','strike':150,'call_put':'C','expiration':'2026-10-16','premium_usd':250000})
            result=CandidateCorrelationEngine(str(path)).run_candidate_correlation_audit()
            self.assertEqual(result['total_stops'],0)
            self.assertIsNone(result['overall_win_rate_pct'])
            self.assertEqual(result['resolved_candidates'],0)
            with db._get_connection() as conn:
                row=dict(conn.execute('SELECT * FROM flow_candidate_analytics').fetchone())
                for field in ('entry_price','mfe_pct','mae_pct','initial_oi','next_day_oi'):
                    self.assertIsNone(row[field],field)
                self.assertIsNone(conn.execute('SELECT mfe_max_gain_pct FROM notable_flow').fetchone()[0])

class QuarantineTests(unittest.TestCase):
    def test_linked_quarantine_excludes_both_list_consumers(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AnalystDatabase(Path(tmp)/'TEST.db')
            for name in ('parent','child'):
                db.save_notable_flow({'flow_id':'TEST-'+name,'ticker':'TEST','strike':100,'call_put':'C','expiration':'2026-10-16','premium_usd':250000,'trade_timestamp':name})
                db.save_flow_candidate_analytics({'flow_id':'TEST-'+name,'ticker':'TEST'})
            with db._get_connection() as conn:
                conn.execute("UPDATE notable_flow SET is_quarantined=1 WHERE flow_id='TEST-parent'")
                conn.execute("UPDATE flow_candidate_analytics SET is_quarantined=1 WHERE flow_id='TEST-child'")
            self.assertEqual(db.get_notable_flow(consolidate_duplicates=False),[])
            self.assertEqual(db.list_flow_candidate_analytics(),[])

    def test_legacy_readonly_all_fixture_ids_and_two_batch_revert(self):
        import sqlite3
        import hashlib
        from scripts.quarantine_synthetic_data import quarantine_data, KNOWN_SCANNER_FIXTURES
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST-legacy.db'
            with sqlite3.connect(path) as conn:
                conn.execute('CREATE TABLE notable_flow(flow_id TEXT PRIMARY KEY, source TEXT, trade_timestamp TEXT, raw_message_id TEXT, strike REAL, expiration TEXT)')
                for flow_id,(source,stamp) in KNOWN_SCANNER_FIXTURES.items():
                    conn.execute('INSERT INTO notable_flow VALUES (?,?,?,NULL,100,?)',(flow_id,source,stamp,'2026-10-16'))
                conn.execute("INSERT INTO notable_flow VALUES ('TEST-valid','unusual_whales','TEST','TEST-message',100,'2026-10-16')")
            before=path.read_bytes()
            self.assertEqual(quarantine_data(path)['notable_flow_to_quarantine'],5)
            self.assertEqual(path.read_bytes(),before)
            batch1=quarantine_data(path,apply=True)['batch_id']
            with sqlite3.connect(path) as conn:
                conn.execute('CREATE TABLE flow_candidate_analytics(analytics_id TEXT PRIMARY KEY,flow_id TEXT,correlations_json TEXT,mfe_pct REAL,outcome_label TEXT)')
                conn.execute("INSERT INTO flow_candidate_analytics VALUES ('TEST-synthetic','TEST-valid',?,35,'WIN_TP1')", ('{"evidence_kind":"synthetic","evidence_id":"TEST-reviewed-generator"}',))
                conn.execute("INSERT INTO flow_candidate_analytics VALUES ('TEST-observed','TEST-other','{}',220,'WIN_TP2')")
            batch2=quarantine_data(path,apply=True)['batch_id']
            quarantine_data(path,apply=True,revert=True,batch_id=batch1)
            with sqlite3.connect(path) as conn:
                self.assertEqual(conn.execute("SELECT is_quarantined,quarantine_batch_id FROM notable_flow WHERE flow_id='TEST-valid'").fetchone(),(1,batch2))
                self.assertIsNone(conn.execute("SELECT is_quarantined FROM flow_candidate_analytics WHERE analytics_id='TEST-observed'").fetchone()[0])
                with self.assertRaises(sqlite3.IntegrityError): conn.execute('DELETE FROM quarantine_audit')
            with self.assertRaises(ValueError): quarantine_data(path,revert=True,batch_id="' OR 1=1 --")
            quarantine_data(path,apply=True,revert=True,batch_id=batch2)
            quarantine_data(path,apply=True,revert=True,batch_id=batch2)

    def test_reingestion_cannot_clear_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AnalystDatabase(Path(tmp)/'TEST.db')
            flow={'flow_id':'TEST-q','ticker':'TEST','strike':100,'call_put':'C','expiration':'2026-10-16','premium_usd':250000,
                  'is_quarantined':1,'quarantine_reason':'TEST-reviewed','quarantine_batch_id':'TEST-batch'}
            db.save_notable_flow(flow)
            db.save_notable_flow(dict(flow,is_quarantined=0,quarantine_reason='replacement',quarantine_batch_id='replacement'))
            row=db.get_notable_flow_by_id('TEST-q')
            assert row is not None
            self.assertEqual((row['is_quarantined'],row['quarantine_reason'],row['quarantine_batch_id']),(1,'TEST-reviewed','TEST-batch'))

    def test_provenance_scoped_readonly_apply_and_revert(self):
        import hashlib
        from scripts.quarantine_synthetic_data import quarantine_data
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.db'
            db=AnalystDatabase(path); db.init_db()
            valid={'flow_id':'TEST-valid','ticker':'TEST','strike':100,'call_put':'C',
                   'expiration':'2026-10-16','premium_usd':250000,
                   'source':'discord_notable_flow','raw_message_id':'TEST-observed'}
            db.save_notable_flow(valid)
            historical=dict(valid,flow_id='flow_flowseeker_NVDA_20261016_230C',ticker='NVDA',strike=230,
                            source='skylit_flowseeker',raw_message_id=None,
                            trade_timestamp='2026-08-24T19:42:00.000000+00:00')
            db.save_notable_flow(historical)
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            dry=quarantine_data(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
            self.assertEqual(dry['notable_flow_to_quarantine'],1)
            batch=quarantine_data(path,apply=True)['batch_id']
            self.assertFalse(db.get_notable_flow_by_id('TEST-valid')['is_quarantined'])
            self.assertEqual(db.get_notable_flow_by_id(historical['flow_id'])['is_quarantined'],1)
            with self.assertRaises(ValueError): quarantine_data(path,apply=True,revert=True)
            quarantine_data(path,apply=True,revert=True,batch_id=batch)
            quarantine_data(path,apply=True,revert=True,batch_id=batch)
            self.assertFalse(db.get_notable_flow_by_id(historical['flow_id'])['is_quarantined'])
            with db._get_connection() as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM quarantine_audit').fetchone()[0],2)

