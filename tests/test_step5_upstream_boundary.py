"""Step5 actual producer capability probe, NOT full integrated acceptance.

Only the external Finviz/chart/quote/delivery boundaries receive TEST inputs.
Quant, classifier, ARM, persistence and OWLFRED are not mocked.
"""
import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
from typing import Any


class UpstreamBoundary(unittest.TestCase):
    def test_real_producers_retain_proxy_abstention(self):
        from plugins.analyst_trader.db import AnalystDatabase
        from flow_ingestion_engine import FlowIngestionEngine
        from owlfred_engine import eval_ticker
        with tempfile.TemporaryDirectory(prefix='TEST-step5-dataset-') as tmp:
            db = AnalystDatabase(Path(tmp) / 'TEST.sqlite')
            calls = []
            policy = dict(publishing_authorized=True, alert_id='TEST-step5-alert',
                          revision=1, policy_version='TEST-explicit-publication',
                          flow_id='flow_TEST-step5-raw')
            def transport(unit):
                calls.append(unit)
                return dict(state='succeeded', receipt='TEST-not-a-real-receipt')
            market = dict(ticker='TEST', price=100, current_price=100, volume=1000000,
                          change_pct=5, rel_volume=4, atr=2,
                          ta_info={'ema_stack_state': 'TEST_OBSERVED_STACK'},
                          event_info={'binary_event_risk': 'TEST_PENDING'})
            options = dict(delivery_transport=transport,
                           delivery_destinations=[('discord', 'TEST-channel'), ('telegram', 'TEST-chat')])
            with patch('plugins.analyst_trader.finviz_fetcher.FinvizFetcher.fetch_ticker_metrics', return_value=market):
                producer = FlowIngestionEngine(db, publication_policy=lambda source: policy,
                    discord_token='', chart_loader=lambda **kw: None,
                    observation_reader=lambda parsed, msg: {'entry_price': 2, 'spot_price': 100}, **options)
                msg = dict(id='TEST-step5-raw', content='TEST 100 C 10/16/2026 $1M SWEEP',
                           timestamp='2026-09-19T00:00:00Z')
                self.assertTrue(producer._process_message(msg, 'TEST-channel', 'TEST-fixture', 'equity'))
                flow: Any = producer.last_evaluation
                self.assertIsNotNone(flow, 'actual upstream evaluation must have completed')
                owl: Any = eval_ticker('TEST', db_path=str(db.db_path), flow_id=policy['flow_id'],
                                  publication=policy, observation_reader=lambda source: {'spot_price':100}, **options)
                self.assertIn('quant_result', owl, 'must reach OWLFRED positive source route, not early deny')
                self.assertFalse(producer._process_message(msg, 'TEST-channel', 'TEST-fixture', 'equity'))
            for result in (flow, owl):
                self.assertEqual(result['quant_result']['fail_closed_status'], 'FAIL_CLOSED_DATA_UNAVAILABLE')
                self.assertFalse(result['is_dream_setup'])
                self.assertEqual(result['quant_result']['ofi_metrics'], {})
                self.assertIsNone(result['quant_result']['directional_alpha']['p_bullish'])
                self.assertIsNone(result['quant_result']['directional_alpha']['brier_score'])
                self.assertEqual(result['alert_delivery']['status'], 'not_requested')
                self.assertIsNone(result['paper_trade'])
                self.assertIsNone(result['learning_decision'])
            with db._get_connection() as c:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM raw_messages').fetchone()[0], 1)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM notable_flow').fetchone()[0], 1)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_holdings').fetchone()[0], 0)
                exists = c.execute("SELECT 1 FROM sqlite_master WHERE name='alert_units'").fetchone()
                units = c.execute('SELECT COUNT(*) FROM alert_units').fetchone()[0] if exists else 0
                self.assertEqual(units, 0)
            self.assertEqual(calls, [])
            self.assertEqual(producer.ingest_unusual_whales_feeds()['status'], 'unavailable')
            self.assertEqual(producer.ingest_flowseeker_scanner_feeds()['status'], 'unavailable')
            print('STEP5_BLOCKER_TRACE ' + json.dumps(dict(
                source_id=policy['flow_id'], raw_id=msg['id'], raw_count=1, notable_count=1,
                flow_status=flow['quant_result']['fail_closed_status'],
                owlfred_status=owl['quant_result']['fail_closed_status'],
                alert_units=units, transport_calls=len(calls), holdings=0,
                disposition='I1 blocked: real proxy abstains; no substituted business result'), sort_keys=True))
            if '--require-publication' in sys.argv:
                self.assertGreater(units, 0, 'I1 requires actual upstream durable card obligations; no qualified publication path exists')
