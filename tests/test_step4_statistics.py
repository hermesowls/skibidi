import unittest
from unittest.mock import patch
import test_step3_learning as fixtures


class StatisticsTests(unittest.TestCase):
    setUp = fixtures.EconomicImportTests.setUp
    holding = fixtures.EconomicImportTests.holding

    def api(self, path):
        from hermes_cli import web_server as server
        from starlette.testclient import TestClient
        from plugins.analyst_trader import holding_statistics
        from datetime import datetime, timedelta
        class SnapshotClock(datetime):
            @classmethod
            def now(cls, tz=None):
                # Shared lifecycle fixtures close at entry+2 seconds. Analyze
                # after that synthetic event clock, not before its close.
                return datetime.now(tz) + timedelta(seconds=10)
        with patch.object(server, '_analyst_db_path', return_value=self.db.db_path), patch.object(holding_statistics, 'datetime', SnapshotClock):
            return TestClient(server.app).get(path, headers={'X-Hermes-Session-Token': server._SESSION_TOKEN})

    def test_full_history_statistics_independent_of_display_page(self):
        for i in range(36):
            self.holding('TEST-history-' + str(i), right='C' if i % 2 else 'P')
        with self.db._get_connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM recorded_strategies').fetchone()[0], 180)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM recorded_strategies WHERE event_type IN ('autonomous_trade_executed','autonomous_trade_trimmed','autonomous_trade_closed')").fetchone()[0], 108)
        response = self.api('/api/analyst-trader/strategies?limit=7&offset=0')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn('statistics', body)
        stats = body['statistics']['total']
        self.assertEqual(stats['closed_count'], 36)
        self.assertEqual(stats['gross_realized_pnl'], -3600)
        self.assertEqual(stats['gross_return_pct'], -12.5)
        self.assertIsNone(stats['net_realized_pnl'])
        self.assertEqual(stats['unknown_cost_count'], 36)
        self.assertEqual(len(body['strategies']), 7)
        self.assertTrue(body['pagination']['has_more'])
        later = self.api('/api/analyst-trader/strategies?limit=7&offset=177').json()
        self.assertEqual(later['statistics']['total'], stats)
        self.assertEqual(len(later['strategies']), 3)
        self.assertFalse(later['pagination']['has_more'])

    def test_profitable_trim_is_realized_not_closed_outcome(self):
        self.holding(close=False)
        response = self.api('/api/analyst-trader/strategies')
        self.assertEqual(response.status_code, 200)
        stats = response.json()['statistics']['total']
        self.assertEqual(stats['gross_realized_pnl'], 200)
        self.assertEqual(stats['closed_count'], 0)
        self.assertEqual(stats['open_count'], 1)
        self.assertIsNone(stats['gross_win_rate_pct'])

    def test_empty_history_is_not_zero_performance(self):
        stats = self.api('/api/analyst-trader/strategies').json()['statistics']['total']
        self.assertIsNone(stats['gross_win_rate_pct'])
        self.assertIsNone(stats['gross_realized_pnl'])
        self.assertEqual(stats['holding_count'], 0)

    def test_offline_quotes_are_unknown_not_observed_zero(self):
        response = self.api('/api/analyst-trader/live-quotes?tickers=TEST')
        self.assertEqual(response.status_code, 200)
        quote = response.json()['quotes']['TEST']
        self.assertIsNone(quote['price'])
        self.assertEqual(quote['status'], 'unavailable')

    def test_observed_zero_costs_and_correction_precedence(self):
        from plugins.analyst_trader.learning_store import record_correction
        hid = self.holding()
        for name, at, costs in [('new', '2026-09-22T20:00:00Z', 0), ('old', '2026-09-21T20:00:00Z', 99)]:
            record_correction(self.db, dict(correction_id='TEST-'+name, holding_id=hid, evidence_id='TEST-costs', observed_at=at, total_costs=costs))
        stats = self.api('/api/analyst-trader/strategies').json()['statistics']['total']
        self.assertEqual(stats['net_realized_pnl'], -100)
        self.assertEqual(stats['unknown_cost_count'], 0)
        self.assertEqual(stats['net_win_rate_pct'], 0)

    def test_quarantine_and_missing_entry_excluded_not_fabricated(self):
        self.holding('TEST-quarantine')
        self.holding('TEST-noentry')
        with self.db._get_connection() as conn:
            conn.execute("UPDATE notable_flow SET is_quarantined=1 WHERE flow_id='TEST-quarantine'")
            conn.execute("DELETE FROM recorded_strategies WHERE flow_id='TEST-noentry' AND event_type='autonomous_trade_executed'")
        stats = self.api('/api/analyst-trader/strategies').json()['statistics']['total']
        self.assertEqual(stats['excluded_count'], 2)
        self.assertEqual(stats['closed_count'], 0)
        self.assertIsNone(stats['gross_realized_pnl'])

    def test_api_auth_and_query_errors_are_not_fabricated_success(self):
        from hermes_cli import web_server as server
        from starlette.testclient import TestClient
        self.assertEqual(TestClient(server.app).get('/api/analyst-trader/strategies').status_code, 401)
        with patch.object(self.db.__class__, 'list_recorded_strategies', side_effect=RuntimeError('TEST query error')):
            self.assertEqual(self.api('/api/analyst-trader/strategies').status_code, 500)

    def test_mixed_uneven_tranches_terminal_loss_label_and_unresolved(self):
        from step1_fixtures import lifecycle_evidence
        # One contract trims at 4; three runners exit at 1.5: +200 -150 = +50.
        for right in ('C', 'P'):
            hid = self.holding('TEST-profit-' + right, right=right, close=False)
            self.engine.execute_autonomous_exit(hid, 1.5, **lifecycle_evidence(self.db, hid, 1.5))
        self.holding('TEST-loss', trim=False)
        self.holding('TEST-unresolved', trim=False, close=False)
        body = self.api('/api/analyst-trader/strategies?limit=1&offset=2').json()
        stats = body['statistics']['total']
        self.assertEqual(stats['closed_count'], 3)
        self.assertEqual(stats['open_count'], 1)
        self.assertEqual(stats['gross_realized_pnl'], -300)
        self.assertAlmostEqual(stats['gross_win_rate_pct'], 200/3)
        self.assertEqual(stats['initial_economic_basis'], 3200)
        self.assertEqual(stats['gross_return_pct'], -9.375)
        self.assertEqual(len(body['strategies']), 1)
        self.assertEqual(body['statistics']['by_cohort']['paper_test']['holding_count'], 4)
        self.assertTrue(all(s['mode'] == 'paper_options' for s in body['statistics']['holdings']))
        with self.db._get_connection() as c:
            labels = [r[0] for r in c.execute("SELECT outcome_label FROM recorded_strategies WHERE event_type='autonomous_trade_closed' AND flow_id LIKE 'TEST-profit-%'")]
        self.assertTrue(labels)
        self.assertTrue(all('LOSS' in s for s in labels))

    def test_missing_mark_and_observed_zero_mark_are_distinct(self):
        hid = self.holding(trim=False, close=False)
        with self.db._get_connection() as c:
            c.execute('UPDATE portfolio_holdings SET unrealized_pnl=0,last_price_updated_at=NULL WHERE holding_id=?', (hid,))
        missing = self.api('/api/analyst-trader/strategies').json()['statistics']['total']
        self.assertIsNone(missing['estimated_unrealized_pnl'])
        self.assertEqual(missing['unknown_mark_count'], 1)
        with self.db._get_connection() as c:
            c.execute("UPDATE portfolio_holdings SET last_price_updated_at='2026-09-01T00:00:00Z' WHERE holding_id=?", (hid,))
        zero = self.api('/api/analyst-trader/strategies').json()['statistics']['total']
        self.assertEqual(zero['estimated_unrealized_pnl'], 0)
        self.assertEqual(zero['mark_status'], 'estimated_nonexecutable')

    def test_live_quote_transport_is_mocked_and_errors_non2xx(self):
        from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
        fixtures = {'TEST': {'price': 0, 'change_pct': 0},
                    'ZERO': {'price': 0, 'change_pct': 0, 'source': 'TEST-observed', 'as_of': '2026-09-01T00:00:00Z'},
                    'LEGACY': {'price': 100, 'change_pct': 0}}
        with patch.object(FinvizFetcher, 'fetch_live_quotes', return_value=fixtures) as transport:
            response = self.api('/api/analyst-trader/live-quotes?tickers=TEST,ZERO,LEGACY&live=true')
        self.assertEqual(response.status_code, 200)
        transport.assert_called_once()
        quotes = response.json()['quotes']
        self.assertIsNone(quotes['TEST']['price'])
        self.assertEqual(quotes['ZERO']['price'], 0)
        self.assertEqual(quotes['LEGACY']['status'], 'unknown_asof')
        self.assertIsNone(quotes['LEGACY']['as_of'])
        with patch.object(FinvizFetcher, 'fetch_live_quotes', side_effect=RuntimeError('TEST offline error')):
            self.assertEqual(self.api('/api/analyst-trader/live-quotes?tickers=TEST&live=true').status_code, 502)

    def test_malformed_holding_is_excluded_without_aborting_good_history(self):
        self.holding('TEST-valid')
        self.holding('TEST-malformed')
        with self.db._get_connection() as c:
            c.execute("UPDATE portfolio_holdings SET occ_symbol=NULL WHERE flow_id='TEST-malformed'")
        response = self.api('/api/analyst-trader/strategies')
        self.assertEqual(response.status_code, 200)
        stats = response.json()['statistics']['total']
        self.assertEqual(stats['excluded_count'], 1)
        self.assertEqual(stats['closed_count'], 1)
        self.assertIsNone(stats['gross_realized_pnl'])
        self.assertEqual(stats['known_gross_subtotal'], -100)

    def test_future_correction_not_current_performance(self):
        from plugins.analyst_trader.learning_store import record_correction
        hid = self.holding()
        record_correction(self.db, dict(correction_id='TEST-future', holding_id=hid, evidence_id='TEST-costs', observed_at='2099-01-01T00:00:00Z', total_costs=0))
        stats = self.api('/api/analyst-trader/strategies').json()['statistics']['total']
        self.assertIsNone(stats['net_realized_pnl'])
        self.assertEqual(stats['excluded_count'], 1)
        self.assertEqual(stats['closed_count'], 0)

    def test_portfolio_null_cash_is_not_a_manufactured_balance(self):
        self.db.get_portfolio('autonomous_ai')
        with self.db._get_connection() as conn:
            conn.execute("UPDATE portfolios SET cash_balance=NULL WHERE portfolio_id='autonomous_ai'")
        stats = self.api('/api/analyst-trader/portfolio').json()['portfolios']['autonomous_ai']
        self.assertIsNone(stats['cash_balance'])
        self.assertIsNone(stats['total_value'])
        self.assertIsNone(stats['win_rate_pct'])

    def test_auth_and_corrupt_disposable_database_all_relevant_routes(self):
        from hermes_cli import web_server as server
        from starlette.testclient import TestClient
        from pathlib import Path
        bad = Path(self.tmp.name)/'corrupt.db'
        bad.write_bytes(b'TEST not SQLite')
        routes = ('portfolio', 'portfolio-holdings', 'strategies', 'live-quotes')
        for route in routes:
            path = '/api/analyst-trader/' + route
            self.assertEqual(TestClient(server.app).get(path).status_code, 401)
            if route != 'live-quotes':
                with patch.object(server, '_analyst_db_path', return_value=str(bad)):
                    res = TestClient(server.app).get(path, headers={'X-Hermes-Session-Token': server._SESSION_TOKEN})
                    self.assertEqual(res.status_code, 500)

    def test_real_chart_route_allowed_outside_and_symlink_confinement(self):
        from hermes_cli import web_server as server
        from pathlib import Path
        root = Path(self.tmp.name)
        charts = root/'charts'
        charts.mkdir()
        image = charts/'fixture.svg'
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        outside = root/'outside.svg'
        outside.write_text('TEST outside chart')
        link = charts/'escape.svg'
        link.symlink_to(outside)
        self.holding('TEST-chart')
        with patch.object(server, 'get_hermes_home', return_value=root):
            for path, expected in ((image, 200), (outside, 403), (link, 403)):
                with self.db._get_connection() as c:
                    c.execute('UPDATE notable_flow SET local_chart_path=? WHERE flow_id=?', (str(path), 'TEST-chart'))
                response = self.api('/api/analyst-trader/flow-chart/TEST-chart')
                self.assertEqual(response.status_code, expected)

