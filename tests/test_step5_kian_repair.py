"""Offline actual caller tests. Only market/transport boundaries substituted."""
import inspect
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from typing import Any
from step5_test_clock import frozen_test_clock


class ProducerContext(unittest.TestCase):
    def test_both_actual_producers_record_context_without_authorizing_publication(self):
        self.run_producers(False)

    def test_registered_research_publishes_from_both_producers_without_a_plus_or_execution(self):
        self.run_producers(True)

    def test_real_producers_consume_completed_candles(self):
        self.run_producers(True, technical=True)

    def test_candle_caller_cannot_relax_registered_freshness(self):
        self.run_producers(True,technical=True,relax_ta=True)

    def test_observed_gex_king_node_is_target_not_entry_and_wall_is_conflict(self):
        self.run_producers(True, technical=True, gex=True)

    def test_missing_baseline_fields_never_qualify(self):
        for key in ('size','volume','open_interest','spot_observed_at','complex_trade'):
            with self.subTest(field=key):
                self.run_producers(True, missing=key, expected='INCOMPLETE')

    def test_baseline_rejections_remain_tracked(self):
        for change in ({'size':499},{'volume':0},{'complex_trade':True},{'spot_price':105.}):
            with self.subTest(change=change):
                self.run_producers(True, change=change, expected='REJECTED')

    def test_recovered_premium_candidate_does_not_require_legacy_sweep_gate(self):
        self.run_producers(True, low_premium=True)

    def test_publication_denial_is_independent_of_research_evaluation(self):
        self.run_producers(True, publish=False)

    def test_incomplete_baseline_cannot_execute_research_intent(self):
        self.run_producers(True, execute=True, missing='size',expected='INCOMPLETE')

    def test_missing_explicit_paper_lifecycle_abstains(self):
        self.run_producers(True,execute=True,no_lifecycle=True)

    def test_actual_producer_delivery_restart_and_uncertain_no_resend(self):
        for mode in ('retryable','unknown','permanent'):
            with self.subTest(mode=mode): self.run_producers(True,delivery_mode=mode)

    def test_changed_source_cannot_resume_research_delivery(self):
        self.run_producers(True,delivery_mode='retryable',corrupt_resume=True)

    def test_actual_callers_reject_bad_policy_and_identity(self):
        for invalid in ('missing_policy','proposed','future_policy','hash','source','contract','unauthorized'):
            with self.subTest(invalid=invalid):
                self.run_producers(True,invalid=invalid)

    def test_connected_authorized_paper_economics_learning_and_authenticated_api(self):
        with tempfile.TemporaryDirectory() as dataset:
            for trim,expected_net,total,suffix in ((.75,496,496,'gain'),(.25,-104,392,'loss')):
                with self.subTest(trim=trim):
                    self.run_producers(True, execute=True, trim=trim, expected_net=expected_net,
                        shared=dataset,suffix=suffix,expected_total=total,delivery_mode='retryable')

    @frozen_test_clock
    def run_producers(self, research, technical=False, missing=None, change=None, expected='QUALIFIED', low_premium=False,
                      execute=False, trim=.75, expected_net=496, publish=True, invalid=None, gex=False,no_lifecycle=False,delivery_mode=None,
                      shared=None,suffix='',expected_total=None,corrupt_resume=False,relax_ta=False,
                      max_hold_seconds=86400, lifecycle_probe=None, expiry='2026-10-16',
                      research_policy=None, candidate_probe=None, selected_profile_factory=None, option_side='C', queued_probe=None):
        from plugins.analyst_trader.db import AnalystDatabase
        from flow_ingestion_engine import FlowIngestionEngine
        from owlfred_engine import eval_ticker
        for caller in (FlowIngestionEngine, eval_ticker):
            self.assertIn('learning_context', inspect.signature(caller).parameters,
                          'Actual producer must expose explicit learning context')
            self.assertIn('execution_decision', inspect.signature(caller).parameters)
            if research:
                self.assertIn('research_context', inspect.signature(caller).parameters)
        from contextlib import nullcontext
        with (nullcontext(shared) if shared else tempfile.TemporaryDirectory()) as tmp:
            db = AnalystDatabase(Path(tmp)/'TEST.sqlite')
            now = datetime.now(timezone.utc)
            at = now.isoformat()
            version = 'TEST-context-policy'+suffix
            from plugins.analyst_trader.learning_store import digest
            policy: dict[str, Any] = dict(schema_version=1,mode='paper_test',origin='recovered_local_plus_test_proposals',
                min_premium=50000,min_size=500,dte_min=0,dte_max=40,max_otm_fraction=.10,
                max_age_seconds=120,calendar_zone='UTC',complex_handling='reject',ask_handling='report_only',
                premium_definition='single_print_usd',size_definition='single_print_contracts',
                volume_definition='aggregate_contract_session',approval='TEST_OFFLINE_ONLY')
            policy['ta_settings']=dict(timeframe='1h',max_age_seconds=3600,expected_interval_seconds=3600,
                variant='KIAN-TA-v1',approval='TEST_OFFLINE_ONLY')
            if not no_lifecycle:
                policy['paper_lifecycle']=dict(entry_trigger='explicit_source_matched_owner_test',quantity=4,
                    stop_loss_price=1.,tp1_price=4.,tp2_price=6.,max_hold_seconds=max_hold_seconds,
                    quote_max_age_seconds=60,cost_requirement='observed_costs_before_learning',
                    exits='explicit_evidence_backed_partial_final',approval='TEST_OFFLINE_ONLY')
            if research_policy is not None:
                policy = research_policy
            db.save_learning_version(dict(version_id=version,schema_version=1,code_identity='TEST',
                config_identity='TEST',training_cutoff=(now-timedelta(days=2)).isoformat(),
                created_at=(now+timedelta(days=1) if invalid=='future_policy' else now-timedelta(days=1)).isoformat(),source_mode='paper_test',evidence_ids=[],
                uncertainty=['TEST only; no edge'],classification='proposal' if invalid=='proposed' else 'stated_policy',
                profile={'rules':{},'kian_research':policy,'kian_policy_hash':digest(policy)}))
            if selected_profile_factory is not None:
                selected = selected_profile_factory(db, now)
                version = selected['version_id']
                policy = selected['profile']['kian_research']
            compact_expiry = datetime.fromisoformat(expiry).strftime('%y%m%d')
            inputs = dict(ticker='TEST',strike=105.,call_put='C',expiration=expiry,
                dte=(datetime.fromisoformat(expiry).date()-now.date()).days,
                premium_usd=1000000.,entry_price=2.,spot_price=100.,technical_data={})
            context = dict(decision_id='TEST-flow-decision'+suffix,source_id='flow_TEST-context'+suffix,
                           profile_version=version,decision_at=at,inputs=inputs)
            publication = dict(publishing_authorized=publish,flow_id=context['source_id'],
                alert_id='TEST-context-alert'+suffix,revision=1,policy_version=version)
            evidence = dict(source_id=context['source_id'],source='discord_notable_flow',
                contract_symbol=f'TEST{compact_expiry}C00105000',ticker='TEST',strike=105.,call_put='C',expiration=expiry,
                observed_at=(now-timedelta(seconds=10)).isoformat(),spot_observed_at=(now-timedelta(seconds=10)).isoformat(),
                spot_price=100.,premium_usd=1000000.,size=500,volume=1000,open_interest=0,
                complex_trade=False,reported_side='ask',premium_definition='single_print_usd',
                size_definition='single_print_contracts',volume_definition='aggregate_contract_session',
                evidence_id='TEST-observation')
            inputs['call_put'] = evidence['call_put'] = option_side
            evidence['contract_symbol'] = f'TEST{compact_expiry}{option_side}00105000'
            if low_premium:
                inputs['premium_usd']=evidence['premium_usd']=50000.
            if missing:
                evidence.pop(missing)
            if change:
                evidence.update(change)
                if 'spot_price' in change: inputs['spot_price']=change['spot_price']
            extra: dict[str, Any] = dict(research_context=dict(authorized=True,mode='paper_test',policy_hash=digest(policy),
                evidence=evidence)) if research else {}
            if invalid=='missing_policy': context['profile_version']='TEST-missing'
            if invalid=='hash': extra['research_context']['policy_hash']='TEST-not-hash'
            if invalid=='source': evidence['source_id']='TEST-other-source'
            if invalid=='contract': evidence['contract_symbol']='OTHER261016C00105000'
            if invalid=='unauthorized': extra['research_context']['authorized']=False
            if technical:
                from test_step5_kian_technicals import candles
                bars=candles()
                bars['asof']=at
                if relax_ta: bars['max_age_seconds']=999999
                for i,bar in enumerate(bars['bars']):
                    bar['completed_at']=(now-timedelta(hours=201-i)).isoformat()
                extra['research_context']['candles']=bars
            if gex:
                extra['research_context']['gex']=dict(ticker='TEST',source='TEST-observed-levels',
                    evidence_id='TEST-gex',observed_at=at,timeframe='0DTE_INTRADAY',
                    levels=[dict(kind='king_node',price=110.),dict(kind='negative_wall',price=102.)])
            calls = []
            resumed=False
            def transport(unit):
                calls.append(unit)
                if delivery_mode and not resumed and unit['alert_id']==publication['alert_id'] and unit['card']=='risk':
                    return dict(state=delivery_mode,error='TEST boundary '+delivery_mode,retry_after=0)
                return dict(state='succeeded',receipt='TEST-receipt-'+str(len(calls)))
            opts = dict(delivery_clock=lambda:now.timestamp(),delivery_destinations=[('discord','TEST-only')],
                        delivery_transport=transport,
                        observation_reader=lambda *args:dict(entry_price=2.,spot_price=inputs['spot_price'],
                            source_evidence=dict(mode='paper_test',source_id=context['source_id'],evidence_id='TEST-fixture-source')))
            intent: Any=None
            if execute:
                from step1_fixtures import paper_intent
                intent=paper_intent(dict(inputs,flow_id=context['source_id'],tp1_price=4.,tp2_price=6.,stop_loss_price=1.),quantity=4)
                intent.update(parent_trace_id=context['decision_id'],policy_version=version)
                intent['quote']['observed_at']=at
            with patch('plugins.analyst_trader.finviz_fetcher.FinvizFetcher.fetch_ticker_metrics',
                       return_value={'ticker':'TEST','price':100,'current_price':100}):
                flow = FlowIngestionEngine(db,discord_token='',chart_loader=lambda **kw:None,
                    publication_policy=lambda source:publication,learning_context=context,execution_decision=intent,**opts,**extra)
                msg = dict(id='TEST-context'+suffix,content=f'TEST 105 {option_side} {expiry} $1M SWEEP',
                           # Distinct observed prints in the shared gain/loss dataset.
                           timestamp=(now-timedelta(seconds=31 if suffix=='loss' else 30)).isoformat())
                if low_premium: msg['content']='TEST 105 C 10/16/2026 $50K'
                self.assertTrue(flow._process_message(msg,'TEST-channel','TEST','equity'))
                if invalid:
                    self.assertIsNone(flow.last_evaluation)
                    with self.assertRaises(ValueError):
                        eval_ticker('TEST',db_path=str(db.db_path),flow_id=context['source_id'],
                            publication=publication,learning_context=context,**opts,**extra)
                    self.assertEqual(calls,[])
                    with db._get_connection() as c:
                        self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_holdings').fetchone()[0],0)
                    return
                if expected == 'EARLY_ABSTENTION':
                    result = flow.last_evaluation or {}
                    self.assertNotEqual((result.get('research_candidate') or {}).get('baseline_status'), 'QUALIFIED')
                    try:
                        owl = eval_ticker('TEST',db_path=str(db.db_path),flow_id=context['source_id'],
                            publication=publication,learning_context=context,**opts,**extra)
                    except ValueError:
                        owl = {}
                    self.assertNotEqual((owl.get('research_candidate') or {}).get('baseline_status'), 'QUALIFIED')
                    self.assertEqual(calls, [])
                    with db._get_connection() as c:
                        self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_holdings').fetchone()[0],0)
                    return
                self.assertIsNotNone(flow.last_evaluation)
                if delivery_mode:
                    already_resumed = queued_probe(db, flow.last_evaluation, publication, opts, now) if queued_probe else False
                    before=len(calls);resumed=True
                    if corrupt_resume:
                        with db._get_connection() as c:
                            c.execute('UPDATE raw_messages SET content=? WHERE message_id=?',('TEST changed source',msg['id']))
                    restarted=FlowIngestionEngine(db,discord_token='',chart_loader=lambda **kw:None,
                        **dict(opts,delivery_clock=lambda:(now+timedelta(seconds=60)).timestamp()))
                    resumed_result=restarted.resume_publication(publication)
                    if corrupt_resume:
                        self.assertEqual(len(calls),before,'Changed raw source must not send a queued research card')
                        self.assertEqual(resumed_result['status'],'partial')
                        with self.assertRaises(ValueError):
                            eval_ticker('TEST',db_path=str(db.db_path),flow_id=context['source_id'],
                                publication=publication,learning_context=context,**opts,**extra)
                        return
                    self.assertEqual(len(calls),before+(1 if delivery_mode=='retryable' and not already_resumed else 0))
                    self.assertEqual(resumed_result['status'],'complete' if delivery_mode=='retryable' else 'uncertain' if delivery_mode=='unknown' else 'partial')
                    again=len(calls);restarted.resume_publication(publication)
                    self.assertEqual(len(calls),again)
                    self.assertFalse(restarted._process_message(msg,'TEST-channel','TEST','equity'))
                owl = eval_ticker('TEST',db_path=str(db.db_path),flow_id=context['source_id'],
                    publication=dict(publication,alert_id='TEST-owl-alert'+suffix),
                    learning_context=dict(context,decision_id='TEST-owl-decision'+suffix),**opts,**extra)
            results: list[Any] = [flow.last_evaluation,owl]
            for result in results:
                assert result is not None
                self.assertEqual(result['learning_decision']['source_id'],context['source_id'])
                self.assertEqual(result['learning_decision']['profile_version'],version)
                self.assertFalse(result['is_dream_setup'])
                delivery_status=('complete' if publish else 'denied') if research and expected=='QUALIFIED' else 'not_requested'
                if delivery_mode and result is flow.last_evaluation:
                    delivery_status='uncertain' if delivery_mode=='unknown' else 'partial'
                self.assertEqual(result['alert_delivery']['status'],delivery_status)
                if execute and not no_lifecycle and expected=='QUALIFIED' and result is flow.last_evaluation:
                    self.assertIsNotNone(result['paper_trade'],'Authorized source-matched producer intent must reach real simulator')
                else:
                    self.assertIsNone(result['paper_trade'])
                if research:
                    self.assertEqual(result['research_candidate']['baseline_status'],expected)
                    self.assertEqual(result['research_candidate']['enhanced_status'],'CONFLICT' if gex else 'UNKNOWN')
                    self.assertEqual(result['research_candidate']['policy_hash'],digest(policy))
                    if technical:
                        self.assertIn('ta',result['research_candidate'],'Actual caller dropped candle evidence')
                        self.assertEqual(result['research_candidate']['ta']['status'],'UNKNOWN' if relax_ta else 'AVAILABLE')
                        if not relax_ta: self.assertTrue(result['research_candidate']['ta']['squeeze_on'])
                    if gex:
                        self.assertEqual(result['research_candidate']['gex']['target'],110.)
                        self.assertEqual(result['research_candidate']['gex']['entry'],None)
                        self.assertTrue(result['research_candidate']['gex']['wall_conflict'])
            if candidate_probe is not None:
                candidate_probe(db, results)
            self.assertTrue(bool(calls) == (research and publish and expected=='QUALIFIED'))
            if research and calls:
                contents='\n'.join(str(unit['payload']) for unit in calls)
                self.assertIn('Baseline: QUALIFIED',contents)
                self.assertIn(digest(policy),contents)
                self.assertIn('Reported side: ask; verified buy: unknown',contents)
            if execute and not no_lifecycle and expected=='QUALIFIED':
                from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
                from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
                from step1_fixtures import lifecycle_evidence
                result=results[0]
                hid=result['paper_trade']['holding_id']
                if lifecycle_probe is not None:
                    lifecycle_probe(db, hid, result)
                    return
                engine=DualPortfolioEngine(db);learner=AnalystStyleLearner(db)
                engine.execute_autonomous_trim(hid,4.,trim_pct=trim,**lifecycle_evidence(db,hid,4.,'trim'))
                engine.execute_autonomous_exit(hid,1.,**lifecycle_evidence(db,hid,1.))
                learner.record_economic_correction(dict(correction_id='TEST-cost'+suffix,holding_id=hid,
                    evidence_id='TEST-cost-observation',observed_at=(now+timedelta(seconds=5)).isoformat(),total_costs=4))
                sample=next(s for s in learner.import_paper_outcomes()['samples'] if s['holding_id']==hid)
                self.assertIn('net_pnl',sample,repr(sample))
                self.assertEqual(sample['net_pnl'],expected_net)
                self.assertEqual(sample['decision_id'],context['decision_id'])
                self.assertEqual(learner.import_paper_outcomes()['inserted'],0)
                summary=learner.summarize_paper_learning('paper_test',(now+timedelta(seconds=10)).isoformat())
                self.assertEqual(db.get_learning_version(summary['proposed_version'])['classification'],'proposal')
                from flow_classifier import FlowClassifierEngine
                self.assertEqual(FlowClassifierEngine(str(db.db_path)).replay_learning_decision(context['decision_id']),result['learning_decision'])
                from hermes_cli import web_server as server
                from starlette.testclient import TestClient
                from plugins.analyst_trader import holding_statistics
                class SnapshotClock(datetime):
                    @classmethod
                    def now(cls,tz=None): return now+timedelta(seconds=10)
                with patch.object(server,'_analyst_db_path',return_value=db.db_path),patch.object(holding_statistics,'datetime',SnapshotClock):
                    client=TestClient(server.app)
                    self.assertEqual(client.get('/api/analyst-trader/strategies').status_code,401)
                    response=client.get('/api/analyst-trader/strategies',headers={'X-Hermes-Session-Token':server._SESSION_TOKEN})
                    self.assertEqual(response.status_code,200)
                    body=response.json()
                    portfolio_response=client.get('/api/analyst-trader/portfolio',headers={'X-Hermes-Session-Token':server._SESSION_TOKEN})
                    self.assertEqual(portfolio_response.status_code,200)
                    portfolio_body=portfolio_response.json()
                self.assertEqual(body['statistics']['total']['net_realized_pnl'],expected_net if expected_total is None else expected_total)
                import json,os
                Path(os.environ['ASTRA_SANDBOX'],f'TEST-api-{trim}.json').write_text(json.dumps(dict(strategies=body,portfolio=portfolio_body),sort_keys=True))
                with db._get_connection() as c:
                    receipts=[dict(row) for row in c.execute('SELECT * FROM alert_units WHERE alert_id IN (?,?) ORDER BY alert_id,card',
                        (publication['alert_id'],'TEST-owl-alert'+suffix))]
                self.assertEqual(sum(r['state']=='succeeded' and bool(r['receipt']) for r in receipts),4)
                Path(os.environ['ASTRA_SANDBOX'],f'TEST-lineage-{trim}.json').write_text(json.dumps(dict(
                    decision=result['learning_decision'],candidate=result['research_candidate'],entry=result['paper_trade'],
                    receipts=receipts,sample=sample,proposal=db.get_learning_version(summary['proposed_version']),
                    journal=db.list_recorded_strategies()),sort_keys=True))
                print('KIAN_CONNECTED_TRACE '+json.dumps(dict(source_id=context['source_id'],decision_id=context['decision_id'],
                    policy=version,baseline=result['research_candidate']['baseline_status'],net_pnl=sample['net_pnl'],
                    outcome=sample['outcome'],receipts=4,transport_calls=len(calls),api_net=body['statistics']['total']['net_realized_pnl']),sort_keys=True))
