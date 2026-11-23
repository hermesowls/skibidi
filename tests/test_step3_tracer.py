"""Persisted TEST tracer. All inference inputs deterministic; real business callers."""
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
from flow_classifier import FlowClassifierEngine
from step1_fixtures import paper_intent, lifecycle_evidence

class LearningTracer(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.db=AnalystDatabase(Path(self.tmp.name)/'TEST.db')
  self.learner=AnalystStyleLearner(self.db); self.engine=DualPortfolioEngine(self.db)
  self.classifier=FlowClassifierEngine(str(self.db.db_path))
  self.clock=datetime.now(timezone.utc)
  self.snapshot=dict(version_id='TEST-registered-policy',schema_version=1,code_identity='TEST-policy-code',config_identity='TEST-policy-config',training_cutoff=(self.clock-timedelta(days=2)).isoformat(),created_at=(self.clock-timedelta(days=1)).isoformat(),source_mode='paper_test',evidence_ids=[],uncertainty=['TEST deterministic stated policy, not learned edge'],classification='stated_policy',profile={'rules':{},'summary':'TEST only'})
  self.db.save_learning_version(self.snapshot)

 def trade(self,name='TEST-tracer',right='P',trim_pct=.75,close=True,costs=True):
  raw='TEST-raw:'+name
  self.db.save_raw_message(raw,'TEST-channel','TEST-channel','TEST-analyst','TEST-author','TEST deterministic option source, not provider history',timestamp=(self.clock-timedelta(minutes=1)).isoformat())
  self.db.save_notable_flow(dict(flow_id=name,raw_message_id=raw,source='TEST-fixture',ticker='TEST',strike=100,call_put=right,expiration='2026-10-16',premium_usd=100000,trade_timestamp=(self.clock-timedelta(seconds=30+len(name))).isoformat()))
  self.assertTrue(callable(getattr(self.classifier,'record_learning_decision',None)),'missing persisted decision caller')
  inputs=dict(ticker='TEST',strike=100,call_put=right,expiration='2026-10-16',dte=27,premium_usd=100000,entry_price=2,spot_price=100,vol_to_oi=0,technical_data={})
  decision=self.classifier.record_learning_decision('TEST-decision:'+name,name,'TEST-registered-policy',self.clock.isoformat(),inputs)
  intent=paper_intent(dict(flow_id=name,ticker='TEST',strike=100,call_put=right,entry_price=2,tp1_price=4,tp2_price=6,stop_loss_price=1),quantity=4)
  intent.update(parent_trace_id=decision['decision_id'],policy_version=decision['profile_version'])
  entry=self.engine.execute_autonomous_trade(intent); assert entry
  hid=entry['holding_id']
  self.engine.execute_autonomous_trim(hid,4,trim_pct=trim_pct,**lifecycle_evidence(self.db,hid,4,'trim'))
  if close: self.engine.execute_autonomous_exit(hid,1,**lifecycle_evidence(self.db,hid,1))
  if costs: self.learner.record_economic_correction(dict(correction_id='TEST-cost:'+name,holding_id=hid,evidence_id='TEST-fees:'+name,observed_at=(self.clock+timedelta(seconds=5)).isoformat(),total_costs=4))
  return hid,decision

 def test_proposal_creation_not_backdated_to_historical_cutoff(self):
  before=datetime.now(timezone.utc)
  summary=self.learner.summarize_paper_learning('paper_test','2026-01-01T00:00:00Z')
  proposal=self.db.get_learning_version(summary['proposed_version'])
  self.assertGreaterEqual(datetime.fromisoformat(proposal['created_at']),before)
  with self.assertRaises(ValueError): self.db.get_learning_version(summary['proposed_version'],decision_at='2026-01-02T00:00:00Z')

 def test_persisted_version_survives_correction_and_rejects_raw_mismatch(self):
  hid,decision=self.trade()
  cutoff=(self.clock+timedelta(seconds=10)).isoformat()
  summary=self.learner.summarize_paper_learning('paper_test',cutoff)
  original=self.db.get_learning_version(summary['proposed_version'])
  self.learner.record_economic_correction(dict(correction_id='TEST-revised-cost',holding_id=hid,evidence_id='TEST-cost2',observed_at=(self.clock+timedelta(seconds=20)).isoformat(),total_costs=8))
  self.assertEqual(self.learner.summarize_paper_learning('paper_test',cutoff)['retained']['unavailable_at_cutoff'],1)
  self.assertEqual(self.db.get_learning_version(summary['proposed_version']),original)
  self.assertEqual(self.classifier.replay_learning_decision(decision['decision_id']),decision)
  with self.db._get_connection() as c:
   c.execute("UPDATE raw_messages SET content='TEST changed source' WHERE message_id=?",(decision['raw_source_id'],))
  sample=self.learner.import_paper_outcomes()['samples'][0]
  self.assertEqual(sample['status'],'rejected')
  self.assertIn('lineage mismatch',sample['reason'])

 def test_replay_conflict_and_future_raw_rejected(self):
  _,decision=self.trade()
  inputs=dict(decision['inputs'],call_put='C')
  with self.assertRaises(ValueError): self.classifier.record_learning_decision('TEST-new',decision['source_id'],decision['profile_version'],decision['decision_at'],inputs)
  with self.assertRaises(ValueError): self.classifier.record_learning_decision(decision['decision_id'],decision['source_id'],decision['profile_version'],decision['decision_at'],inputs)
  with self.db._get_connection() as c:
   c.execute("UPDATE notable_flow SET final_outcome='MONITORING'")
   c.execute("UPDATE raw_messages SET timestamp='2099-01-01T00:00:00Z'")
  with self.assertRaises(ValueError): self.classifier.record_learning_decision('TEST-future-raw',decision['source_id'],decision['profile_version'],decision['decision_at'],decision['inputs'])

 def test_complete_tracer_profit_despite_runner_loss_replay_future_profile(self):
  hid,decision=self.trade()
  first=self.learner.import_paper_outcomes()
  sample=first['samples'][0]
  self.assertEqual(sample['lineage_status'],'linked')
  self.assertEqual(sample['outcome'],'WIN')
  self.assertEqual(sample['net_pnl'],496)
  self.assertEqual(sample['net_return_pct'],62)
  self.assertEqual(sample['source_outcome'],'LOSS_STOP_HIT')
  self.assertEqual(self.learner.import_paper_outcomes()['inserted'],0)
  summary=self.learner.summarize_paper_learning('paper_test',(self.clock+timedelta(seconds=10)).isoformat())
  self.assertEqual((summary['resolved_count'],summary['wins'],summary['losses']),(1,1,0))
  self.assertEqual(summary['net_pnl'],496)
  version=self.db.get_learning_version(summary['proposed_version'])
  self.assertEqual(version['evidence_ids'],[sample['sample_id']])
  self.assertEqual(version['classification'],'proposal')
  self.db.save_learning_version(dict(self.snapshot,version_id='TEST-future',created_at='2099-01-01T00:00:00Z'))
  replay=self.classifier.replay_learning_decision(decision['decision_id'])
  self.assertEqual(replay,decision)
  self.assertEqual(replay['profile_version'],'TEST-registered-policy')
  print('TEST_TRACER '+json.dumps({'source_id':sample['source_id'],'decision_id':sample['decision_id'],'holding_id':hid,'outcome_id':sample['outcome_id'],'policy_version':sample['policy_version'],'evidence_ids':sample['evidence_ids'],'summary':summary},sort_keys=True))

 def test_loss_partial_costs_unknown_quarantine_correction_and_missing_lineage(self):
  hid,decision=self.trade(trim_pct=.25)
  loss=self.learner.import_paper_outcomes()['samples'][0]
  self.assertEqual(loss['net_pnl'],-104)
  partial,_=self.trade('TEST-partial',right='C',close=False)
  unknown,_=self.trade('TEST-cost-unknown',right='C',costs=False)
  cutoff=(self.clock+timedelta(seconds=10)).isoformat()
  summary=self.learner.summarize_paper_learning('paper_test',cutoff)
  self.assertEqual((summary['resolved_count'],summary['losses']),(1,1))
  self.assertEqual(summary['retained']['partial'],1)
  self.assertEqual(summary['retained']['costs_unobserved'],1)
  self.learner.record_economic_correction(dict(correction_id='TEST-price-correction',holding_id=hid,evidence_id='TEST-price-observation',observed_at=(self.clock+timedelta(seconds=6)).isoformat(),corrected_event_id='paper-exit:'+hid,corrected_exit_price=2))
  revised=next(s for s in self.learner.import_paper_outcomes()['samples'] if s['holding_id']==hid)
  self.assertEqual(revised['supersedes'],loss['sample_id'])
  self.assertEqual(revised['net_pnl'],196)
  self.assertEqual(self.db.get_portfolio_holding(hid)['realized_pnl'],-100)
  with self.db._get_connection() as c: c.execute("UPDATE notable_flow SET is_quarantined=1 WHERE flow_id='TEST-tracer'")
  summary=self.learner.summarize_paper_learning('paper_test',cutoff)
  self.assertEqual(summary['resolved_count'],0)
  self.assertEqual(summary['retained']['quarantined'],1)
  with self.assertRaises(ValueError): self.classifier.record_learning_decision('TEST-bad','TEST-partial','missing-version',self.clock.isoformat(),{})
  self.assertEqual(self.learner.summarize_paper_learning('paper_observed',cutoff)['resolved_count'],0)
