"""Independent-review countercases as expected invariants; TEST-only real callers."""
import unittest
import copy
from typing import Any
from datetime import datetime, timezone, timedelta
import test_step1_execution as fixtures

class CloseoutTests(unittest.TestCase):
    db: Any
    engine: Any
    intent: dict[str, Any]
    def setUp(self):
        getattr(fixtures.ExecutionTests,'setUp')(self)
        with self.db._get_connection() as conn: conn.execute('DELETE FROM notable_flow')
    manager=fixtures.ExecutionTests.manager
    holding=fixtures.ExecutionTests.holding
    portfolio=fixtures.ExecutionTests.portfolio
    flow=fixtures.ExecutionTests.flow

    def source(self):
        self.db.save_notable_flow(dict(self.intent,flow_score=90,premium_usd=1000000,entry_contract_price=4,source='TEST-persisted'))

    def evaluate(self):
        manager=self.manager(); manager.quant_engine=None; manager.deep_dive_analyzer=None
        return manager.evaluate_candidate_end_to_end(ticker=self.intent['ticker'],strike=100,call_put=self.intent['call_put'],expiration=self.intent['expiration'],dte=27,premium_usd=1000000,entry_price=4,spot_price=100,auto_publish_alerts=False,execution_decision=copy.deepcopy(self.intent))

    def admitted(self):
        self.source()
        clock=datetime(2026,9,19,14,0,tzinfo=timezone.utc)
        self.intent['quote']['observed_at']=(clock-timedelta(seconds=10)).isoformat()
        entry=self.engine.execute_autonomous_trade(self.intent,now=clock)
        quote=dict(self.intent['quote'],holding_id=entry['holding_id'],quote_id='TEST-life',observed_at=clock.isoformat(),bid=5,ask=5.1)
        manager=self.manager(); manager.clock=lambda:clock; manager.quote_max_age_seconds=60
        return entry,quote,manager,clock

    def test_first_quote_respects_entry_execution_and_observation(self):
        entry,q,m,clock=self.admitted()
        q['observed_at']=(clock-timedelta(seconds=5)).isoformat()
        self.assertIsNone(m.process_price_update(entry['holding_id'],q))
        self.assertEqual(self.holding(entry['holding_id'])['quantity'],2)
        q['observed_at']=clock.astimezone(timezone(timedelta(hours=-4))).isoformat()
        self.assertIsNotNone(m.process_price_update(entry['holding_id'],q))  # explicit same-tick allowed
        restarted=self.manager(); restarted.quote_max_age_seconds=60; restarted.clock=lambda:clock+timedelta(seconds=10)
        q.update(quote_id='TEST-next',bid=6,ask=6.1)
        self.assertIsNone(restarted.process_price_update(entry['holding_id'],q))
        q['observed_at']=(clock+timedelta(seconds=1)).isoformat()
        self.assertIsNotNone(restarted.process_price_update(entry['holding_id'],q))

    def test_expired_fresh_entry_denied(self):
        self.intent.update(expiration='2020-01-17',occ_symbol='TEST200117C00100000')
        self.intent['quote'].update(expiration='2020-01-17',occ_symbol='TEST200117C00100000')
        self.source()
        with self.assertRaisesRegex(ValueError,'[Ee]xpir'): self.engine.execute_autonomous_trade(self.intent)
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])

    def test_expiry_exchange_date_same_day_future_and_receipt_replay(self):
        # Valid same-day date admission; this does not assert trading hours/settlement.
        clock=datetime(2026,10,16,19,0,tzinfo=timezone.utc)
        self.intent['quote']['observed_at']=clock.isoformat(); self.source()
        entry=self.engine.execute_autonomous_trade(self.intent,now=clock)
        self.assertIsNotNone(entry)
        self.assertEqual(self.engine.execute_autonomous_trade(self.intent,now=clock+timedelta(days=5)),entry)

    def test_expiry_new_york_date_boundary_and_aware_clock(self):
        for clock,allowed in [(datetime(2026,10,15,18,tzinfo=timezone.utc),True),
                              (datetime(2026,10,17,3,59,tzinfo=timezone.utc),True),
                              (datetime(2026,10,17,4,tzinfo=timezone.utc),False),
                              (datetime(2026,10,16,15),False)]:
            with self.subTest(clock=clock):
                self.setUp(); self.source()
                self.intent['quote']['observed_at']=clock.isoformat()
                if allowed: self.assertIsNotNone(self.engine.execute_autonomous_trade(self.intent,now=clock))
                else:
                    with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(self.intent,now=clock)
                    self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])

    def test_public_bare_price_and_connection_cannot_mutate(self):
        entry,q,m,clock=self.admitted(); hid=entry['holding_id']
        before=(self.holding(hid),self.portfolio('autonomous_ai'),self.flow('TEST-source'),self.db.list_recorded_strategies())
        for method in (self.engine.execute_autonomous_trim,self.engine.execute_autonomous_exit):
            with self.assertRaises((ValueError,TypeError)): method(hid,99)
            with self.db._get_connection() as conn:
                with self.assertRaises((ValueError,TypeError)): method(hid,99,_connection=conn)
        self.assertEqual(before,(self.holding(hid),self.portfolio('autonomous_ai'),self.flow('TEST-source'),self.db.list_recorded_strategies()))

    def test_public_exit_bare_price_is_not_authorization(self):
        entry,q,m,clock=self.admitted(); hid=entry['holding_id']
        with self.assertRaises((ValueError,TypeError)):
            self.engine.execute_autonomous_exit(hid,99,outcome_label='WIN_TP2')
        self.assertEqual((self.holding(hid)['quantity'],self.flow('TEST-source')['final_outcome']),(2,'MONITORING'))

    def test_direct_evidence_lifecycle_atomic_rollback_and_interleaving(self):
        from concurrent.futures import ThreadPoolExecutor
        entry,q,m,clock=self.admitted(); hid=entry['holding_id']
        def snap(): return (self.holding(hid),self.portfolio('autonomous_ai'),self.flow('TEST-source'),self.db.list_recorded_strategies())
        for trigger in ("BEFORE UPDATE ON notable_flow", "BEFORE UPDATE ON portfolios", "AFTER INSERT ON recorded_strategies"):
            before=snap()
            with self.db._get_connection() as conn: conn.execute("CREATE TRIGGER TEST_abort "+trigger+" BEGIN SELECT RAISE(ABORT,'TEST-rollback'); END")
            with self.assertRaisesRegex(Exception,'TEST-rollback'): self.engine.execute_autonomous_trim(hid,5,quote=q,now=clock)
            self.assertEqual(snap(),before)
            with self.db._get_connection() as conn: conn.execute('DROP TRIGGER TEST_abort')
        with self.assertRaises(ValueError): self.engine.execute_autonomous_exit(hid,5,outcome_label='WIN_TP2',quote=q,now=clock)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(self.engine.execute_autonomous_trim,hid,5,quote=q,now=clock)
            b=pool.submit(m.process_price_update,hid,q)
            receipt=a.result(); b.result()
        self.assertEqual(receipt['realized_pnl'],100)
        self.assertEqual(self.engine.execute_autonomous_trim(hid,5,quote=q,now=clock),receipt)
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'WIN_TP1')
        later=clock+timedelta(seconds=10); q2=dict(q,quote_id='TEST-exit',observed_at=later.isoformat(),bid=6,ask=6.1)
        with self.assertRaises(ValueError): self.engine.execute_autonomous_exit(hid,6,outcome_label='FAKE',quote=q2,now=later)
        before=snap()
        with self.db._get_connection() as conn: conn.execute("CREATE TRIGGER TEST_abort BEFORE UPDATE ON notable_flow BEGIN SELECT RAISE(ABORT,'TEST-rollback'); END")
        with self.assertRaisesRegex(Exception,'TEST-rollback'): self.engine.execute_autonomous_exit(hid,6,quote=q2,now=later)
        self.assertEqual(snap(),before)
        with self.db._get_connection() as conn: conn.execute('DROP TRIGGER TEST_abort')
        final=self.engine.execute_autonomous_exit(hid,6,outcome_label='WIN_TP2',quote=q2,now=later)
        self.assertEqual(self.engine.execute_autonomous_exit(hid,6,quote=q2,now=later+timedelta(days=5)),final)
        self.assertEqual(self.engine.execute_autonomous_trim(hid,5,quote=q,now=later),receipt)
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'WIN_TP2')
        self.assertEqual((self.holding(hid)['quantity'],self.portfolio('autonomous_ai')['cash_balance']),(0,100300))
        self.assertEqual(len(self.db.list_recorded_strategies()),5)
        m.quote_reader=lambda h:q2; m.clock=lambda:later
        self.assertEqual(m.monitor_and_update_positions(),[])
        with self.assertRaises(ValueError): self.engine.execute_autonomous_exit(hid,6,quote=dict(q2,source='OTHER'),now=later)

    def test_source_change_serializes_with_real_entry_transaction(self):
        import sqlite3
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
        self.source()
        reached=threading.Event(); release=threading.Event()
        class TracedDatabase(AnalystDatabase):
            # Instrument SQLite only; execute the actual engine and SQL unchanged.
            def _get_connection(inner):
                conn=super()._get_connection()
                def trace(sql):
                    if sql.startswith('SELECT * FROM notable_flow WHERE flow_id='):
                        reached.set()
                        if not release.wait(5): raise RuntimeError('TEST synchronization timeout')
                conn.set_trace_callback(trace)
                return conn
        engine=DualPortfolioEngine(TracedDatabase(self.db.db_path))
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending=pool.submit(engine.execute_autonomous_trade,self.intent)
            try:
                self.assertTrue(reached.wait(5))
                with sqlite3.connect(self.db.db_path,timeout=0) as writer:
                    with self.assertRaisesRegex(sqlite3.OperationalError,'locked'):
                        writer.execute("UPDATE notable_flow SET is_quarantined=1 WHERE flow_id='TEST-source'")
            finally: release.set()
            entry=pending.result()
        self.assertIsNotNone(entry)
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],99200)

    def test_source_change_committed_ahead_of_entry_is_seen(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        self.source(); started=threading.Event()
        def enter():
            started.set()
            return self.engine.execute_autonomous_trade(self.intent)
        with self.db._get_connection() as writer:
            writer.execute('BEGIN IMMEDIATE')
            writer.execute("UPDATE notable_flow SET final_outcome='LOSS_STOP_HIT'")
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending=pool.submit(enter)
                self.assertTrue(started.wait(5))
                writer.commit()
                with self.assertRaisesRegex(ValueError,'SOURCE_NOT_ELIGIBLE'): pending.result()
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])
        self.assertEqual(self.db.list_recorded_strategies(),[])

    def test_competing_intents_share_source_only_once(self):
        from concurrent.futures import ThreadPoolExecutor
        self.source(); other=copy.deepcopy(self.intent)
        other['intent_id']='TEST-other'; other['quote']['intent_id']='TEST-other'
        def enter(intent):
            try: return self.engine.execute_autonomous_trade(intent)
            except ValueError as exc: return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(enter,[self.intent,other]))
        self.assertEqual(sum(isinstance(r,dict) for r in results),1)
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],99200)

    def test_linked_quarantine_blocks_admission(self):
        self.source()
        self.db.save_flow_candidate_analytics(dict(analytics_id='TEST-q',flow_id='TEST-source',ticker='TEST'))
        with self.db._get_connection() as conn: conn.execute("UPDATE flow_candidate_analytics SET is_quarantined=1")
        with self.assertRaisesRegex(ValueError,'SOURCE_NOT_ELIGIBLE'): self.engine.execute_autonomous_trade(self.intent)
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])

    def test_validator_focused_caller_requires_evidence_and_completes_lifecycle(self):
        # Import only; never call the operational run_full_workstream_validation.
        from scripts.validate_full_workstream import execute_validation_transition
        entry,q,m,clock=self.admitted(); hid=entry['holding_id']
        with self.assertRaises(ValueError): execute_validation_transition(self.engine,hid,'trim',None,now=clock)
        trim=execute_validation_transition(self.engine,hid,'trim',q,now=clock)
        self.assertEqual(trim['realized_pnl'],100)
        q.update(quote_id='TEST-exit',observed_at=(clock+timedelta(seconds=1)).isoformat(),bid=6,ask=6.1)
        final=execute_validation_transition(self.engine,hid,'exit',q,now=clock+timedelta(seconds=1))
        self.assertEqual(final['outcome_label'],'WIN_TP2')
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'WIN_TP2')

    def test_direct_quote_countercases_cannot_bypass_evidence(self):
        entry,q,m,clock=self.admitted(); hid=entry['holding_id']
        cases=[{key:None} for key in q]
        cases += [dict(bid=True),dict(bid=float('nan')),dict(bid=1e308),dict(ask=4),dict(evidence_status='estimated'),
                  dict(observed_at=(clock-timedelta(seconds=30)).isoformat()),dict(observed_at=clock.replace(tzinfo=None).isoformat()),
                  dict(observed_at=(clock+timedelta(seconds=1)).isoformat()),dict(flow_id='OTHER'),dict(holding_id='OTHER'),dict(intent_id='OTHER'),
                  dict(occ_symbol='TEST261016P00100000'),dict(expiration='2027-10-16')]
        before=(self.holding(hid),self.portfolio('autonomous_ai'),self.flow('TEST-source'),self.db.list_recorded_strategies())
        for change in cases:
            with self.subTest(change=change):
                with self.assertRaises((ValueError,TypeError)): self.engine.execute_autonomous_trim(hid,quote=dict(q,**change),now=clock)
                self.assertEqual(before,(self.holding(hid),self.portfolio('autonomous_ai'),self.flow('TEST-source'),self.db.list_recorded_strategies()))
        self.assertIsNotNone(self.engine.execute_autonomous_trim(hid,quote=q,now=clock))

    def test_real_arm_denies_absent_source_without_economic_mutation(self):
        self.assertIsNone(self.evaluate()['paper_trade'])
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])
        self.assertFalse(any(e['event_type']=='autonomous_trade_executed' for e in self.db.list_recorded_strategies()))

    def test_real_arm_denies_ineligible_source(self):
        for field,value in [('is_quarantined',1),('expiration','2027-10-16'),('final_outcome','LOSS_STOP_HIT'),('final_outcome','WIN_TP1'),('ticker','OTHER'),('call_put','P'),('strike',101)]:
            self.setUp(); self.source()  # independent fresh source/intent/database per countercase
            original=self.flow('TEST-source')[field]
            with self.db._get_connection() as conn: conn.execute('UPDATE notable_flow SET '+field+'=? WHERE flow_id=?',(value,'TEST-source'))
            with self.subTest(field=field,value=value):
                self.assertIsNone(self.evaluate()['paper_trade'])
                self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])
            with self.db._get_connection() as conn: conn.execute('UPDATE notable_flow SET '+field+'=? WHERE flow_id=?',(original,'TEST-source'))

    def test_real_arm_persisted_source_entry_and_monitor(self):
        self.source()
        entry=self.evaluate()['paper_trade']; self.assertIsNotNone(entry)
        clock=datetime.fromisoformat(entry['timestamp'])
        quote=dict(self.intent['quote'],holding_id=entry['holding_id'],quote_id='TEST-life',observed_at=clock.isoformat(),bid=5,ask=5.1)
        manager=self.manager(); manager.clock=lambda:clock; manager.quote_max_age_seconds=60
        result=manager.process_price_update(entry['holding_id'],quote)
        self.assertIsNotNone(result)
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'WIN_TP1')
        with self.db._get_connection() as conn: conn.execute("UPDATE notable_flow SET is_quarantined=1, final_outcome='LOSS_STOP_HIT'")
        before=self.portfolio('autonomous_ai')
        self.assertEqual(self.engine.execute_autonomous_trade(self.intent),entry)
        self.assertEqual(self.portfolio('autonomous_ai'),before)
