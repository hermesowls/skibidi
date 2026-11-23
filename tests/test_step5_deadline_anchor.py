"""Original admission, not mutable execution JSON, anchors research max hold."""
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import test_step5_kian_closeout as closeout
import test_step5_kian_repair as producer
from step5_test_clock import ASOF, wall_clock


class AdmissionAnchor(unittest.TestCase):
    def snapshot(self, db):
        with db._get_connection() as c:
            return {t: [tuple(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY rowid')]
                    for t in ('portfolio_holdings', 'portfolios', 'notable_flow', 'recorded_strategies')}

    def test_original_admission_rejects_mutable_clock_and_missing_evidence(self):
        from plugins.analyst_trader.paper_monitor import process_quote
        from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
        variants = ('receipt', 'start', 'self_consistent', 'missing_admission',
                    'malformed_admission', 'missing_lifecycle', 'malformed_start',
                    'malformed_holding', 'malformed_journal')
        for variant in variants:
            with self.subTest(variant=variant):
                def probe(db, hid, result):
                    d = closeout.Deadline()
                    original, intent = d.origin(db, hid)
                    q = d.quote(db, hid, 3., 10, 'anchor')
                    shifted = (datetime.fromisoformat(intent['research_lifecycle']['entered_at']) + timedelta(seconds=5)).isoformat()
                    with db._get_connection() as c:
                        if variant in ('receipt', 'start', 'self_consistent'):
                            if variant != 'start': original['receipt']['timestamp'] = shifted
                            if variant != 'receipt':
                                intent['research_lifecycle']['entered_at'] = shifted
                                intent['research_lifecycle']['exit_deadline'] = (datetime.fromisoformat(shifted)+timedelta(seconds=10)).isoformat()
                            original['intent_json'] = json.dumps(dict(intent=intent))
                            c.execute("UPDATE recorded_strategies SET payload_json=? WHERE holding_id=? AND event_type='autonomous_trade_executed'", (json.dumps(original), hid))
                        elif variant == 'missing_admission':
                            c.execute("DELETE FROM recorded_strategies WHERE event_type='paper_execution_decision'")
                        elif variant in ('malformed_admission', 'missing_lifecycle', 'malformed_start'):
                            row = c.execute("SELECT payload_json FROM recorded_strategies WHERE event_type='paper_execution_decision'").fetchone()
                            data = json.loads(row[0])
                            if variant == 'missing_lifecycle': data.pop('research_lifecycle')
                            elif variant == 'malformed_start': data['research_lifecycle']['entered_at'] = 'not-a-clock'
                            c.execute("UPDATE recorded_strategies SET payload_json=? WHERE event_type='paper_execution_decision'", ('{' if variant == 'malformed_admission' else json.dumps(data),))
                        elif variant == 'malformed_holding':
                            c.execute('UPDATE portfolio_holdings SET created_at=? WHERE holding_id=?', ('bad', hid))
                        else:
                            c.execute("UPDATE recorded_strategies SET timestamp='bad' WHERE event_type='autonomous_trade_executed'")
                    before = self.snapshot(db)
                    for evidence in (q, dict(q, quote=None)):
                        update = process_quote(db, DualPortfolioEngine(db), hid, **evidence)
                        self.assertEqual(update.get('exit_status'), 'INVALID_DEADLINE')
                        self.assertIsNone(update['economic_receipt'])
                        self.assertEqual(self.snapshot(db), before)
                    with self.assertRaises(ValueError):
                        DualPortfolioEngine(db).execute_autonomous_exit(hid, 3., **q)
                    self.assertEqual(self.snapshot(db), before)
                producer.ProducerContext().run_producers(True, execute=True, max_hold_seconds=10, lifecycle_probe=probe)

    def test_precise_delayed_admission_preserves_original_deadline_and_noquote(self):
        from plugins.analyst_trader.paper_monitor import process_quote
        from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
        ticks = [0]
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                ticks[0] += 1
                at = ASOF + timedelta(microseconds=123456*ticks[0])
                return at.astimezone(tz) if tz else at.replace(tzinfo=None)
        def probe(db, hid, result):
            d = closeout.Deadline()
            origin, intent = d.origin(db, hid)
            start = datetime.fromisoformat(intent['research_lifecycle']['entered_at'])
            self.assertGreater(datetime.fromisoformat(origin['receipt']['timestamp']), start)
            self.assertNotEqual(start.microsecond, 0)
            e = DualPortfolioEngine(db)
            before = self.snapshot(db)
            pre = d.quote(db, hid, 3., 9.999999, 'pre')
            self.assertIsNone(process_quote(db, e, hid, **dict(pre, quote=None)))
            self.assertEqual(self.snapshot(db), before)
            self.assertIsNone(process_quote(db, e, hid, **pre)['operation'])
            exact = d.quote(db, hid, 3., 10, 'exact')
            before = self.snapshot(db)
            pending = process_quote(db, e, hid, **dict(exact, quote=None))
            self.assertEqual(pending['exit_status'], 'EXIT_PENDING')
            self.assertEqual(self.snapshot(db), before)
            self.assertEqual(process_quote(db, e, hid, **exact)['outcome'], 'CLOSED_MAX_HOLD')
            self.assertIsNone(process_quote(db, DualPortfolioEngine(db), hid, **exact))
        # Only external clocks vary; real producer/ARM/admission/monitor execute.
        with wall_clock(ASOF), patch('autonomous_risk_manager.datetime', Clock), \
                patch('plugins.analyst_trader.db.datetime', Clock), \
                patch('plugins.analyst_trader.strategy_logger.datetime', Clock):
            getattr(producer.ProducerContext().run_producers, '__wrapped__')(producer.ProducerContext(), True,
                execute=True, max_hold_seconds=10, lifecycle_probe=probe)
