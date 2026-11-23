"""Actual producer + monitor behavior under unrelated surrounding wall years."""
import unittest
from datetime import datetime, timezone, timedelta
from step5_test_clock import ASOF, wall_clock
import test_step5_kian_repair as repair

class ClockPortability(unittest.TestCase):
    def test_same_asof_producer_and_monitor_in_two_surrounding_years(self):
        from plugins.analyst_trader.paper_monitor import process_quote
        from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
        from test_step5_kian_closeout import Deadline
        snapshots=[]
        for year in (2025, 2028):
            with self.subTest(year=year), wall_clock(datetime(year, 1, 15, tzinfo=timezone.utc)):
                self.assertEqual(repair.datetime.now(timezone.utc).year, year)
                def probe(db, hid, result):
                    origin, intent=Deadline().origin(db,hid)
                    self.assertEqual(intent['research_lifecycle']['entered_at'], ASOF.isoformat())
                    evidence=Deadline().quote(db,hid,3.)
                    update=process_quote(db,DualPortfolioEngine(db),hid,**evidence)
                    self.assertEqual(update['outcome'],'CLOSED_MAX_HOLD')
                    snapshots.append(dict(candidate=result['research_candidate'],
                        decision=result['learning_decision'], lifecycle=intent['research_lifecycle'],
                        pnl=update['economic_receipt']['realized_pnl'],
                        quantity=update['economic_receipt']['quantity'], outcome=update['outcome']))
                repair.ProducerContext().run_producers(True,execute=True,max_hold_seconds=10,lifecycle_probe=probe)
        self.assertEqual(len(snapshots),2)
        self.assertEqual(snapshots[0],snapshots[1])

    def test_frozen_asof_still_rejects_expired_and_future_observations(self):
        for year in (2025,2028):
            with self.subTest(year=year), wall_clock(datetime(year,1,15,tzinfo=timezone.utc)):
                repair.ProducerContext().run_producers(True,change={'observed_at':(ASOF+timedelta(seconds=1)).isoformat()},expected='INCOMPLETE')
                repair.ProducerContext().run_producers(True,change={'observed_at':(ASOF-timedelta(seconds=121)).isoformat()},expected='INCOMPLETE')
                repair.ProducerContext().run_producers(True,invalid='future_policy')
                repair.ProducerContext().run_producers(True,execute=True,expiry='2026-09-22',expected='REJECTED')
