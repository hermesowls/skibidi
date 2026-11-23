"""STEP3 independent finding regressions: actual callers, offline boundary data only."""
import unittest
from unittest.mock import patch
import json
from datetime import datetime, timedelta
from typing import Any
from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
from flow_classifier import FlowClassifierEngine
import test_step3_tracer as fixture


class CallerFixture(unittest.TestCase):
    db: AnalystDatabase
    learner: AnalystStyleLearner
    engine: DualPortfolioEngine
    classifier: FlowClassifierEngine
    clock: datetime
    snapshot: dict[str, Any]
    setUp = fixture.LearningTracer.setUp


class LegacyAvailability(CallerFixture):
    setUp = fixture.LearningTracer.setUp

    def position(self, identity, entry, exit):
        self.db.create_position(identity, 'TEST-analyst', 'TEST', 'TEST', 'option', 'call', 2,
                                strike=100, expiration='2026-10-16')
        self.db.update_position_trim_or_close(identity, 4, 'CLOSED')
        with self.db._get_connection() as c:
            c.execute('UPDATE positions SET entry_time=?,exit_time=? WHERE position_id=?',
                      (entry, exit, identity))

    def test_original_future_legacy_probe(self):
        self.position('TEST-future', '2099-01-01T00:00:00Z', '2099-01-02T00:00:00Z')
        with patch.object(self.learner, '_fetch_cboe_bars', return_value=[]):
            summary = self.learner.analyze_analyst('TEST-analyst')
        self.assertEqual(summary['closed_trades'], 0)

    def test_future_training_cutoff_cannot_invent_creation_time(self):
        with self.assertRaises(ValueError):
            self.learner.analyze_analyst('TEST-analyst', cutoff='2099-01-01T00:00:00Z')

    def test_explicit_cutoff_equality_timezone_and_unknown(self):
        cutoff = '2026-09-20T12:00:00Z'
        cases = [
            ('past', '2026-09-19T12:00:00Z', '2026-09-20T11:00:00Z', cutoff),
            ('equal', '2026-09-20T04:00:00-07:00', '2026-09-20T05:00:00-07:00', cutoff),
            ('future', '2099-01-01T00:00:00Z', '2099-01-02T00:00:00Z', cutoff),
            ('late', '2026-09-19T12:00:00Z', '2026-09-20T11:00:00Z', '2099-01-01T00:00:00Z'),
            ('unknown', '2026-09-19T12:00:00', None, cutoff),
            ('bad', 'bad', 'bad', cutoff),
        ]
        for name, entry, exit, available in cases:
            self.position('TEST-' + name, entry, exit)
            with self.db._get_connection() as c:
                c.execute('UPDATE positions SET updated_at=? WHERE position_id=?', (available, 'TEST-' + name))
        with patch.object(self.learner, '_fetch_cboe_bars', return_value=[]):
            summary = self.learner.analyze_analyst('TEST-analyst', cutoff=cutoff)
        self.assertEqual(summary['closed_trades'], 2)
        self.assertEqual(sum(summary['retained'].values()), 4)
        version = self.db.get_learning_version(summary['rules']['profile_version'])
        self.assertEqual(version['training_cutoff'], cutoff)
        self.assertEqual(set(version['evidence_ids']), {'TEST-past', 'TEST-equal'})
        self.assertEqual(version['dataset_selection']['retained'], summary['retained'])


class ArmCaller(CallerFixture):
    setUp = fixture.LearningTracer.setUp

    def candidate(self: CallerFixture):
        from autonomous_risk_manager import AutonomousRiskManager
        from step1_fixtures import paper_intent
        self.db.save_raw_message('TEST-arm-raw', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST source',
                                 timestamp=(self.clock-timedelta(minutes=1)).isoformat())
        self.db.save_notable_flow(dict(flow_id='TEST-arm-source', raw_message_id='TEST-arm-raw',
            source='TEST-fixture', ticker='TEST', strike=100, call_put='C', expiration='2026-10-16',
            premium_usd=100000, trade_timestamp=(self.clock-timedelta(seconds=30)).isoformat()))
        inputs: dict[str, Any] = dict(ticker='TEST', strike=100, call_put='C', expiration='2026-10-16',
                      dte=27, premium_usd=100000, entry_price=2, spot_price=100, vol_to_oi=3,
                      technical_data={})
        context: dict[str, Any] = dict(decision_id='TEST-arm-decision', source_id='TEST-arm-source',
                       profile_version='TEST-registered-policy', decision_at=self.clock.isoformat(), inputs=inputs)
        intent: dict[str, Any] = paper_intent(dict(flow_id='TEST-arm-source', ticker='TEST', strike=100, call_put='C',
                                  entry_price=2, tp1_price=4, tp2_price=6, stop_loss_price=1), quantity=4)
        intent.update(parent_trace_id=context['decision_id'], policy_version=context['profile_version'])
        manager = AutonomousRiskManager(str(self.db.db_path), quant_engine=False)
        args = {k:v for k,v in inputs.items() if k not in ('vol_to_oi', 'technical_data')}
        args['auto_publish_alerts'] = False
        return manager, args, context, intent

    def test_actual_evaluator_versioned_authorized_simulation_learning_tracer(self):
        from step1_fixtures import lifecycle_evidence
        manager, args, context, intent = self.candidate()
        result = manager.evaluate_candidate_end_to_end(**args, learning_context=context, execution_decision=intent)
        decision = self.classifier.replay_learning_decision(context['decision_id'])
        self.assertEqual(result['learning_decision'], decision)
        self.assertEqual(result['confluence']['profile_version'], context['profile_version'])
        self.assertIsNone(result['confluence']['analyst_edge'])
        self.assertFalse(decision['execution_authorized'])
        self.assertIsNotNone(result['paper_trade'])
        hid = result['paper_trade']['holding_id']
        self.engine.execute_autonomous_trim(hid, 4, trim_pct=.75, **lifecycle_evidence(self.db, hid, 4, 'trim'))
        self.engine.execute_autonomous_exit(hid, 1, **lifecycle_evidence(self.db, hid, 1))
        self.learner.record_economic_correction(dict(correction_id='TEST-arm-cost', holding_id=hid,
            evidence_id='TEST-arm-receipt', observed_at=(self.clock+timedelta(seconds=30)).isoformat(), total_costs=4))
        sample = self.learner.import_paper_outcomes()['samples'][0]
        self.assertEqual((sample['decision_id'],sample['source_id'],sample['policy_version']),
                         (context['decision_id'],context['source_id'],context['profile_version']))
        self.assertEqual(sample['net_pnl'], 496)
        summary = self.learner.summarize_paper_learning('paper_test', (self.clock+timedelta(seconds=60)).isoformat())
        self.assertEqual(summary['resolved_count'], 1)
        with self.db._get_connection() as c:
            analytics = dict(c.execute('SELECT * FROM flow_candidate_analytics').fetchone())
            trace = json.loads(c.execute("SELECT payload_json FROM recorded_strategies WHERE event_type='flow_candidate_evaluation'").fetchone()[0])
        self.assertEqual(analytics['flow_id'], context['source_id'])
        self.assertEqual(trace['decision_id'], context['decision_id'])
        for key in ('intraday_vol','initial_oi','next_day_oi','mfe_pct','mae_pct'):
            self.assertIsNone(analytics[key])
        print('CORRECTED_ARM_TRACER '+json.dumps(dict(decision=decision, sample=sample, summary=summary),sort_keys=True))

    def test_unknown_no_context_does_not_fabricate_metrics(self):
        manager, args, _, _ = self.candidate()
        result = manager.evaluate_candidate_end_to_end(**args)
        self.assertEqual(result['profile_status'], 'legacy_unknown')
        self.assertIsNone(result['quant_snapshot']['conviction_score'])
        self.assertIsNone(result['recommendation']['vol_to_oi'])
        self.assertIsNone(result['paper_trade'])
        deep = result['deep_dive_analysis']
        self.assertIsNone(deep['skew_analysis']['call_put_ratio'])
        self.assertIsNone(deep['synthesis_confidence'])

    def test_missing_execution_evidence_gets_no_favorable_classifier_points(self):
        manager, args, context, _ = self.candidate()
        unknown = manager.evaluate_candidate_end_to_end(**args, learning_context=context)
        known_context = dict(context, decision_id='TEST-known-venue',
                             inputs=dict(context['inputs'], is_sweep=False, execution_venue='MID'))
        known = manager.evaluate_candidate_end_to_end(**args, learning_context=known_context)
        self.assertLess(unknown['recommendation']['conviction_score'], known['recommendation']['conviction_score'])
        self.assertNotIn('sweep on', unknown['learning_decision']['result']['interpretation'])
        self.assertEqual(unknown['learning_decision']['result']['position_intent'], 'Unknown')

    def test_positive_confluence_does_not_require_learned_bonus(self):
        manager, args, context, _ = self.candidate()
        context['inputs'].update(is_sweep=True, execution_venue='ASK', gex_regime='Clear Runway')
        result = manager.evaluate_candidate_end_to_end(**args, learning_context=context)
        self.assertTrue(result['confluence']['is_dream_setup'])
        self.assertIsNone(result['confluence']['analyst_edge'])
        self.assertIsNone(result['paper_trade'])
        self.db.save_learning_version(dict(self.snapshot,version_id='TEST-another-context',classification='proposal'))
        alternate = dict(context,decision_id='TEST-alternate',profile_version='TEST-another-context')
        second = manager.evaluate_candidate_end_to_end(**args, learning_context=alternate)
        self.assertEqual(result['recommendation']['conviction_score'], second['recommendation']['conviction_score'])
        self.assertIsNone(second['paper_trade'])

    def test_real_quant_boundary_evidence_and_no_implicit_execution(self):
        from plugins.analyst_trader.dynamic_shadow_quant import DynamicShadowQuantEngine
        manager, args, context, intent = self.candidate()
        manager.quant_engine = DynamicShadowQuantEngine(str(self.db.db_path))
        # External market data only; real quant/proxy rejection and evaluator run.
        market = dict(price=100, current_price=100, call_put_ratio=0,
                      ta_info={'ema_stack_state':'TEST_OBSERVED_STACK'},
                      event_info={'binary_event_risk':'TEST_PENDING'})
        with patch.object(manager.quant_engine.fetcher, 'fetch_ticker_metrics', return_value=market):
            result = manager.evaluate_candidate_end_to_end(**args, learning_context=context)
        self.assertIsNone(result['paper_trade'])
        self.assertFalse(result['is_dream_setup'])
        self.assertTrue(result['quant_result']['fail_closed_status'])
        self.assertEqual(result['deep_dive_analysis']['skew_analysis']['call_put_ratio'], 0)
        self.assertEqual(result['deep_dive_analysis']['technical_confluence']['ema_stack'], 'TEST_OBSERVED_STACK')
        self.assertEqual(result['learning_decision']['profile_version'], context['profile_version'])

    def test_mismatched_execution_lineage_abstains(self):
        manager, args, context, intent = self.candidate()
        for field, value in [('parent_trace_id','TEST-wrong'),('flow_id','TEST-wrong'),('policy_version','TEST-wrong')]:
            result = manager.evaluate_candidate_end_to_end(**args, learning_context=context,
                                                           execution_decision=dict(intent, **{field:value}))
            self.assertIsNone(result['paper_trade'])
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'), [])

    def test_future_missing_mismatch_and_proposal_cannot_authorize(self):
        manager, args, context, intent = self.candidate()
        self.db.save_learning_version(dict(self.snapshot, version_id='TEST-future', created_at='2099-01-01T00:00:00Z'))
        for bad in (dict(context,profile_version='TEST-future'), dict(context,profile_version='TEST-missing'),
                    dict(context,inputs=dict(context['inputs'],strike=101)), dict(context,source_id='TEST-missing-source')):
            with self.assertRaises(ValueError):
                manager.evaluate_candidate_end_to_end(**args, learning_context=bad, execution_decision=intent)
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'), [])
        self.db.save_learning_version(dict(self.snapshot,version_id='TEST-proposal',classification='proposal'))
        proposed = dict(context,profile_version='TEST-proposal',decision_id='TEST-proposal-decision')
        proposed_intent = dict(intent,policy_version='TEST-proposal',parent_trace_id='TEST-proposal-decision')
        result = manager.evaluate_candidate_end_to_end(**args, learning_context=proposed, execution_decision=proposed_intent)
        self.assertIsNone(result['paper_trade'])
        self.assertFalse(result['learning_decision']['execution_authorized'])
        self.assertIsNone(result['confluence']['analyst_edge'])


class ProvenanceIsolation(CallerFixture):
    setUp = fixture.LearningTracer.setUp
    trade = fixture.LearningTracer.trade

    def test_bad_shapes_do_not_abort_good_holding_and_are_idempotent(self):
        good, _ = self.trade('TEST-good')
        bad, _ = self.trade('TEST-bad-provenance')
        for payload in ('null', '[]', '1', '"string"', '{',
                        '{"source_evidence":null}', '{"source_evidence":[]}',
                        '{"source_evidence":42}', '{"source_evidence":"x"}'):
            with self.subTest(payload=payload):
                with self.db._get_connection() as c:
                    c.execute("UPDATE notable_flow SET source='provider_observed',quant_metrics_json=? WHERE flow_id='TEST-bad-provenance'", (payload,))
                samples = self.learner.import_paper_outcomes()['samples']
                self.assertEqual(next(s for s in samples if s['holding_id']==good)['net_pnl'], 496)
                rejected = next(s for s in samples if s['holding_id']==bad)
                self.assertEqual(rejected['status'], 'rejected')
                self.assertNotEqual(rejected.get('lineage_status'), 'linked')
                self.assertNotEqual(rejected['cohort'], 'paper_observed')
                self.assertEqual(self.learner.import_paper_outcomes()['inserted'], 0)

    def test_sqlite_failure_is_not_converted_to_rejected_sample(self):
        import sqlite3
        self.trade('TEST-db-error')
        with self.db._get_connection() as c:
            c.execute('DROP TABLE learning_corrections')
        with self.assertRaises(sqlite3.OperationalError):
            self.learner.import_paper_outcomes()


class CorrectionPrecedence(CallerFixture):
    setUp = fixture.LearningTracer.setUp
    trade = fixture.LearningTracer.trade

    def correction(self, hid, identity, seconds, **values):
        self.learner.record_economic_correction(dict(correction_id=identity, holding_id=hid,
            evidence_id='receipt:' + identity, observed_at=(self.clock+timedelta(seconds=seconds)).isoformat(), **values))

    def test_older_late_cost_and_price_do_not_override_newer(self):
        hid, _ = self.trade('TEST-precedence')
        self.correction(hid, 'TEST-new', 30, total_costs=100,
                        corrected_event_id='paper-exit:'+hid, corrected_exit_price=2)
        newer = self.learner.import_paper_outcomes()['samples'][0]
        self.correction(hid, 'TEST-old', 10, total_costs=0,
                        corrected_event_id='paper-exit:'+hid, corrected_exit_price=0)
        latest = self.learner.import_paper_outcomes()['samples'][0]
        self.assertEqual(latest['costs'], 100)
        self.assertEqual(latest['gross_pnl'], newer['gross_pnl'])
        self.assertEqual(latest['supersedes'], newer['sample_id'])
        self.assertEqual(self.learner.import_paper_outcomes()['inserted'], 0)
        with self.db._get_connection() as c:
            saved = json.loads(c.execute('SELECT payload_json FROM learning_samples WHERE sample_id=?', (newer['sample_id'],)).fetchone()[0])
        self.assertEqual(saved, newer)
        self.assertEqual(self.learner.summarize_paper_learning('paper_test', (self.clock+timedelta(seconds=60)).isoformat())['net_pnl'], latest['net_pnl'])

    def test_equal_observation_conflicts_abstain_cost_and_price(self):
        for kind in ('cost', 'price'):
            hid, _ = self.trade('TEST-conflict-'+kind)
            for i, value in enumerate((0, 10)):
                values = {'total_costs': value} if kind == 'cost' else {'corrected_exit_price': value, 'corrected_event_id': 'paper-exit:'+hid}
                self.correction(hid, 'TEST-'+kind+str(i), 30, **values)
            sample = next(s for s in self.learner.import_paper_outcomes()['samples'] if s['holding_id']==hid)
            self.assertEqual(sample['status'], 'rejected')
            self.assertIn('Conflicting correction', sample['reason'])

    def test_zero_and_future_cutoff_and_unsupported_supersession(self):
        hid, _ = self.trade('TEST-zero')
        self.correction(hid, 'TEST-zero-cost', 30, total_costs=0)
        self.assertEqual(self.learner.import_paper_outcomes()['samples'][0]['costs'], 0)
        self.assertEqual(self.learner.summarize_paper_learning('paper_test', (self.clock+timedelta(seconds=20)).isoformat())['resolved_count'], 0)
        with self.assertRaisesRegex(ValueError, 'supersession'):
            self.correction(hid, 'TEST-unsupported', 40, total_costs=1, supersedes='TEST-zero-cost')


    def test_price_future_cutoff_and_observed_zero(self):
        hid, _ = self.trade('TEST-price-future')
        self.correction(hid, 'TEST-price-future-correction', 30,
                        corrected_event_id='paper-exit:'+hid, corrected_exit_price=0)
        self.assertEqual(self.learner.summarize_paper_learning('paper_test',
            (self.clock+timedelta(seconds=20)).isoformat())['retained'], {'unavailable_at_cutoff':1})
        sample = self.learner.import_paper_outcomes()['samples'][0]
        self.assertEqual(sample['gross_pnl'], 400)
        self.assertEqual(self.learner.summarize_paper_learning('paper_test',
            (self.clock+timedelta(seconds=60)).isoformat())['resolved_count'], 1)


class SourceRevision(CallerFixture):
    setUp = fixture.LearningTracer.setUp
    trade = fixture.LearningTracer.trade

    def test_changed_current_source_rejected_and_replay_frozen(self):
        for field, value in [('trade_timestamp', '2099-01-01T00:00:00Z'),
                             ('premium_usd', 999999), ('premium_raw', 'changed'),
                             ('vol_to_oi_ratio', 9876), ('is_sweep', 1)]:
            with self.subTest(field=field):
                hid, decision = self.trade('TEST-revision-' + field + str(value))
                before = next(s for s in self.learner.import_paper_outcomes()['samples'] if s['holding_id'] == hid)
                self.assertEqual(before['lineage_status'], 'linked')
                with self.db._get_connection() as c:
                    c.execute('UPDATE notable_flow SET '+field+'=? WHERE flow_id=?', (value, decision['source_id']))
                after = next(s for s in self.learner.import_paper_outcomes()['samples'] if s['holding_id'] == hid)
                self.assertEqual(after['status'], 'rejected')
                self.assertEqual(self.classifier.replay_learning_decision(decision['decision_id']), decision)
                self.assertTrue(decision['source_snapshot_hash'])
                self.assertEqual(decision['raw_source_snapshot']['message_id'], decision['raw_source_id'])
                self.assertEqual(after['supersedes'], before['sample_id'])
        self.assertEqual(self.learner.import_paper_outcomes()['inserted'], 0)

    def test_legacy_snapshot_not_fabricated(self):
        # Append-only imported historical decision predating source snapshots;
        # never edit a committed decision or economic journal.
        manager, args, context, intent = ArmCaller.candidate(self)
        current = self.classifier.record_learning_decision(context['decision_id'],context['source_id'],
            context['profile_version'],context['decision_at'],context['inputs'])
        legacy = {k:v for k,v in current.items() if k not in ('source_snapshot','source_snapshot_hash','raw_source_snapshot')}
        legacy['decision_id'] = 'TEST-legacy-snapshot'
        with self.db._get_connection() as c:
            c.execute('INSERT INTO learning_decisions VALUES (?,?)', (legacy['decision_id'],json.dumps(legacy)))
        intent['parent_trace_id'] = legacy['decision_id']
        result = manager.evaluate_candidate_end_to_end(**args, execution_decision=intent)
        self.assertIsNotNone(result['paper_trade'])
        sample = self.learner.import_paper_outcomes()['samples'][0]
        self.assertEqual(sample['lineage_status'], 'legacy_unknown_source_snapshot')
        self.assertNotIn('source_snapshot', self.classifier.replay_learning_decision(legacy['decision_id']))

    def test_lifecycle_changes_not_source_revision_and_quarantine_overrides(self):
        hid, decision = self.trade('TEST-lifecycle')
        sample = self.learner.import_paper_outcomes()['samples'][0]
        self.assertEqual(sample['lineage_status'], 'linked')
        self.assertEqual(sample['net_pnl'], 496)
        self.assertEqual(decision['source_snapshot']['trade_timestamp'],
                         (self.clock-timedelta(seconds=30+len('TEST-lifecycle'))).isoformat())
        with self.db._get_connection() as c:
            c.execute('UPDATE notable_flow SET is_quarantined=1 WHERE flow_id=?', (decision['source_id'],))
        self.assertEqual(self.learner.import_paper_outcomes()['samples'][0]['status'], 'quarantined')
        self.assertEqual(self.classifier.replay_learning_decision(decision['decision_id']), decision)

