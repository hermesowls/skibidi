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
        assert pos is not None
        self.assertEqual(pos["status"], "OPEN")
        self.assertEqual(pos["entry_price"], 2.00)

        # Trim (50% trim of 1.0 contract -> 0.5 contracts trimmed)
        trimmed = self.db.update_position_trim_or_close("pos_1", exit_price=3.00, status="TRIMMED")
        assert trimmed is not None
        self.assertEqual(trimmed["status"], "TRIMMED")
        self.assertEqual(trimmed["realized_pnl"], 50.0)  # (3 - 2) * 0.5 * 100

        # Close
        closed = self.db.update_position_trim_or_close("pos_1", exit_price=4.00, status="CLOSED")
        assert closed is not None
        self.assertEqual(closed["status"], "CLOSED")
        self.assertEqual(closed["realized_pnl"], 150.0)  # $50.00 from trim + $100.00 from final exit



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

    def test_parse_trim_and_close_alerts(self):
        from plugins.analyst_trader.parser import extract_trim_ratio
        self.assertEqual(extract_trim_ratio("trimmed 50% at 3.50"), 0.50)
        self.assertEqual(extract_trim_ratio("sold 1/2 of SPY @ 4.00"), 0.50)
        self.assertEqual(extract_trim_ratio("fully out of SPY"), 1.0)
        self.assertEqual(extract_trim_ratio("leaving runner"), 0.85)

        sig_trim = TradeSignalParser.parse_message("TRIM SPY 500 CALL @ 3.50 (+75%)")
        assert sig_trim is not None
        self.assertEqual(sig_trim["action"], "TRIM")
        self.assertEqual(sig_trim["ticker"], "SPY")
        self.assertEqual(sig_trim["price"], 3.50)
        self.assertEqual(sig_trim["pct_roi"], 75.0)

        sig_close = TradeSignalParser.parse_message("STC SPY 500C @ 4.50 fully out")
        assert sig_close is not None
        self.assertEqual(sig_close["action"], "EXIT")
        self.assertEqual(sig_close["ticker"], "SPY")
        self.assertEqual(sig_close["price"], 4.50)

    def test_trade_event_logging_on_trim(self):
        pos = self.db.create_position(
            position_id="pos_trim_test",
            analyst_name="Eva",
            channel_id="ch_eva",
            ticker="QQQ",
            asset_type="option",
            direction="call",
            entry_price=2.00,
            strike=450.0,
            expiration="08/21"
        )
        assert pos is not None

        # Trim 50% at $3.00 (+50% gain)
        trimmed = self.db.update_position_trim_or_close("pos_trim_test", exit_price=3.00, status="TRIMMED", trim_ratio=0.5)
        assert trimmed is not None

        # Verify position list includes trade event trims array
        positions = self.db.list_positions(analyst_name="Eva")
        self.assertEqual(len(positions), 1)
        p = positions[0]
        self.assertIn("trims", p)
        self.assertTrue(len(p["trims"]) >= 1)
        self.assertEqual(p["trims"][0]["price"], 3.00)
        self.assertEqual(p["trims"][0]["gain_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()

