"""Actual authenticated API snapshots for mounted holding-mark contract tests.

Run under the offline Step4 guard. Only disposable SQLite is mutated; real
entry/journal/statistics/route business code is used. No positive outcome labels
are fabricated. MARK_API_SNAPSHOTS is serialized unchanged into the UI harness.
"""
import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import test_step4_statistics as fixtures


class MarkContractTests(unittest.TestCase):
    setUp = fixtures.StatisticsTests.setUp
    holding = fixtures.StatisticsTests.holding

    def test_actual_api_snapshots(self):
        from hermes_cli import web_server as server
        from plugins.analyst_trader import holding_statistics
        from starlette.testclient import TestClient
        hid = self.holding(close=False, trim=False)
        cutoff = datetime.now(timezone.utc) + timedelta(seconds=10)
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cutoff
        def request():
            with patch.object(server, '_analyst_db_path', return_value=self.db.db_path), patch.object(holding_statistics, 'datetime', Clock):
                response = TestClient(server.app).get('/api/analyst-trader/portfolio', headers={'X-Hermes-Session-Token': server._SESSION_TOKEN})
            self.assertEqual(response.status_code, 200)
            return response.json()
        snapshots = {}
        for name, stamp in (
            ('hour24', '2026-09-01T24:00:00Z'),
            ('microsecond_future', (cutoff + timedelta(microseconds=1)).isoformat()),
            ('valid_zero', cutoff.isoformat()),
            ('valid_stale', (cutoff - timedelta(seconds=61)).isoformat()),
        ):
            # Observed zero, not a fabricated successful trade outcome.
            with self.db._get_connection() as conn:
                conn.execute('UPDATE portfolio_holdings SET last_price_updated_at=?, current_price=0, market_value=0, unrealized_pnl=0 WHERE holding_id=?', (stamp, hid))
            body = request()
            p = body['portfolios']['autonomous_ai']
            h = next(h for h in p['statistics']['holdings'] if h['holding_id'] == hid)
            bad = name in ('hour24', 'microsecond_future')
            self.assertEqual(h['mark_freshness'], 'unknown' if bad else 'stale' if name == 'valid_stale' else 'fresh')
            self.assertEqual(h['estimated_market_value'], None if bad else 0)
            self.assertEqual(p['unknown_mark_count'], int(bad))
            snapshots[name] = body
        # A NEW API snapshot accepts the formerly-future observation only after
        # its snapshot cutoff advances. The old response is never altered.
        cutoff += timedelta(seconds=1)
        with self.db._get_connection() as conn:
            conn.execute('UPDATE portfolio_holdings SET last_price_updated_at=? WHERE holding_id=?', (snapshots['microsecond_future']['portfolios']['autonomous_ai']['open_positions'][0]['last_price_updated_at'], hid))
        snapshots['recovery'] = request()
        self.assertEqual(snapshots['recovery']['portfolios']['autonomous_ai']['statistics']['holdings'][0]['estimated_market_value'], 0)
        print('MARK_API_SNAPSHOTS ' + json.dumps(snapshots))
