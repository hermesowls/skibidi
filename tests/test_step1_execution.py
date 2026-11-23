"""Step 1 TEST fixtures only. Actual callers, isolated SQLite; no provider evidence."""
import tempfile
import unittest
from pathlib import Path
from typing import Any
from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
from step1_fixtures import persist_source, lifecycle_evidence

class ExecutionTests(unittest.TestCase):
    def holding(self, holding_id):
        row = self.db.get_portfolio_holding(holding_id)
        assert row is not None
        return row

    def portfolio(self, portfolio_id):
        row = self.db.get_portfolio(portfolio_id)
        assert row is not None
        return row

    def flow(self, flow_id):
        row = self.db.get_notable_flow_by_id(flow_id)
        assert row is not None
        return row

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = AnalystDatabase(Path(self.tmp.name)/'TEST.sqlite')
        self.engine = DualPortfolioEngine(self.db)
        self.intent: dict[str, Any] = dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',
                           occ_symbol='TEST261016C00100000',flow_id='TEST-source',intent_id='TEST-intent',
                           parent_trace_id='TEST-decision',policy_version='TEST-policy-v1',
                           execution_authorized=True,execution_mode='paper',entry_price=4,
                           tp1_price=5,tp2_price=6,stop_loss_price=3)
        from datetime import datetime,timezone
        self.intent['risk_limits']=dict(max_order_notional=1500,max_gross_notional=5000,max_positions=5,max_evidence_age_seconds=60)
        self.intent['quote']=dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',occ_symbol='TEST261016C00100000',flow_id='TEST-source',intent_id='TEST-intent',quote_id='TEST-entry',source='TEST-observed-fixture',evidence_status='observed',observed_at=datetime.now(timezone.utc).isoformat(),bid=3.9,ask=4)
        persist_source(self.db,self.intent)

    def evidence(self, hid, price, operation='exit'):
        return lifecycle_evidence(self.db,hid,price,operation)

    def test_caller_missing_policy_abstains_until_explicit_version(self):
        manager=self.manager(); manager.quant_engine=None; manager.deep_dive_analyzer=None
        args: dict[str, Any] = dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',dte=27,premium_usd=1000000,entry_price=4,spot_price=100,auto_publish_alerts=False)
        for change in ({'execution_authorized':False},{'execution_mode':'live'},{'policy_version':None},{'ticker':'OTHER'}):
            result=manager.evaluate_candidate_end_to_end(**args,execution_decision=dict(self.intent,**change))
            self.assertIsNone(result['paper_trade'])
        result=manager.evaluate_candidate_end_to_end(**args,execution_decision=dict(self.intent,policy_version=None),execution_policy_version='TEST-explicit-version')
        self.assertIsNotNone(result['paper_trade'])
        self.assertEqual(result['paper_trade']['policy_version'],'TEST-explicit-version')

    def test_sql_faults_after_journal_insert_and_economic_update_rollback(self):
        for trigger in ("BEFORE UPDATE ON portfolios", "AFTER INSERT ON recorded_strategies"):
            with self.db._get_connection() as conn:
                conn.execute('CREATE TRIGGER TEST_before_commit '+trigger+" BEGIN SELECT RAISE(ABORT,'TEST-before-commit'); END")
            with self.assertRaises(Exception): self.engine.execute_autonomous_trade(self.intent)
            self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])
            self.assertEqual(self.db.list_recorded_strategies(),[])
            with self.db._get_connection() as conn: conn.execute('DROP TRIGGER TEST_before_commit')
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        for method in (self.engine.execute_autonomous_trim,self.engine.execute_autonomous_exit):
            before=self.holding(entry['holding_id'])
            with self.db._get_connection() as conn:
                conn.execute("CREATE TRIGGER TEST_before_commit AFTER INSERT ON recorded_strategies BEGIN SELECT RAISE(ABORT,'TEST-before-commit'); END")
            price=5 if method==self.engine.execute_autonomous_trim else 3
            op='trim' if price==5 else 'exit'
            with self.assertRaisesRegex(Exception,'TEST-before-commit'): method(entry['holding_id'],price,**self.evidence(entry['holding_id'],price,op))
            self.assertEqual(self.holding(entry['holding_id']),before)
            self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],99200)
            self.assertEqual(len(self.db.list_recorded_strategies()),1)
            with self.db._get_connection() as conn: conn.execute('DROP TRIGGER TEST_before_commit')

    def test_initial_stop_and_wrong_source_expiry(self):
        manager,quote,hid,clock=self.monitor_fixture('P')
        with self.db._get_connection() as conn: conn.execute("UPDATE notable_flow SET expiration='2027-10-16' WHERE flow_id='TEST-source'")
        self.assertEqual(manager.monitor_and_update_positions(),[])
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'MONITORING')
        with self.db._get_connection() as conn: conn.execute("UPDATE notable_flow SET expiration='2026-10-16' WHERE flow_id='TEST-source'")
        quote.update(bid=2.5,ask=2.6)
        result=manager.monitor_and_update_positions()
        self.assertEqual(result[0]['outcome'],'LOSS_STOP_HIT')
        self.assertEqual(self.holding(hid)['realized_pnl'],-300)
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],99700)
        self.assertEqual(manager.monitor_and_update_positions(),[])

    def test_real_evaluation_caller_propagates_only_explicit_decision(self):
        manager=self.manager()
        # Upstream inference is outside step 1; no inferred approval is manufactured.
        manager.quant_engine=None; manager.deep_dive_analyzer=None
        args: dict[str, Any] = dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',dte=27,premium_usd=1000000,entry_price=4,spot_price=100,auto_publish_alerts=False)
        denied=manager.evaluate_candidate_end_to_end(**args)
        self.assertFalse(denied.get('paper_trade'))
        result=manager.evaluate_candidate_end_to_end(**args,execution_decision=dict(self.intent))
        self.assertIsNotNone(result.get('paper_trade'))
        event=next(e for e in self.db.list_recorded_strategies() if e['event_type']=='autonomous_trade_executed')
        self.assertEqual(event['parent_trace_id'],'TEST-decision')

    def test_entry_requires_quote_and_shared_risk_limits(self):
        import copy
        for change in ({'quote':None},{'risk_limits':None},{'risk_limits':dict(self.intent['risk_limits'],max_order_notional=1)}, {'quantity':5}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(dict(self.intent,**change))
        for change in ({'bid':None},{'observed_at':'2026-01-01T00:00:00+00:00'},{'ask':3},{'expiration':'2026-10-17'}):
            intent=copy.deepcopy(self.intent); intent['quote'].update(change)
            with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(intent)
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])

    def test_public_execution_requires_explicit_permission(self):
        for permission in (None,False,1,'true'):
            intent=dict(self.intent)
            if permission is None: intent.pop('execution_authorized')
            else: intent['execution_authorized']=permission
            with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(intent)
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])
        self.assertIsNotNone(self.engine.execute_autonomous_trade(self.intent))

    def test_entry_receipt_immutable_conflict_and_atomic_journal(self):
        from concurrent.futures import ThreadPoolExecutor
        with self.db._get_connection() as conn:
            conn.execute("CREATE TRIGGER TEST_fault BEFORE INSERT ON recorded_strategies BEGIN SELECT RAISE(ABORT,'TEST-journal-fault'); END")
        with self.assertRaises(Exception): self.engine.execute_autonomous_trade(self.intent)
        self.assertEqual(self.db.list_portfolio_holdings('autonomous_ai'),[])
        with self.db._get_connection() as conn: conn.execute('DROP TRIGGER TEST_fault')
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts=list(pool.map(lambda _:self.engine.execute_autonomous_trade(self.intent),range(4)))
        self.assertTrue(all(r==receipts[0] for r in receipts))
        with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(dict(self.intent,entry_price=4.1))
        for field in ('intent_id','flow_id','parent_trace_id','policy_version','occ_symbol'):
            bad=dict(self.intent); bad.pop(field)
            with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(bad)
        events=self.db.list_recorded_strategies()
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['parent_trace_id'],'TEST-decision')

    def manager(self):
        from unittest.mock import patch
        from autonomous_risk_manager import AutonomousRiskManager
        with patch('autonomous_risk_manager.DiscordPublisher'), patch('plugins.analyst_trader.dynamic_shadow_quant.DynamicShadowQuantEngine'), patch('llm_deep_dive_analyzer.LLMDeepDiveAnalyzer'):
            return AutonomousRiskManager(str(self.db.db_path))

    def test_scheduled_monitor_no_quote_cannot_advance(self):
        self.db.save_notable_flow(dict(self.intent,flow_score=90,premium_usd=1000000,current_contract_price=9,entry_contract_price=4))
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        manager=self.manager()
        manager.monitor_and_update_positions()
        self.assertEqual(self.holding(entry['holding_id'])['status'],'OPEN')
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'MONITORING')

    def test_scheduled_test_tracer_observed_quote_to_close(self):
        from datetime import datetime,timezone,timedelta
        import json
        clock=datetime(2026,9,19,6,0,tzinfo=timezone.utc)
        self.intent['quote']['observed_at']=clock.isoformat()
        self.db.save_notable_flow(dict(self.intent,flow_score=90,premium_usd=1000000,current_contract_price=9,entry_contract_price=4))
        entry=self.engine.execute_autonomous_trade(self.intent,now=clock); assert entry
        self.assertEqual(entry['timestamp'],clock.isoformat())
        hid=entry['holding_id']
        manager=self.manager()
        quote=dict(ticker='TEST',strike=100,call_put='C',expiration='2026-10-16',occ_symbol='TEST261016C00100000',
                   holding_id=hid,flow_id='TEST-source',intent_id='TEST-intent',quote_id='TEST-tick1',
                   source='TEST-observed-fixture',evidence_status='observed',observed_at=clock.isoformat(),bid=5,ask=5.1)
        manager.quote_max_age_seconds=60
        manager.clock=lambda:clock
        manager.quote_reader=lambda holding:dict(quote)
        result=manager.monitor_and_update_positions()
        self.assertEqual(self.holding(hid)['quantity'],1)
        self.assertEqual(self.holding(hid)['target_sl'],4)
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'WIN_TP1')
        self.assertEqual(manager.monitor_and_update_positions(),[])
        clock+=timedelta(seconds=10)
        quote.update(quote_id='TEST-tick2',observed_at=clock.isoformat(),bid=6,ask=6.1)
        restarted=self.manager(); restarted.quote_max_age_seconds=60; restarted.clock=lambda:clock; restarted.quote_reader=lambda holding:dict(quote)
        self.assertEqual(len(restarted.monitor_and_update_positions()),1)
        self.assertEqual(restarted.monitor_and_update_positions(),[])
        holding=self.holding(hid)
        portfolio=self.portfolio('autonomous_ai')
        self.assertEqual((holding['status'],holding['quantity'],holding['realized_pnl']),('CLOSED',0,300))
        self.assertEqual((portfolio['cash_balance'],portfolio['total_value']),(100300,100300))
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'WIN_TP2')
        events=self.db.list_recorded_strategies()
        self.assertEqual(sum(e['event_type']=='paper_monitor_outcome' for e in events),2)
        self.assertEqual(sum(e['event_type'].startswith('autonomous_trade_') for e in events),3)
        economic=[e for e in events if e['event_type'].startswith('autonomous_trade_')]
        self.assertEqual(sum(e['realized_pnl'] or 0 for e in economic),holding['realized_pnl'])
        self.assertEqual(sum(e['quantity'] for e in economic if e['event_type']!='autonomous_trade_executed'),entry['quantity'])
        print('STEP1_TEST_TRACER '+json.dumps(dict(fixture='TEST ONLY - no provider/broker evidence',clock=clock.isoformat(),entry_receipt=entry,final_holding=holding,final_portfolio=portfolio,event_count=len(events),economic_event_count=len(economic),outcome='WIN_TP2'),sort_keys=True))

    def monitor_fixture(self, right='C'):
        from datetime import datetime,timezone
        self.intent.update(call_put=right,occ_symbol='TEST261016'+right+'00100000')
        self.intent['quote'].update(call_put=right,occ_symbol=self.intent['occ_symbol'])
        persist_source(self.db,self.intent)
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        manager=self.manager()
        clock=datetime.fromisoformat(entry['timestamp'])
        quote=dict(self.intent['quote'],holding_id=entry['holding_id'],observed_at=clock.isoformat(),bid=5,ask=5.1,quote_id='TEST-tick1')
        manager.quote_max_age_seconds=60; manager.clock=lambda:clock; manager.quote_reader=lambda holding:dict(quote)
        return manager,quote,entry['holding_id'],clock

    def test_monitor_abstains_countercases_and_atomic_outcome_rollback(self):
        from datetime import timedelta
        manager,quote,hid,clock=self.monitor_fixture('P')
        original=dict(quote)
        cases=[{'bid':v} for v in (None,True,False,float('nan'),float('inf'),1e308,-1,0)]
        cases += [{'source':''},{'evidence_status':'estimated'},{'ask':4},{'ask':None},{'observed_at':clock.replace(tzinfo=None).isoformat()},
                  {'observed_at':(clock-timedelta(seconds=61)).isoformat()},{'observed_at':(clock+timedelta(seconds=1)).isoformat()},
                  {'expiration':'2026-10-17'},{'occ_symbol':'BAD'},{'intent_id':'OTHER'},{'flow_id':'OTHER'},{'holding_id':'OTHER'},{'strike':101},{'call_put':'C'}]
        for change in cases:
            quote.clear(); quote.update(original); quote.update(change)
            with self.subTest(change=change): self.assertEqual(manager.monitor_and_update_positions(),[])
        quote.clear(); quote.update(original)
        before=self.holding(hid)
        with self.db._get_connection() as conn:
            conn.execute("CREATE TRIGGER TEST_outcome_fault BEFORE INSERT ON recorded_strategies WHEN NEW.event_type='paper_monitor_outcome' BEGIN SELECT RAISE(ABORT,'TEST-outcome-fault'); END")
        with self.assertRaises(Exception): manager.monitor_and_update_positions()
        self.assertEqual(self.holding(hid),before)
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],99200)
        self.assertEqual(self.flow('TEST-source')['final_outcome'],'MONITORING')
        self.assertEqual(len(self.db.list_recorded_strategies()),1)
        with self.db._get_connection() as conn: conn.execute('DROP TRIGGER TEST_outcome_fault')
        result=manager.monitor_and_update_positions()
        self.assertEqual(result[0]['pnl_pct'],25)
        quote.update(quote_id='TEST-tick2',observed_at=(clock+timedelta(seconds=10)).isoformat(),bid=3.5,ask=3.6)
        manager.clock=lambda:clock+timedelta(seconds=10)
        result=manager.monitor_and_update_positions()
        self.assertEqual(result[0]['outcome'],'LOSS_STOP_HIT')
        self.assertEqual(self.holding(hid)['realized_pnl'],50)
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],100050)
        self.assertEqual(manager.monitor_and_update_positions(),[])

    def test_concurrent_monitor_and_direct_lifecycle_retries(self):
        from concurrent.futures import ThreadPoolExecutor
        manager,quote,hid,clock=self.monitor_fixture()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:manager.monitor_and_update_positions(),range(4)))
        self.assertEqual(sum(len(r) for r in results),1)
        self.assertEqual(self.holding(hid)['quantity'],1)
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts=list(pool.map(lambda _:self.engine.execute_autonomous_exit(hid,6,**self.evidence(hid,6)),range(4)))
        self.assertTrue(all(r==receipts[0] for r in receipts))
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],100300)

    def test_decimal_tranche_pnl_is_economic_not_float_subtraction_noise(self):
        self.intent.update(entry_price=2.1,quantity=3,tp1_price=2.2,tp2_price=2.3,stop_loss_price=1.9)
        self.intent['quote'].update(bid=2.09,ask=2.1)
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        mark=self.db.update_holding_market_price(entry['holding_id'],2.2); assert mark
        self.assertEqual(mark['unrealized_pnl'],30)
        trim=self.engine.execute_autonomous_trim(entry['holding_id'],2.2,**self.evidence(entry['holding_id'],2.2,'trim'))
        final=self.engine.execute_autonomous_exit(entry['holding_id'],2.0,**self.evidence(entry['holding_id'],2.0))
        assert trim is not None and final is not None
        self.assertEqual(trim['realized_pnl'],20)
        self.assertEqual(final['realized_pnl'],-10)
        self.assertEqual(self.holding(entry['holding_id'])['realized_pnl'],10)
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],100010)

    def test_mark_then_close_reconciles_persisted_unrealized_and_journal_fields(self):
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        self.db.update_holding_market_price(entry['holding_id'],5)
        self.engine.execute_autonomous_trim(entry['holding_id'],5,**self.evidence(entry['holding_id'],5,'trim'))
        self.engine.execute_autonomous_exit(entry['holding_id'],6,**self.evidence(entry['holding_id'],6))
        self.assertEqual(self.portfolio('autonomous_ai')['unrealized_pnl'],0)
        event=next(e for e in self.db.list_recorded_strategies() if e['event_type']=='autonomous_trade_executed')
        self.assertEqual(event['entry_price'],4)
        event=next(e for e in self.db.list_recorded_strategies() if e['event_type']=='autonomous_trade_closed')
        self.assertEqual(event['exit_price'],6)

    def test_direct_lifecycle_rejects_corrupt_holding_identity_and_extreme_trim(self):
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        hid=entry['holding_id']
        with self.assertRaises(ValueError): self.engine.execute_autonomous_trim(hid,5,trim_pct=1e308,**self.evidence(hid,5,'trim'))
        for field,value in (('expiration','2027-10-16'),('average_cost',0),('quantity',3),('occ_symbol','WRONG')):
            original=self.holding(hid)[field]
            with self.db._get_connection() as conn: conn.execute('UPDATE portfolio_holdings SET '+field+'=? WHERE holding_id=?',(value,hid))
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,'identity'): self.engine.execute_autonomous_exit(hid,3,**self.evidence(hid,3))
            with self.db._get_connection() as conn: conn.execute('UPDATE portfolio_holdings SET '+field+'=? WHERE holding_id=?',(original,hid))

    def test_low_level_autonomous_mutations_cannot_bypass_journal(self):
        with self.assertRaises(ValueError):
            self.db.add_portfolio_holding('TEST-low','autonomous_ai','TEST','option','call',0.5,4,strike=100,expiration='2026-10-16')
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        hid=entry['holding_id']
        with self.assertRaises(ValueError): self.db.trim_portfolio_holding(hid,1,5,100)
        with self.assertRaises(ValueError): self.db.close_portfolio_holding(hid,5,200)
        self.assertEqual(self.holding(hid)['quantity'],2)

    def test_entry_economic_precision_is_not_rounded_to_display_cents(self):
        from decimal import Decimal
        self.intent.update(entry_price=4.12345,quantity=3,tp1_price=5.12345,tp2_price=6.2,stop_loss_price=3)
        self.intent['quote'].update(bid=4.12,ask=4.12345)
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        self.assertEqual(entry['total_cost'],float(Decimal('4.12345')*300))
        trimmed=self.engine.execute_autonomous_trim(entry['holding_id'],5.12345,trim_pct=0.6666666666666666,**self.evidence(entry['holding_id'],5.12345,'trim'))
        final=self.engine.execute_autonomous_exit(entry['holding_id'],3.12345,**self.evidence(entry['holding_id'],3.12345))
        assert trimmed is not None and final is not None
        self.assertEqual(trimmed['realized_pnl'],200)
        self.assertEqual(final['realized_pnl'],-100)
        self.assertEqual(self.holding(entry['holding_id'])['realized_pnl'],100)
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],100100)

    def test_bounded_economics_targets_and_corrupt_quantity(self):
        for key in ('entry_price','tp1_price','tp2_price','stop_loss_price','quantity'):
            for value in (True,False,float('nan'),float('inf'),1e308,-1,0):
                with self.subTest(key=key,value=value):
                    with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(dict(self.intent,**{key:value}))
        with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(dict(self.intent,quantity=0.5))
        with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(dict(self.intent,entry_price=1e-320))
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry
        hid=entry['holding_id']
        for method in (self.engine.execute_autonomous_trim,self.engine.execute_autonomous_exit,self.db.update_holding_market_price):
            with self.assertRaises(ValueError): method(hid,1e308)
        mark=self.db.update_holding_market_price(hid,5)
        assert mark is not None
        self.assertEqual(mark['unrealized_pnl'],200)
        self.assertEqual(self.portfolio('autonomous_ai')['total_value'],100200)
        with self.db._get_connection() as conn: conn.execute('UPDATE portfolio_holdings SET quantity=0.5 WHERE holding_id=?',(hid,))
        for method in (self.engine.execute_autonomous_trim,self.engine.execute_autonomous_exit,self.db.update_holding_market_price):
            with self.assertRaises(ValueError): method(hid,5)

    def test_exact_free_roll_and_existing_risk_caps(self):
        from autonomous_risk_manager import get_contract_trim_schedule
        self.assertFalse(get_contract_trim_schedule(3,49.99,60)['is_free_roll'])
        with self.assertRaises(ValueError): self.engine.execute_autonomous_trade(self.intent,account_tier='micro')
        self.portfolio('autonomous_ai')
        with self.db._get_connection() as conn: conn.execute("UPDATE portfolios SET cash_balance=0,total_value=0 WHERE portfolio_id='autonomous_ai'")
        self.assertIsNone(self.engine.execute_autonomous_trade(self.intent))
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],0)

    def test_trim_exit_atomic_replay_after_close_and_put_economics(self):
        import json
        self.intent.update(call_put='P',occ_symbol='TEST261016P00100000')
        self.intent['quote'].update(call_put='P',occ_symbol='TEST261016P00100000')
        self.intent['tp2_price']=5
        persist_source(self.db,self.intent)
        entry=self.engine.execute_autonomous_trade(self.intent); assert entry is not None
        hid=entry['holding_id']
        for operation in ('trim','exit'):
            before=self.holding(hid)
            cash=self.portfolio('autonomous_ai')['cash_balance']
            count=len(self.db.list_recorded_strategies())
            with self.db._get_connection() as conn:
                conn.execute("CREATE TRIGGER TEST_fault BEFORE INSERT ON recorded_strategies BEGIN SELECT RAISE(ABORT,'TEST-journal-fault'); END")
            method=getattr(self.engine,'execute_autonomous_'+operation)
            evidence=self.evidence(hid,5,operation)
            with self.assertRaisesRegex(Exception,'TEST-journal-fault'): method(hid,5,**evidence)
            self.assertEqual(self.holding(hid),before)
            self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],cash)
            self.assertEqual(len(self.db.list_recorded_strategies()),count)
            with self.db._get_connection() as conn: conn.execute('DROP TRIGGER TEST_fault')
            receipt=method(hid,5,**evidence)
            self.assertEqual(receipt['realized_pnl'],100)
            self.assertEqual(method(hid,5,**evidence),receipt)
            with self.assertRaises(ValueError): method(hid,5.1,**self.evidence(hid,5.1,operation))
        self.assertEqual(self.engine.execute_autonomous_trade(self.intent),entry)
        self.assertEqual(self.portfolio('autonomous_ai')['cash_balance'],100200)
        self.assertEqual(self.holding(hid)['quantity'],0)
        self.assertEqual(len(self.db.list_recorded_strategies()),5)


