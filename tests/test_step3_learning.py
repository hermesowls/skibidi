"""STEP3 TEST fixtures only. Never invoke providers or operational runners."""
import tempfile
import json
from typing import Any
import unittest
from unittest.mock import patch
from pathlib import Path
from datetime import datetime, timezone
from plugins.analyst_trader.db import AnalystDatabase

class EligibilityTests(unittest.TestCase):
 def test_analytics_replay_cannot_reparent_quarantined_evidence(self):
  with tempfile.TemporaryDirectory() as tmp:
   db=AnalystDatabase(Path(tmp)/'TEST.db')
   db.save_flow_candidate_analytics(dict(analytics_id='TEST-a',flow_id='TEST-original',ticker='TEST'))
   with db._get_connection() as c: c.execute('UPDATE flow_candidate_analytics SET is_quarantined=1')
   with self.assertRaises(ValueError): db.save_flow_candidate_analytics(dict(analytics_id='TEST-a',flow_id='TEST-new',ticker='TEST',is_quarantined=0))
   row=db._get_connection().execute('SELECT flow_id,is_quarantined FROM flow_candidate_analytics').fetchone()
   self.assertEqual(tuple(row),('TEST-original',1))

 def test_expected_outcome_label_is_not_measured_performance(self):
  from candidate_correlation_engine import CandidateCorrelationEngine
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
   db.save_notable_flow(dict(flow_id='TEST-label',ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',premium_usd=100000,final_outcome='WIN_TP2'))
   result=CandidateCorrelationEngine(str(path)).run_candidate_correlation_audit()
   self.assertEqual(result['resolved_candidates'],0)
   self.assertIsNone(result['overall_win_rate_pct'])

 def test_ingestion_observed_zero_not_replaced_by_other_quote(self):
  from flow_ingestion_engine import FlowIngestionEngine
  with tempfile.TemporaryDirectory() as tmp:
   db=AnalystDatabase(Path(tmp)/'TEST.db')
   engine=FlowIngestionEngine(db,chart_loader=lambda **kw:None,discord_token='',quant_engine=False,deep_dive_analyzer=False,observation_reader=lambda parsed,msg:{'entry_price':0,'contract_price':5})
   with patch('plugins.analyst_trader.finviz_fetcher.FinvizFetcher.fetch_ticker_metrics',return_value={}):
    self.assertTrue(engine._process_message(dict(id='TEST-zero',content='TEST 100 C 10/16/2026 $1M',timestamp='2026-09-19T00:00:00Z'),'TEST-channel','TEST','equity'))
   row=db.get_notable_flow_by_id('flow_TEST-zero'); assert row
   self.assertEqual(row['entry_contract_price'],0)

 def test_whale_missing_oi_does_not_receive_fabricated_aggression(self):
  from whale_filter_criteria import WhaleFilterEngine
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'TEST.db'; AnalystDatabase(path); whale=WhaleFilterEngine(str(path))
   kw: dict[str,Any]=dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',dte=30,premium_usd=100000,is_sweep=True)
   with patch.object(whale.fetcher,'fetch_ticker_metrics',return_value={}):
    missing=whale.evaluate_whale_candidate(**kw)
    zero=whale.evaluate_whale_candidate(**kw,vol_to_oi=0)
   self.assertLess(missing['flow_score'],zero['flow_score'])

 def test_learner_excludes_linked_quarantine_and_retains_unknown(self):
  from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
  with tempfile.TemporaryDirectory() as tmp:
   db=AnalystDatabase(Path(tmp)/'TEST.db')
   for name in ('linked','unknown'):
    db.create_position('TEST-'+name,'TEST-analyst','TEST-channel','TEST','option','put',2,strike=100,expiration='2026-10-16',entry_message_id='TEST-raw-'+name)
    db.update_position_trim_or_close('TEST-'+name,3,'CLOSED')
   db.save_notable_flow(dict(flow_id='TEST-linked',raw_message_id='TEST-raw-linked',ticker='TEST',strike=100,call_put='P',expiration='2026-10-16',premium_usd=100000))
   db.save_flow_candidate_analytics(dict(flow_id='TEST-linked',ticker='TEST'))
   with db._get_connection() as c:
    c.execute('UPDATE flow_candidate_analytics SET is_quarantined=1')
    c.execute("UPDATE positions SET realized_pnl=NULL,roi_pct=NULL WHERE position_id='TEST-unknown'")
   learner=AnalystStyleLearner(db)
   with patch.object(learner,'_fetch_cboe_bars',return_value=[]): result=learner.analyze_analyst('TEST-analyst')
   self.assertEqual(result['closed_trades'],0)
   self.assertEqual(result['retained'],{'quarantined':1,'unknown_outcome':1})
   self.assertIsNone(result['win_rate'])


 def test_linked_quarantine_excluded_by_oi_and_classifier(self):
  from premarket_oi_auditor import PremarketOIAuditor
  from flow_classifier import FlowClassifierEngine
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
   db.save_notable_flow({'flow_id':'TEST-linked','ticker':'TEST','trade_timestamp':datetime.now(timezone.utc).isoformat(),'strike':100,'call_put':'C','expiration':'2026-10-16','premium_usd':100000})
   db.save_flow_candidate_analytics({'flow_id':'TEST-linked','analytics_id':'TEST-a','ticker':'TEST'})
   with db._get_connection() as c: c.execute("UPDATE flow_candidate_analytics SET is_quarantined=1")
   self.assertEqual(PremarketOIAuditor(str(path)).run_premarket_oi_audit()['total_audited'],0)
   self.assertEqual(FlowClassifierEngine(str(path)).score_all_db_notable_flows(False),[])

 def test_oi_numbers_without_contract_session_provenance_abstain(self):
  from premarket_oi_auditor import PremarketOIAuditor
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
   db.save_notable_flow({'flow_id':'TEST-oi','ticker':'TEST','strike':100,'call_put':'C','expiration':'2026-10-16','premium_usd':100000,'trade_timestamp':datetime.now(timezone.utc).isoformat(),'initial_oi':0,'next_day_oi':0})
   with db._get_connection() as conn:
    conn.execute('UPDATE notable_flow SET initial_oi=0,next_day_oi=0')
   stats=PremarketOIAuditor(str(path)).run_premarket_oi_audit()
   row=dict(db._get_connection().execute('SELECT * FROM notable_flow').fetchone())
   self.assertIsNone(row['oi_delta'])
   self.assertEqual((row['initial_oi'],row['next_day_oi']),(0,0))
   self.assertEqual(stats['unobserved'],1)

 def test_classifier_missing_oi_is_unknown_not_synthetic_sweep_ratio(self):
  from flow_classifier import FlowClassifierEngine
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'TEST.db'; AnalystDatabase(path)
   c=FlowClassifierEngine(str(path))
   kw: dict[str, Any]=dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',dte=30,premium_usd=100000,technical_data={})
   missing=c.classify_and_score_flow(**kw)
   zero=c.classify_and_score_flow(**kw,vol_to_oi=0)
   self.assertIsNone(missing['size_to_oi'])
   self.assertEqual(zero['size_to_oi'],0)
   self.assertLess(missing['conviction_score'],zero['conviction_score'])

 def test_oi_exact_session_evidence_and_zero_through_auditor(self):
  from premarket_oi_auditor import PremarketOIAuditor
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
   flow={'flow_id':'TEST-session','ticker':'TEST','strike':100,'call_put':'P','expiration':'2026-10-16','premium_usd':100000,'trade_timestamp':datetime.now(timezone.utc).isoformat()}
   db.save_notable_flow(flow)
   ev={'source':'TEST-observed','contract':{'ticker':'TEST','strike':100,'call_put':'P','expiration':'2026-10-16'},'session':'2026-09-17','next_session':'2026-09-18','session_evidence_id':'TEST-calendar','next_open_at':'2026-09-18T13:30:00Z','initial':{'value':0,'session':'2026-09-17','available_at':'2026-09-17T13:30:00Z','evidence_id':'TEST-oi-1'},'next':{'value':0,'session':'2026-09-18','available_at':'2026-09-18T13:30:00Z','evidence_id':'TEST-oi-2'}}
   # TEST-only provider observations, not inferred in production from receipt.
   ev['initial']['observed_at']='2026-09-17T13:30:00Z'
   ev['next']['observed_at']='2026-09-18T13:30:00Z'
   ev['flow_id']='TEST-session'
   ev['session_timezone']='America/New_York'
   with db._get_connection() as c:
    c.execute("UPDATE notable_flow SET trade_timestamp='2026-09-17T15:00:00Z'")
   for mode in ('valid','missing_session','wrong_contract','future','wrong_flow','wrong_session','preopen'):
    e=json.loads(json.dumps(ev))
    if mode=='missing_session': e.pop('session_evidence_id')
    if mode=='wrong_contract': e['contract']['call_put']='C'
    if mode=='future': e['next']['available_at']='2099-01-01T00:00:00Z'
    if mode=='wrong_flow': e['flow_id']='TEST-other'
    if mode=='wrong_session': e['session']='2026-09-16'; e['initial']['session']='2026-09-16'
    with db._get_connection() as c:
     c.execute('UPDATE notable_flow SET initial_oi=0,next_day_oi=0,quant_metrics_json=?',(json.dumps({'oi_evidence':e}),))
    PremarketOIAuditor(str(path)).run_premarket_oi_audit(as_of='2026-09-18T13:29:00Z' if mode=='preopen' else '2026-09-19T00:00:00Z')
    row=db._get_connection().execute('SELECT oi_delta,is_carried_over FROM notable_flow').fetchone()
    self.assertEqual(tuple(row),(0,None) if mode=='valid' else (None,None))

class PointInTimeTests(unittest.TestCase):
 def test_actual_learner_bar_order_duplicates_availability_and_horizon(self):
  from datetime import timedelta
  from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
  with tempfile.TemporaryDirectory() as tmp:
   learner=AnalystStyleLearner(AnalystDatabase(Path(tmp)/'TEST.db'))
   start=datetime(2025,1,1,tzinfo=timezone.utc)
   bars=[{'date':(start+timedelta(days=i)).date().isoformat(),'available_at':(start+timedelta(days=i,hours=22)).isoformat(),'close':100+i,'volume':100} for i in range(260)]
   for data,valid in ((bars,True),(bars[::-1],True),(bars+bars,True),(bars[:5],False),(bars[:199]+[dict(bars[199],close=float('nan'))],False),([dict(b,available_at='2099-01-01T00:00:00Z') for b in bars],False),([dict(b,date='2026-09-19') for b in bars],False)):
    with patch.object(learner,'_fetch_cboe_bars',return_value=data):
     result=learner._get_ta_at_date('TEST','2026-09-19T14:00:00-04:00')
    if valid:
     self.assertIsNotNone(result['ema200'])
     self.assertTrue(result['is_above_200_ema'])
    else:
     self.assertIsNone(result.get('ema200'))
     self.assertIsNone(result['is_above_200_ema'])
     self.assertIsNone(result.get('ta_bullish_pass'))

 def test_unknown_ta_not_put_alignment_or_call_penalty(self):
  from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
  from plugins.analyst_trader.technical_indicators import TechnicalIndicatorsEngine
  from flow_classifier import FlowClassifierEngine
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'TEST.db'; db=AnalystDatabase(path)
   db.create_position('TEST-put','TEST-analyst','TEST-channel','TEST','option','put',2,strike=100,expiration='2026-10-16')
   db.update_position_trim_or_close('TEST-put',3,'CLOSED')
   with db._get_connection() as c:
    c.execute("UPDATE positions SET entry_time='2026-01-01T00:00:00Z',exit_time='2026-01-02T00:00:00Z',updated_at='2026-01-02T00:00:00Z'")
   learner=AnalystStyleLearner(db)
   with patch.object(learner,'_fetch_cboe_bars',return_value=[]): result=learner.analyze_analyst('TEST-analyst')
   self.assertIsNone(result['rules']['ta_requirements']['below_200_win_rate_pct'])
   ta=TechnicalIndicatorsEngine().compute_technical_indicators([1])
   self.assertIsNone(ta['ta_pass'])
   kw: dict[str,Any]=dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',dte=5,premium_usd=100000,vol_to_oi=0)
   c=FlowClassifierEngine(str(path))
   a=c.classify_and_score_flow(**kw,technical_data={})
   b=c.classify_and_score_flow(**kw,technical_data=ta)
   self.assertEqual(a['conviction_score'],b['conviction_score'])

class EconomicImportTests(unittest.TestCase):
 def setUp(self):
  from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.db=AnalystDatabase(Path(self.tmp.name)/'TEST.db'); self.engine=DualPortfolioEngine(self.db)

 def holding(self, name='TEST-economic', right='P', trim=True, close=True):
  from step1_fixtures import paper_intent, persist_source, lifecycle_evidence
  intent=paper_intent(dict(flow_id=name,ticker='TEST',strike=100,call_put=right,entry_price=2,tp1_price=4,tp2_price=6,stop_loss_price=1),quantity=4)
  persist_source(self.db,intent)
  entry=self.engine.execute_autonomous_trade(intent); assert entry
  hid=entry['holding_id']
  if trim: self.engine.execute_autonomous_trim(hid,4,trim_pct=.25,**lifecycle_evidence(self.db,hid,4,'trim'))
  if close: self.engine.execute_autonomous_exit(hid,1,**lifecycle_evidence(self.db,hid,1))
  return hid

 def test_legacy_unregistered_policy_synthetic_cohort_and_reversion(self):
  from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
  hid=self.holding(); learner=AnalystStyleLearner(self.db)
  with self.db._get_connection() as c: c.execute("UPDATE notable_flow SET is_quarantined=0")
  first=learner.import_paper_outcomes()['samples'][0]
  self.assertEqual(first['lineage_status'],'legacy_unknown')
  with self.db._get_connection() as c: c.execute("UPDATE notable_flow SET is_quarantined=1")
  quarantined=learner.import_paper_outcomes()['samples'][0]
  with self.db._get_connection() as c: c.execute("UPDATE notable_flow SET is_quarantined=0")
  restored=learner.import_paper_outcomes()['samples'][0]
  self.assertEqual(restored['supersedes'],quarantined['sample_id'])
  self.assertNotEqual(first['sample_id'],restored['sample_id'])
  with self.db._get_connection() as c: c.execute("UPDATE notable_flow SET source='synthetic_demo'")
  synthetic=learner.import_paper_outcomes()['samples'][0]
  self.assertNotEqual(synthetic['cohort'],'paper_observed')

 def test_import_actual_unequal_tranches_cost_unknown_and_idempotent(self):
  from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
  hid=self.holding()
  learner=AnalystStyleLearner(self.db)
  self.assertTrue(callable(getattr(learner,'import_paper_outcomes',None)),'missing economic importer')
  result=learner.import_paper_outcomes()
  sample=result['samples'][0]
  self.assertEqual(sample['holding_id'],hid)
  self.assertEqual(sample['gross_pnl'],-100)
  self.assertEqual(sample['basis'],800)
  self.assertEqual(sample['gross_return_pct'],-12.5)
  self.assertIsNone(sample['net_pnl'])
  self.assertEqual(sample['cohort'],'paper_test')
  self.assertEqual(learner.import_paper_outcomes()['inserted'],0)

 def test_partial_retained_correction_invalidates_exact_sample_and_loss_kept(self):
  from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
  learner=AnalystStyleLearner(self.db); hid=self.holding()
  self.assertTrue(callable(getattr(learner,'import_paper_outcomes',None)))
  first=learner.import_paper_outcomes()['samples'][0]
  correction={'correction_id':'TEST-cost','holding_id':hid,'evidence_id':'TEST-cost-receipt','observed_at':datetime.now(timezone.utc).isoformat(),'total_costs':4}
  learner.record_economic_correction(correction)
  after=learner.import_paper_outcomes()['samples'][0]
  self.assertEqual(after['supersedes'],first['sample_id'])
  self.assertEqual(after['net_pnl'],-104)
  self.assertEqual(after['outcome'],'LOSS')
  self.assertEqual(after['net_return_pct'],-13)
  learner.record_economic_correction(correction)
  self.assertEqual(learner.import_paper_outcomes()['inserted'],0)
  partial=self.holding('TEST-partial',right='C',close=False)
  samples=learner.import_paper_outcomes()['samples']
  self.assertEqual(next(s for s in samples if s['holding_id']==partial)['status'],'partial')
  with self.db._get_connection() as c: c.execute("UPDATE notable_flow SET is_quarantined=1 WHERE flow_id='TEST-economic'")
  samples=learner.import_paper_outcomes()['samples']
  self.assertEqual(next(s for s in samples if s['holding_id']==hid)['status'],'quarantined')

class VersionTests(unittest.TestCase):
 def test_temp_legacy_migration_preserves_data_and_is_repeatable(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'TEST-legacy.db'; db=AnalystDatabase(path)
   db.save_raw_message('TEST-legacy','TEST','TEST','TEST','TEST','TEST legacy payload')
   with db._get_connection() as c:
    before=tuple(c.execute('SELECT * FROM raw_messages').fetchone())
    for table in ('learning_decisions','learning_samples','learning_corrections','learning_versions'):
     c.execute('DROP TABLE '+table)
   for _ in range(2):
    migrated=AnalystDatabase(path)
    with migrated._get_connection() as c:
     self.assertEqual(tuple(c.execute('SELECT * FROM raw_messages').fetchone()),before)
     for table in ('learning_decisions','learning_samples','learning_corrections','learning_versions'):
      self.assertEqual(c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)

 def test_unknown_duration_not_default_one_day(self):
  from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
  with tempfile.TemporaryDirectory() as tmp:
   db=AnalystDatabase(Path(tmp)/'TEST.db')
   db.create_position('TEST-duration','TEST-analyst','TEST','TEST','option','call',2,strike=100,expiration='2026-10-16')
   db.update_position_trim_or_close('TEST-duration',3,'CLOSED')
   with db._get_connection() as c: c.execute("UPDATE positions SET entry_time='unknown'")
   learner=AnalystStyleLearner(db)
   with patch.object(learner,'_fetch_cboe_bars',return_value=[]): result=learner.analyze_analyst('TEST-analyst')
   self.assertIsNone(result['rules']['avg_holding_hours'])

 def test_arm_does_not_promote_mutable_legacy_style(self):
  from autonomous_risk_manager import AutonomousRiskManager
  with tempfile.TemporaryDirectory() as tmp:
   db=AnalystDatabase(Path(tmp)/'TEST.db')
   db.save_analyst_style('TEST',['TEST'],1,100,50,14,60,'TEST',{},total_trades=5)
   manager=AutonomousRiskManager(str(db.db_path),quant_engine=False,deep_dive_analyzer=False)
   result=manager.validate_dream_setup_confluence(90,30,2,True,ticker='TEST')
   self.assertIsNone(result['analyst_edge'])
   self.assertEqual(result['profile_status'],'legacy_unknown')
   snapshot=dict(version_id='TEST-arm',schema_version=1,code_identity='TEST-code',config_identity='TEST-config',training_cutoff='2026-09-17T00:00:00Z',created_at='2026-09-18T00:00:00Z',source_mode='paper_test',evidence_ids=[],uncertainty=['unvalidated'],classification='proposal',profile={'summary':'TEST descriptive'})
   db.save_learning_version(snapshot)
   result=manager.validate_dream_setup_confluence(90,30,2,True,ticker='TEST',profile_version='TEST-arm',decision_at='2026-09-19T00:00:00Z')
   self.assertEqual(result['profile_snapshot']['profile']['summary'],'TEST descriptive')
   self.assertIsNone(result['analyst_edge'])


 def test_immutable_profile_conflict_and_classifier_recorded_version(self):
  from flow_classifier import FlowClassifierEngine
  with tempfile.TemporaryDirectory() as tmp:
   db=AnalystDatabase(Path(tmp)/'TEST.db')
   self.assertTrue(callable(getattr(db,'save_learning_version',None)),'missing version store')
   snapshot=dict(version_id='TEST-v1',schema_version=1,code_identity='TEST-code',config_identity='TEST-config',training_cutoff='2026-09-17T00:00:00Z',created_at='2026-09-18T00:00:00Z',source_mode='paper_test',evidence_ids=[],uncertainty=['unvalidated'],classification='proposal',profile={'analyst_name':'TEST','win_rate':100,'total_trades':5,'preferred_tickers':['TEST']})
   db.save_learning_version(snapshot)
   db.save_learning_version(snapshot)
   with self.assertRaisesRegex(ValueError,'CONFLICT'): db.save_learning_version(dict(snapshot,profile={'win_rate':0}))
   db.save_learning_version(dict(snapshot,version_id='TEST-future',created_at='2099-01-01T00:00:00Z'))
   c=FlowClassifierEngine(str(db.db_path))
   kw: dict[str,Any]=dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',dte=30,premium_usd=100000,technical_data={})
   result=c.classify_and_score_flow(**kw,profile_version='TEST-v1',decision_at='2026-09-19T00:00:00Z')
   replay=c.classify_and_score_flow(**kw,profile_version='TEST-v1',decision_at='2026-09-19T00:00:00Z')
   self.assertEqual(result,replay)
   self.assertEqual(result['profile_version'],'TEST-v1')
   self.assertNotIn('ANALYST EDGE',result['flow_tags_str'])
   self.assertIsNone(c.classify_and_score_flow(**kw)['profile_version'])
   with self.assertRaises(ValueError): c.classify_and_score_flow(**kw,profile_version='TEST-future',decision_at='2026-09-19T00:00:00Z')

 def test_one_win_and_five_wins_are_descriptive_not_philosophy(self):
  from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
  with tempfile.TemporaryDirectory() as tmp:
   db=AnalystDatabase(Path(tmp)/'TEST.db'); learner=AnalystStyleLearner(db)
   for i in range(5):
    db.create_position('TEST-'+str(i),'ab','TEST-channel','TEST','option','put',2,strike=100,expiration='2026-10-16')
    db.update_position_trim_or_close('TEST-'+str(i),3,'CLOSED')
    with db._get_connection() as c:
     c.execute("UPDATE positions SET entry_time='2026-01-01T00:00:00Z',exit_time='2026-01-02T00:00:00Z',updated_at='2026-01-02T00:00:00Z'")
    with patch.object(learner,'_fetch_cboe_bars',return_value=[]): result=learner.analyze_analyst('ab')
    self.assertEqual(result['closed_trades'],i+1)
    self.assertEqual(result['rules'].get('classification'),'exploratory_unvalidated')
    self.assertEqual(result['rules']['high_conviction_setups'],[])
    self.assertEqual(result['rules']['validated_rules'],[])
    self.assertNotIn('risk-free',result['strategy_summary'])
    self.assertNotIn('Edge:',result['strategy_summary'])
    self.assertTrue(result['profile_version'])
