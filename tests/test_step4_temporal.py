"""Actual authenticated API with real entry/trim SQLite; only DB path/clock mocked."""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import test_step4_statistics as fixtures

class TemporalTests(unittest.TestCase):
    setUp = fixtures.StatisticsTests.setUp
    holding = fixtures.StatisticsTests.holding
    api = fixtures.StatisticsTests.api

    def temporal(self, kind, field, stamp, valid=False):
        hid = self.holding(close=kind == 'closed')
        with self.db._get_connection() as c:
            row = c.execute('SELECT * FROM recorded_strategies WHERE holding_id=? AND event_type=?',
                            (hid, 'autonomous_trade_'+kind)).fetchone()
            if field == 'timestamp':
                c.execute('UPDATE recorded_strategies SET timestamp=? WHERE trace_id=?', (stamp,row['trace_id']))
            else:
                payload=json.loads(row['payload_json']); payload['timestamp']=stamp
                c.execute('UPDATE recorded_strategies SET payload_json=? WHERE trace_id=?', (json.dumps(payload),row['trace_id']))
        body=self.api('/api/analyst-trader/strategies').json()['statistics']
        self.assertEqual(body['total']['excluded_count'], 0 if valid else 1)
        if not valid:
            self.assertIsNone(body['total']['gross_realized_pnl'])
            self.assertTrue(body['holdings'][0]['reason'])

    def mark_case(self, stamp, expected):
        hid=self.holding(trim=False,close=False)
        with self.db._get_connection() as c:
            c.execute('UPDATE portfolio_holdings SET last_price_updated_at=?,market_value=0,unrealized_pnl=0,current_price=0 WHERE holding_id=?',(stamp,hid))
        response=self.api('/api/analyst-trader/portfolio').json()
        s=response['portfolios']['autonomous_ai']
        if expected == 'unknown':
            self.assertIsNone(s['total_value'])
            self.assertIsNone(s['unrealized_pnl'])
            self.assertIsNone(s['open_market_value'])
            self.assertEqual(s['unknown_mark_count'],1)
            self.assertEqual(s['valuation_status'],'unknown')
        else:
            self.assertEqual(s['open_market_value'],0)
            self.assertEqual(s['unrealized_pnl'],0)
            self.assertEqual(s['unknown_mark_count'],0)
            self.assertEqual(s['stale_mark_count'],int(expected=='stale'))
            self.assertIn('60s',s['mark_policy'])
        if stamp == 'not-a-date': print('ACTUAL_INVALID_MARK_RESPONSE '+json.dumps(response))

    def test_mark_observed_zero_fresh(self):
        self.mark_case(datetime.now(timezone.utc).isoformat(),'fresh')

    def test_mark_aged_zero_explicit_stale_policy(self):
        self.mark_case('2000-01-01T00:00:00Z','stale')

    def test_valid_past_partial_and_cutoff_equality(self):
        from plugins.analyst_trader import holding_statistics
        from hermes_cli import web_server as server
        from starlette.testclient import TestClient
        hid=self.holding(close=False)
        cutoff=datetime.now(timezone.utc)
        with self.db._get_connection() as c:
            for row in c.execute('SELECT * FROM recorded_strategies WHERE holding_id=?',(hid,)).fetchall():
                payload=json.loads(row['payload_json']); payload['timestamp']=cutoff.isoformat()
                c.execute('UPDATE recorded_strategies SET timestamp=?,payload_json=? WHERE trace_id=?',
                          (cutoff.isoformat(),json.dumps(payload),row['trace_id']))
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None): return cutoff
        with patch.object(server,'_analyst_db_path',return_value=self.db.db_path), patch.object(holding_statistics,'datetime',Clock):
            s=TestClient(server.app).get('/api/analyst-trader/strategies',headers={'X-Hermes-Session-Token':server._SESSION_TOKEN}).json()['statistics']['total']
        self.assertEqual((s['gross_realized_pnl'],s['open_count'],s['closed_count'],s['excluded_count']),(200,1,0,0))

for label,stamp in [('date_only','2000-01-01'),('invalid','not-a-date'),('future','2099-01-01T00:00:00Z'),('naive','2026-01-01T00:00:00'),('missing',None),('calendar','2026-02-30T00:00:00Z')]:
    def mark_check(self,s=stamp): self.mark_case(s,'unknown')
    setattr(TemporalTests,f'test_mark_{label}',mark_check)

for kind in ('executed','trimmed','closed'):
    for field in ('timestamp','payload'):
        for label,stamp in [('future','2099-01-01T00:00:00Z'),('malformed','not-a-date'),('naive','2026-01-01T00:00:00')]:
            def check(self,k=kind,f=field,s=stamp): self.temporal(k,f,s)
            setattr(TemporalTests,f'test_{kind}_{field}_{label}',check)
for field in ('timestamp','payload'):
    def check(self,f=field): self.temporal('trimmed',f,'2000-01-01T00:00:00Z')
    setattr(TemporalTests,f'test_trim_before_entry_{field}',check)
