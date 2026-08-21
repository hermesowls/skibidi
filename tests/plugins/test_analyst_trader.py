"""Unit tests for Analyst Trader plugin components."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.parser import TradeSignalParser, DiscordBackfillEngine
from plugins.analyst_trader.analyst_learning import CategoryAutoDiscoverer, AnalystStyleLearner
from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
from plugins.analyst_trader.tools import analyst_trading_tool


class TestAnalystDatabase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_analyst_trading.db"
        self.db = AnalystDatabase(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_analyst_registration(self):
        analyst = self.db.register_analyst("ch_123", "jon-and-kian", "Jon & Kian")
        self.assertIsNotNone(analyst)
        self.assertEqual(analyst["channel_name"], "jon-and-kian")
        self.assertEqual(analyst["display_name"], "Jon & Kian")

        analysts = self.db.list_analysts()
        self.assertEqual(len(analysts), 1)

    def test_save_raw_message_deduplication(self):
        inserted1 = self.db.save_raw_message("m_1", "ch_123", "jon-and-kian", "Jon & Kian", "u_1", "BUY SPY 500 CALL")
        inserted2 = self.db.save_raw_message("m_1", "ch_123", "jon-and-kian", "Jon & Kian", "u_1", "BUY SPY 500 CALL")
        self.assertTrue(inserted1)
        self.assertFalse(inserted2)

    def test_position_lifecycle(self):
        pos = self.db.create_position(
            position_id="pos_1",
            analyst_name="Jon & Kian",
            channel_id="ch_123",
            ticker="SPY",
            asset_type="option",
            direction="call",
            entry_price=2.00,
            strike=500.0,
            expiration="11/20"
        )
        self.assertEqual(pos["status"], "OPEN")
        self.assertEqual(pos["entry_price"], 2.00)

        # Trim
        trimmed = self.db.update_position_trim_or_close("pos_1", exit_price=3.00, status="TRIMMED")
        self.assertEqual(trimmed["status"], "TRIMMED")
        self.assertEqual(trimmed["realized_pnl"], 100.0)  # (3 - 2) * 1 * 100

        # Close
        closed = self.db.update_position_trim_or_close("pos_1", exit_price=4.00, status="CLOSED")
        self.assertEqual(closed["status"], "CLOSED")
        self.assertEqual(closed["realized_pnl"], 200.0)


class TestTradeSignalParser(unittest.TestCase):

    def test_parse_options_alert(self):
        signal = TradeSignalParser.parse_message("BTO RARE $50 CALL 11/20 @ 2.50")
        self.assertIsNotNone(signal)
        self.assertEqual(signal["action"], "ENTRY")
        self.assertEqual(signal["ticker"], "RARE")
        self.assertEqual(signal["strike"], 50.0)
        self.assertEqual(signal["direction"], "call")
        self.assertEqual(signal["price"], 2.50)

    def test_parse_embed_alert(self):
        embeds = [{
            "title": "FRMI Spike Alert",
            "description": "BUY FRMI 7.5 CALL at 0.50"
        }]
        signal = TradeSignalParser.parse_message("", embeds)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["ticker"], "FRMI")
        self.assertEqual(signal["strike"], 7.5)


class TestPortfolioEngine(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_portfolio.db"
        self.db = AnalystDatabase(self.db_path)
        self.engine = DualPortfolioEngine(self.db)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_copy_trade_execution(self):
        alert = {
            "action": "ENTRY",
            "ticker": "SPY",
            "asset_type": "option",
            "direction": "call",
            "price": 2.00,
            "strike": 500.0,
            "expiration": "11/20"
        }
        report = self.engine.execute_copy_trade(alert, "Jon & Kian")
        self.assertIsNotNone(report)
        self.assertEqual(report["action"], "BUY_ENTRY")
        self.assertEqual(report["ticker"], "SPY")

        summary = self.engine.get_portfolio_summary()
        self.assertEqual(summary["copy_trader"]["open_positions_count"], 1)

    def test_autonomous_trade_execution(self):
        # Save analyst style first
        self.db.save_analyst_style(
            analyst_name="JON & KIAN",
            preferred_tickers=["SPY", "QQQ"],
            avg_holding_hours=24.0,
            win_rate=75.0,
            avg_roi_pct=30.0,
            preferred_dte_min=7,
            preferred_dte_max=30,
            strategy_summary="Momentum breakout option trader",
            rules={}
        )

        report = self.engine.evaluate_autonomous_trade_setup("SPY", "BULLISH")
        self.assertIsNotNone(report)
        self.assertEqual(report["action"], "AUTONOMOUS_ENTRY")
        self.assertEqual(report["ticker"], "SPY")


class TestLLMTradeReviewer(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_reviewer.db"
        self.db = AnalystDatabase(self.db_path)
        from plugins.analyst_trader.llm_reviewer import LLMTradeReviewer
        self.reviewer = LLMTradeReviewer()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_audit_raw_message_action_mismatch(self):
        # Create an OPEN position
        self.db.create_position(
            position_id="pos_open_1",
            analyst_name="Jon & Kian",
            channel_id="ch_1",
            ticker="HPE",
            asset_type="option",
            direction="call",
            entry_price=2.00
        )

        positions = self.db.list_positions(analyst_name="Jon & Kian")
        raw_msg = {
            "message_id": "msg_99",
            "analyst_name": "Jon & Kian",
            "content": "sold rest of HPE at +68% gains, fully out"
        }

        audit_res = self.reviewer.audit_raw_message_against_tracker(raw_msg, positions)
        self.assertEqual(audit_res["discrepancy_type"], "ACTION_MISMATCH")
        self.assertEqual(audit_res["ticker"], "HPE")
        self.assertEqual(audit_res["corrected_data"]["action"], "EXIT")

    def test_save_reviewer_audit_and_reconciliation(self):
        # Save an audit record
        audit_record = self.db.save_reviewer_audit(
            audit_id="aud_100",
            message_id="msg_100",
            analyst_name="Jon & Kian",
            ticker="AXTI",
            discrepancy_type="MISSED_SIGNAL",
            original_data=None,
            corrected_data={"action": "ENTRY", "ticker": "AXTI", "price": 1.50, "asset_type": "option", "direction": "call"},
            confidence_score=0.92,
            reasoning="Missed BTO alert",
            status="NEEDS_REVIEW"
        )
        self.assertEqual(audit_record["status"], "NEEDS_REVIEW")

        # Execute reconciliation
        rec = self.db.reconcile_position_from_audit("aud_100")
        self.assertEqual(rec["status"], "RECONCILED")

        # Confirm position was created in DB
        positions = self.db.list_positions(analyst_name="Jon & Kian")
        self.assertTrue(any(p["ticker"] == "AXTI" for p in positions))


if __name__ == "__main__":
    unittest.main()
