"""Step2 closeout invariants; real SQLite/public callers, TEST boundaries only."""
import unittest
from unittest.mock import patch
from test_step2_delivery import DeliveryTests
from typing import Any


class CloseoutTests(unittest.TestCase):
    db: Any
    path: Any
    auth: Any
    rec: Any
    now: Any
    calls: Any
    destinations: Any
    setUp = DeliveryTests.setUp
    manager = DeliveryTests.manager
    transport = DeliveryTests.transport
    # Reuse only fixture helpers, not the inherited regression test collection.
    @patch('plugins.analyst_trader.finviz_fetcher.FinvizFetcher.fetch_ticker_metrics', return_value={})
    def test_flow_upstream_persists_evaluates_and_resumes(self, _market_boundary):
        from flow_ingestion_engine import FlowIngestionEngine
        from unittest.mock import Mock
        quant = Mock()
        quant.evaluate_ticker_complete_quant.return_value = {'is_a_plus_dream_setup': True}
        deep = Mock()
        deep.analyze_candidate_deep_dive.return_value = {}
        auth = dict(self.auth, flow_id='flow_TEST-raw')
        seen = []
        def policy(source):
            seen.append(source['flow_id'])
            with self.db._get_connection() as c:
                self.assertIsNotNone(c.execute('SELECT 1 FROM notable_flow WHERE flow_id=?', (source['flow_id'],)).fetchone())
            return auth
        options = dict(publication_policy=policy, delivery_destinations=self.destinations,
            delivery_transport=self.transport, delivery_clock=lambda: self.now[0],
            quant_engine=quant, deep_dive_analyzer=deep, discord_token='',
            chart_loader=lambda **kw: None,
            observation_reader=lambda parsed, msg: {'entry_price': 2, 'spot_price': 100})
        engine = FlowIngestionEngine(self.db, **options)
        msg = dict(id='TEST-raw', content='TEST 100 C 10/16/2026 $1M', timestamp='2026-09-19T00:00:00Z')
        self.assertTrue(engine._process_message(msg, 'TEST-channel', 'TEST-notable', 'equity'))
        self.assertEqual(engine.last_evaluation['alert_delivery']['status'], 'partial')
        self.assertIsNone(engine.last_evaluation['paper_trade'])
        with self.db._get_connection() as c:
            self.assertEqual(c.execute("SELECT entry_contract_price FROM notable_flow WHERE flow_id='flow_TEST-raw'").fetchone()[0], 2)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(seen, ['flow_TEST-raw'])
        self.now[0] += 60
        restarted = FlowIngestionEngine(self.db, **options)
        self.assertFalse(restarted._process_message(msg, 'TEST-channel', 'TEST-notable', 'equity'))
        result = restarted.resume_publication(auth, limit=1)
        self.assertEqual(result['status'], 'partial')
        result = restarted.resume_publication(auth)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(self.calls), 6)
        restarted.resume_publication(auth)
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(quant.evaluate_ticker_complete_quant.call_count, 1)
        self.assertEqual(deep.analyze_candidate_deep_dive.call_count, 1)
        self.assertEqual(seen, ['flow_TEST-raw'])
        self.assertEqual(restarted.resume_publication(None)['status'], 'denied')
        with self.db._get_connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_holdings').fetchone()[0], 0)
        with self.assertRaises(ValueError):
            restarted.resume_publication(dict(auth, policy_version='OTHER'))
        print('TEST_FLOW_UPSTREAM_TRACE', [(u['platform'],u['card'],u['attempts'],u['receipt']) for u in result['units']], 'evaluations=1; duplicate skipped; explicit bounded resume; paper=None')

    def test_owlfred_actual_source_evaluation_and_delivery_only_resume(self):
        import owlfred_engine as owl
        from unittest.mock import Mock
        quant = Mock()
        quant.evaluate_ticker_complete_quant.return_value = {'is_a_plus_dream_setup': True}
        deep = Mock()
        deep.analyze_candidate_deep_dive.return_value = {}
        options: dict[str, Any] = dict(db_path=str(self.path), flow_id='TEST-flow', publication=self.auth,
            delivery_destinations=self.destinations, delivery_transport=self.transport,
            delivery_clock=lambda: self.now[0], quant_engine=quant, deep_dive_analyzer=deep,
            observation_reader=lambda source: {'spot_price': 100})
        result: Any = owl.eval_ticker('TEST', **options)
        self.assertEqual(result['alert_delivery']['status'], 'partial')
        self.assertIsNone(result['paper_trade'])
        for field in ('ticker', 'strike', 'call_put', 'expiration'):
            self.assertEqual(result['recommendation'][field], self.rec[field])
        self.now[0] += 60
        resume_options: dict[str, Any] = {k:options[k] for k in ('db_path','delivery_destinations','delivery_transport','delivery_clock')}
        result = owl.resume_publication(self.auth, **resume_options)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(self.calls), 6)
        owl.resume_publication(self.auth, **resume_options)
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(quant.evaluate_ticker_complete_quant.call_count, 1)
        self.assertEqual(deep.analyze_candidate_deep_dive.call_count, 1)
        self.assertEqual(owl.eval_ticker('TEST', **dict(options, publication=None))['alert_delivery']['status'], 'denied')
        self.assertEqual(owl.eval_ticker('OTHER', **options)['alert_delivery']['status'], 'denied')
        self.assertEqual(owl.eval_ticker('TEST', **dict(options, flow_id='MISSING'))['alert_delivery']['status'], 'denied')
        self.assertEqual(owl.eval_ticker('TEST')['alert_delivery']['status'], 'denied')
        self.assertEqual(owl.eval_ticker('TEST', **dict(options, observation_reader=None))['alert_delivery']['status'], 'denied')
        with self.db._get_connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_holdings').fetchone()[0], 0)
        self.assertEqual(len(self.calls), 6)
        print('TEST_OWLFRED_UPSTREAM_TRACE', [(u['platform'],u['card'],u['attempts'],u['receipt']) for u in result['units']], 'resume evaluations=0; paper=None')

    @patch('plugins.analyst_trader.finviz_fetcher.FinvizFetcher.fetch_ticker_metrics', return_value={})
    def test_flow_absent_or_invalid_policy_never_enqueues(self, _market_boundary):
        from flow_ingestion_engine import FlowIngestionEngine
        from unittest.mock import Mock
        quant = Mock()
        quant.evaluate_ticker_complete_quant.return_value = {'is_a_plus_dream_setup': True}
        deep = Mock()
        deep.analyze_candidate_deep_dive.return_value = {}
        for i, policy in enumerate((None, lambda source: dict(self.auth, flow_id='OTHER'),
                lambda source: dict(self.auth, flow_id=source['flow_id'], publishing_authorized=1),
                lambda source: dict(self.auth, flow_id=source['flow_id'], policy_version=True))):
            engine = FlowIngestionEngine(self.db, publication_policy=policy,
                delivery_transport=self.transport, delivery_destinations=self.destinations,
                delivery_clock=lambda: self.now[0], quant_engine=quant, deep_dive_analyzer=deep,
                chart_loader=lambda **kw: None, discord_token='',
                observation_reader=lambda parsed, msg: {'entry_price': 2, 'spot_price': 100})
            self.assertTrue(engine._process_message(dict(id='TEST-deny-'+str(i),
                content='TEST 100 C 10/16/2026 $1M'), 'TEST-channel', 'TEST', 'equity'))
        self.assertEqual(self.calls, [])
        with self.db._get_connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM alert_units').fetchone()[0], 0)

    def test_upstream_resume_retains_unknown_and_rechecks_source_config(self):
        import owlfred_engine as owl

        def transport(unit):
            self.calls.append((unit['platform'], unit['card']))
            if unit['platform'] == 'telegram':
                return dict(state='unknown', error='TEST ambiguous')
            return dict(state='retryable', retry_after=10, error='TEST rejected')
        self.manager(transport).publish_actionable_alert(self.rec, publication=self.auth)
        options: dict[str, Any] = dict(db_path=self.path, delivery_clock=lambda: self.now[0],
            delivery_transport=transport, delivery_destinations=self.destinations)
        self.now[0] += 60
        with self.assertRaises(ValueError):
            owl.resume_publication(self.auth, **dict(options, delivery_destinations=[('discord','OTHER')]))
        with self.assertRaises(ValueError):
            owl.resume_publication(self.auth, **options, limit=101)
        with self.db._get_connection() as c:
            c.execute("UPDATE notable_flow SET is_quarantined=1 WHERE flow_id='TEST-flow'")
        result: Any = owl.resume_publication(self.auth, **options)
        self.assertEqual(result['status'], 'uncertain')
        self.assertEqual([u['state'] for u in result['units']], ['permanent','permanent','unknown','unknown'])
        self.assertEqual(len(self.calls), 4)

    def test_position_requires_exact_source_contract(self):
        m = self.manager(self.transport)
        def publish(symbol, rec=None, ticker='TEST'):
            return m.publish_position_exit_alert(ticker, symbol, 'TEST trim', 20, 2.4, 2,
                'TEST guidance', publication=self.auth, source_recommendation=rec or self.rec)
        for symbol in ('OTHER261016P00999000', 'TEST261023C00100000',
                       'TEST261016P00100000', 'TEST261016C00101000',
                       'test261016C00100000', ' TEST261016C00100000', 'broken'):
            with self.assertRaises(ValueError):
                publish(symbol)
        with self.assertRaises(ValueError):
            publish(self.rec['contract_symbol'], dict(self.rec, contract_symbol='broken'))
        with self.assertRaises(ValueError):
            publish(self.rec['contract_symbol'], dict(self.rec, occ_symbol='broken'))
        self.assertEqual(self.calls, [])
        with self.db._get_connection() as c:
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='alert_units'").fetchone())
        self.now[0] += 60
        result = publish(self.rec['contract_symbol'])
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(result['units']), 2)
        # Self-consistent supplied alternate subject still cannot match the DB.
        for fields, symbol in (({'ticker':'OTHER'}, 'OTHER261016C00100000'),
                ({'expiration':'2026-10-23'}, 'TEST261023C00100000'),
                ({'call_put':'P'}, 'TEST261016P00100000'),
                ({'strike':101}, 'TEST261016C00101000')):
            source = dict(self.rec, **fields)
            source['contract_symbol'] = symbol
            with self.assertRaisesRegex(ValueError, 'SOURCE_NOT_ELIGIBLE'):
                m.publish_position_exit_alert(source['ticker'], symbol, 'TEST', 20, 2.4, 2, 'TEST',
                    publication=dict(self.auth, alert_id='TEST-alternate-'+symbol), source_recommendation=source)
        self.assertEqual(len(self.calls), 2)
        with self.db._get_connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM alert_units').fetchone()[0], 2)
            c.execute("UPDATE notable_flow SET final_outcome='CLOSED' WHERE flow_id='TEST-flow'")
        with self.assertRaisesRegex(ValueError, 'SOURCE_NOT_ELIGIBLE'):
            m.publish_position_exit_alert('TEST', self.rec['contract_symbol'], 'TEST', 20, 2.4, 2,
                'TEST', publication=dict(self.auth, alert_id='TEST-closed'), source_recommendation=self.rec)

    def test_media_requests_abstain_before_enqueue(self):
        m = self.manager(self.transport)
        for request in (
            lambda: m.publish_actionable_alert(self.rec, image_path='/TEST/missing-A.png', publication=self.auth),
            lambda: m.publish_actionable_alert(self.rec, image_path='/TEST/missing-B.png', publication=self.auth),
            lambda: m.publish_actionable_alert(self.rec, use_graphic_card=True, publication=self.auth),
            lambda: m.publish_actionable_alert(self.rec, image_path='', publication=self.auth),
            lambda: m.publish_telegram_alert(self.rec, card_image_path='/TEST/missing.png', publication=self.auth),
        ):
            result = request()
            self.assertEqual(result['status'], 'unsupported')
            self.assertEqual(result['units'], [])
            self.assertEqual(result['capability'], 'text_only')
        self.assertEqual(self.calls, [])
        with self.db._get_connection() as c:
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='alert_units'").fetchone())
        self.now[0] += 60
        result = m.publish_actionable_alert(self.rec, publication=self.auth)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['capability'], 'text_only')
        self.assertEqual(result['media_delivered'], False)
        before = list(self.calls)
        self.assertEqual(m.publish_actionable_alert(self.rec, image_path='/TEST/changed-after-complete.png',
            publication=self.auth)['status'], 'unsupported')
        self.assertEqual(self.calls, before)



