"""Caller-driven deadline invariants on actual producer-authorized TEST holdings."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch
from test_step5_kian_repair import ProducerContext


class Deadline(unittest.TestCase):
    def producer(self, probe, seconds=10):
        ProducerContext().run_producers(True, execute=True, max_hold_seconds=seconds,
                                       lifecycle_probe=probe)

    def origin(self, db, hid):
        with db._get_connection() as c:
            row=c.execute("SELECT payload_json FROM recorded_strategies WHERE holding_id=? AND event_type='autonomous_trade_executed'",(hid,)).fetchone()
        origin=json.loads(row[0])
        return origin, json.loads(origin['intent_json'])['intent']

    def quote(self, db, hid, price, offset: float=10, name='deadline') -> dict[str, Any]:
        origin,intent=self.origin(db,hid)
        at=datetime.fromisoformat(intent['research_lifecycle']['entered_at'])+timedelta(seconds=offset)
        return dict(quote=dict(intent['quote'], holding_id=hid, quote_id='TEST-'+name,
                               observed_at=at.isoformat(),bid=price,ask=price), now=at,max_age=60)

    def test_exact_deadline_neutral_quote_closes_once(self):
        def probe(db,hid,result):
            from plugins.analyst_trader.paper_monitor import process_quote
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            engine=DualPortfolioEngine(db)
            evidence=self.quote(db,hid,2.)
            update=process_quote(db,engine,hid,**evidence)
            self.assertEqual(update['operation'],'exit')
            self.assertEqual(update['outcome'],'CLOSED_MAX_HOLD')
            self.assertIsNotNone(update['economic_receipt'])
            self.assertIsNone(process_quote(db,DualPortfolioEngine(db),hid,**evidence))
            with db._get_connection() as c:
                h=dict(c.execute('SELECT * FROM portfolio_holdings WHERE holding_id=?',(hid,)).fetchone())
                self.assertEqual((h['status'],h['quantity'],h['realized_pnl']),('CLOSED',0,0))
                self.assertEqual(c.execute('SELECT final_outcome FROM notable_flow WHERE flow_id=?',(h['flow_id'],)).fetchone()[0],'CLOSED_MAX_HOLD')
        self.producer(probe)

    def test_gain_loss_partial_deadline_economics_and_learning(self):
        from plugins.analyst_trader.paper_monitor import process_quote
        from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
        from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
        for price,partial,gross in ((3.,False,400.),(1.5,False,-200.),(2.5,True,650.)):
            with self.subTest(price=price,partial=partial):
                def probe(db,hid,result):
                    engine=DualPortfolioEngine(db)
                    if partial:
                        engine.execute_autonomous_trim(hid,4.,trim_pct=.75,**self.quote(db,hid,4.,offset=1,name='trim'))
                    update=process_quote(db,engine,hid,**self.quote(db,hid,price))
                    self.assertEqual(update['outcome'],'CLOSED_MAX_HOLD')
                    self.assertEqual(update['economic_receipt']['quantity'],1 if partial else 4)
                    learner=AnalystStyleLearner(db)
                    uncosted=learner.import_paper_outcomes()['samples'][0]
                    self.assertEqual(uncosted['gross_pnl'],gross)
                    self.assertIsNone(uncosted['net_pnl'])
                    self.assertIsNone(uncosted['outcome'])
                    self.assertEqual(uncosted['source_outcome'],'CLOSED_MAX_HOLD')
                    self.assertEqual(uncosted['cohort'],'paper_test')
                    self.assertEqual(uncosted['lineage_status'],'linked')
                    learner.record_economic_correction(dict(correction_id='TEST-deadline-cost',holding_id=hid,
                        evidence_id='TEST-observed-cost',observed_at=self.quote(db,hid,price,offset=11)['now'].isoformat(),total_costs=4))
                    sample=learner.import_paper_outcomes()['samples'][0]
                    self.assertEqual(sample['gross_pnl'],gross)
                    self.assertEqual(sample['net_pnl'],gross-4)
                    self.assertEqual(sample['outcome'],'WIN' if gross>0 else 'LOSS')
                    self.assertEqual(sample['decision_id'],result['learning_decision']['decision_id'])
                    self.assertEqual(learner.import_paper_outcomes()['inserted'],0)
                self.producer(probe)

    def test_actual_manager_pending_then_close_and_direct_replay(self):
        def probe(db,hid,result):
            from autonomous_risk_manager import AutonomousRiskManager
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            evidence=self.quote(db,hid,3.)
            manager=AutonomousRiskManager(str(db.db_path),quote_reader=lambda h:None,
                quote_max_age_seconds=60,clock=lambda:evidence['now'])
            pending=manager.monitor_and_update_positions()
            self.assertEqual(len(pending),1)
            self.assertEqual(pending[0]['exit_status'],'EXIT_PENDING')
            self.assertIsNone(pending[0]['economic_receipt'])
            manager.quote_reader=lambda h:evidence['quote']
            update=manager.monitor_and_update_positions()[0]
            self.assertEqual(update['outcome'],'CLOSED_MAX_HOLD')
            restarted=AutonomousRiskManager(str(db.db_path),quote_reader=manager.quote_reader,
                quote_max_age_seconds=60,clock=lambda:evidence['now'])
            self.assertEqual(restarted.monitor_and_update_positions(),[])
            self.assertEqual(DualPortfolioEngine(db).execute_autonomous_exit(hid,3.,
                outcome_label='CLOSED_MAX_HOLD',**evidence),update['economic_receipt'])
        self.producer(probe)

    def test_direct_deadline_exit_requires_quote_and_rejects_wrong_label(self):
        def probe(db,hid,result):
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            engine=DualPortfolioEngine(db)
            evidence=self.quote(db,hid,3.)
            with self.assertRaises(ValueError):
                engine.execute_autonomous_exit(hid,3.,**dict(evidence,quote=None))
            with self.assertRaises(ValueError):
                engine.execute_autonomous_exit(hid,3.,outcome_label='WIN_TP2',**evidence)
            receipt=engine.execute_autonomous_exit(hid,3.,outcome_label='CLOSED_MAX_HOLD',**evidence)
            assert receipt is not None
            self.assertEqual(receipt['quantity'],4)
            self.assertEqual(receipt['realized_pnl'],400)
            self.assertEqual(DualPortfolioEngine(db).execute_autonomous_exit(hid,3.,**evidence),receipt)
        self.producer(probe)

    def test_before_exact_boundary_and_stop_time_target_priority(self):
        from plugins.analyst_trader.paper_monitor import process_quote
        from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
        for price,label in ((1.,'LOSS_STOP_HIT'),(4.,'CLOSED_MAX_HOLD'),(6.,'CLOSED_MAX_HOLD')):
            with self.subTest(price=price):
                def probe(db,hid,result):
                    engine=DualPortfolioEngine(db)
                    before=process_quote(db,engine,hid,**self.quote(db,hid,2.,offset=9.999,name='before'))
                    self.assertIsNone(before['operation'])
                    update=process_quote(db,engine,hid,**self.quote(db,hid,price))
                    self.assertEqual(update['outcome'],label)
                    self.assertEqual(update['economic_receipt']['quantity'],4)
                self.producer(probe)

    def test_concurrent_restart_and_atomic_journal_failure(self):
        def probe(db,hid,result):
            import sqlite3
            from concurrent.futures import ThreadPoolExecutor
            from plugins.analyst_trader.paper_monitor import process_quote
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            evidence=self.quote(db,hid,3.)
            def snapshot():
                with db._get_connection() as c:
                    return {table:[tuple(row) for row in c.execute('SELECT * FROM '+table+' ORDER BY rowid')]
                            for table in ('portfolio_holdings','portfolios','notable_flow','recorded_strategies')}
            before=snapshot()
            with db._get_connection() as c:
                c.execute("CREATE TRIGGER TEST_fail_deadline BEFORE INSERT ON recorded_strategies WHEN NEW.event_type='paper_monitor_outcome' BEGIN SELECT RAISE(ABORT,'TEST journal failure'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                process_quote(db,DualPortfolioEngine(db),hid,**evidence)
            self.assertEqual(snapshot(),before,'Every economic/source/journal row must roll back')
            with db._get_connection() as c:
                h=dict(c.execute('SELECT * FROM portfolio_holdings WHERE holding_id=?',(hid,)).fetchone())
                self.assertEqual((h['status'],h['quantity'],h['realized_pnl']),('OPEN',4,0))
                self.assertEqual(c.execute("SELECT count(*) FROM recorded_strategies WHERE event_type='autonomous_trade_closed'").fetchone()[0],0)
                self.assertEqual(c.execute('SELECT final_outcome FROM notable_flow WHERE flow_id=?',(h['flow_id'],)).fetchone()[0],'MONITORING')
                c.execute('DROP TRIGGER TEST_fail_deadline')
            with ThreadPoolExecutor(max_workers=2) as pool:
                updates=list(pool.map(lambda _:process_quote(db,DualPortfolioEngine(db),hid,**evidence),range(2)))
            self.assertEqual(sum(u is not None for u in updates),1)
            self.assertIsNone(process_quote(db,DualPortfolioEngine(db),hid,**evidence))
            with db._get_connection() as c:
                self.assertEqual(c.execute("SELECT count(*) FROM recorded_strategies WHERE event_type='autonomous_trade_closed'").fetchone()[0],1)
                self.assertEqual(c.execute("SELECT realized_pnl FROM portfolios WHERE portfolio_id='autonomous_ai'").fetchone()[0],400)
        self.producer(probe)

    def test_changed_source_or_removed_lifecycle_cannot_bypass_deadline(self):
        for corrupt in ('raw','lifecycle'):
            with self.subTest(corrupt=corrupt):
                def probe(db,hid,result):
                    from plugins.analyst_trader.paper_monitor import process_quote
                    from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
                    evidence=self.quote(db,hid,3.)
                    origin,intent=self.origin(db,hid)
                    with db._get_connection() as c:
                        if corrupt=='raw':
                            c.execute('UPDATE raw_messages SET content=?',('TEST corrupt source',))
                        else:
                            intent.pop('research_lifecycle')
                            origin['intent_json']=json.dumps(dict(intent=intent))
                            c.execute("UPDATE recorded_strategies SET payload_json=? WHERE holding_id=? AND event_type='autonomous_trade_executed'",(json.dumps(origin),hid))
                    update=process_quote(db,DualPortfolioEngine(db),hid,**evidence)
                    self.assertIsNotNone(update)
                    self.assertIsNone(update['economic_receipt'])
                    self.assertIn(update['exit_status'],('EXIT_PENDING','INVALID_DEADLINE'))
                    with db._get_connection() as c:
                        self.assertEqual(c.execute('SELECT status FROM portfolio_holdings WHERE holding_id=?',(hid,)).fetchone()[0],'OPEN')
                self.producer(probe)

    def test_removing_lifecycle_and_changing_nested_decision_cannot_look_legacy(self):
        def probe(db,hid,result):
            from plugins.analyst_trader.paper_monitor import process_quote
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            evidence=self.quote(db,hid,3.)
            origin,intent=self.origin(db,hid)
            intent.pop('research_lifecycle')
            intent['parent_trace_id']='TEST-missing-decision'
            origin['parent_trace_id']='TEST-missing-decision'
            origin['intent_json']=json.dumps(dict(intent=intent))
            with db._get_connection() as c:
                c.execute("UPDATE recorded_strategies SET payload_json=? WHERE holding_id=? AND event_type='autonomous_trade_executed'",(json.dumps(origin),hid))
            update=process_quote(db,DualPortfolioEngine(db),hid,**evidence)
            self.assertEqual(update.get('exit_status'),'INVALID_DEADLINE')
            self.assertIsNone(update['economic_receipt'])
            with db._get_connection() as c:
                self.assertEqual(c.execute('SELECT status FROM portfolio_holdings WHERE holding_id=?',(hid,)).fetchone()[0],'OPEN')
        self.producer(probe)

    def test_registered_policy_is_immutable_and_nested_extension_is_rejected(self):
        def probe(db,hid,result):
            import sqlite3
            from plugins.analyst_trader.paper_monitor import process_quote
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            origin,intent=self.origin(db,hid)
            evidence=self.quote(db,hid,3.)
            for table in ('learning_versions','learning_decisions'):
                with self.subTest(table=table), db._get_connection() as c:
                    with self.assertRaises(sqlite3.IntegrityError):
                        c.execute('DELETE FROM '+table)
            changed=json.loads(json.dumps(intent))
            changed['research_lifecycle']['max_hold_seconds']=1000
            changed['research_lifecycle']['exit_deadline']=(
                datetime.fromisoformat(changed['research_lifecycle']['entered_at'])+timedelta(seconds=1000)).isoformat()
            payload=dict(origin,intent_json=json.dumps(dict(intent=changed)))
            with db._get_connection() as c:
                c.execute("UPDATE recorded_strategies SET payload_json=? WHERE holding_id=? AND event_type='autonomous_trade_executed'",(json.dumps(payload),hid))
            update=process_quote(db,DualPortfolioEngine(db),hid,**evidence)
            self.assertEqual(update['exit_status'],'INVALID_DEADLINE')
            self.assertIsNone(update['economic_receipt'])
            with db._get_connection() as c:
                c.execute("UPDATE recorded_strategies SET payload_json=? WHERE holding_id=? AND event_type='autonomous_trade_executed'",(json.dumps(origin),hid))
            stale=self.quote(db,hid,3.,offset=11)
            stale.update(now=stale['now']+timedelta(seconds=61),max_age=10000)
            pending=process_quote(db,DualPortfolioEngine(db),hid,**stale)
            self.assertEqual(pending['exit_status'],'EXIT_PENDING')
            self.assertIsNone(pending['economic_receipt'])
            self.assertEqual(process_quote(db,DualPortfolioEngine(db),hid,**evidence)['outcome'],'CLOSED_MAX_HOLD')
        self.producer(probe)

    def test_deadline_corruption_is_visible_fail_closed(self):
        def probe(db,hid,result):
            from plugins.analyst_trader.paper_monitor import process_quote
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            origin,intent=self.origin(db,hid)
            evidence=self.quote(db,hid,2.,offset=11)
            for bad in ('2099-01-01T00:00:00+00:00','malformed','2026-09-23T00:00:00'):
                with self.subTest(deadline=bad):
                    altered=json.loads(json.dumps(intent))
                    altered['research_lifecycle']['exit_deadline']=bad
                    payload=dict(origin,intent_json=json.dumps(dict(intent=altered)))
                    with db._get_connection() as c:
                        c.execute("UPDATE recorded_strategies SET payload_json=? WHERE holding_id=? AND event_type='autonomous_trade_executed'",(json.dumps(payload),hid))
                    update=process_quote(db,DualPortfolioEngine(db),hid,**evidence)
                    self.assertEqual(update['exit_status'],'INVALID_DEADLINE')
                    self.assertIsNone(update['economic_receipt'])
            with db._get_connection() as c:
                c.execute("UPDATE recorded_strategies SET payload_json=? WHERE holding_id=? AND event_type='autonomous_trade_executed'",(json.dumps(origin),hid))
                self.assertEqual(c.execute('SELECT status FROM portfolio_holdings WHERE holding_id=?',(hid,)).fetchone()[0],'OPEN')
        self.producer(probe)

    def test_predeadline_quote_cannot_fill_overdue_time_exit(self):
        def probe(db,hid,result):
            from plugins.analyst_trader.paper_monitor import process_quote
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            evidence=self.quote(db,hid,2.,offset=9)
            evidence['now']+=timedelta(seconds=2)
            update=process_quote(db,DualPortfolioEngine(db),hid,**evidence)
            self.assertEqual(update['exit_status'],'EXIT_PENDING')
            self.assertIsNone(update['economic_receipt'])
        self.producer(probe)

    def test_missing_or_ineligible_quote_is_visible_pending_without_economics(self):
        def probe(db,hid,result):
            from plugins.analyst_trader.paper_monitor import process_quote
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
            engine=DualPortfolioEngine(db)
            evidence=self.quote(db,hid,2.,offset=100)
            valid=evidence['quote']
            for quote in (None, {}, dict(valid,observed_at=(evidence['now']-timedelta(seconds=61)).isoformat()),
                          dict(valid,observed_at=(evidence['now']+timedelta(seconds=1)).isoformat()),
                          dict(valid,holding_id='WRONG'),dict(valid,bid=3.,ask=2.),
                          dict(valid,flow_id='TEST-wrong'),dict(valid,intent_id='TEST-wrong'),
                          dict(valid,occ_symbol='TEST261016P00105000'),
                          dict(valid,evidence_status='inferred'),dict(valid,source=''),
                          dict(valid,observed_at=evidence['now'].replace(tzinfo=None).isoformat())):
                with self.subTest(quote=quote):
                    update=process_quote(db,engine,hid,**dict(evidence,quote=quote))
                    self.assertIsNotNone(update)
                    self.assertEqual(update['exit_status'],'EXIT_PENDING')
                    self.assertIsNone(update['economic_receipt'])
                    self.assertIsNone(update['operation'])
            with db._get_connection() as c:
                h=dict(c.execute('SELECT * FROM portfolio_holdings WHERE holding_id=?',(hid,)).fetchone())
                self.assertEqual((h['status'],h['quantity'],h['realized_pnl']),('OPEN',4,0))
                self.assertEqual(c.execute("SELECT count(*) FROM recorded_strategies WHERE event_type='autonomous_trade_closed'").fetchone()[0],0)
            samples=AnalystStyleLearner(db).import_paper_outcomes()['samples']
            self.assertTrue(samples)
            self.assertTrue(all(s['status']=='unresolved' and s['outcome'] is None and s['net_pnl'] is None for s in samples))
        self.producer(probe)
