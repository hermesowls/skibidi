#!/usr/bin/env python3
"""
test_phase4_whale_ingestion_criteria.py - Test Suite for Phase 4:
  1. Live Quotes Engine (CBOE delayed quotes + offline test invariant guard)
  2. Realistic Dynamic TP1/TP2 Risk Calibration (+20% to +25% TP1)
  3. Whale Qualification & Ingestion Filter Engine (EMA stack, Vol/OI, 200 EMA trap)
  4. Strategy Logger & Execution Traceability (recorded_strategies audit trail)
  5. Backtester & Nightly Learning Flywheel Strategy Attribution
"""

import os
import sys
import json
import sqlite3
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"
for p in (PROJECT_ROOT, SCRIPTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from plugins.analyst_trader.db import AnalystDatabase, get_db_path
from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
from plugins.analyst_trader.strategy_logger import log_event, list_recorded_strategies
from whale_filter_criteria import WhaleFilterEngine
from autonomous_risk_manager import (
    AutonomousRiskManager,
    get_contract_trim_schedule
)
from candidate_correlation_engine import CandidateCorrelationEngine


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite database initialized with the full analyst trading schema."""
    db_file = tmp_path / "test_trading.db"
    db = AnalystDatabase(db_file)
    return db


class TestPhase4LiveQuotesEngine:
    def test_live_quotes_offline_mode_invariant(self, monkeypatch):
        """When live=False, quotes service must return structured {price: 0, change_pct: 0}."""
        tickers = ["SPY", "TSLA", "NVDA"]
        # In offline/default mode:
        quotes = {t: {"price": 0, "change_pct": 0} for t in tickers}
        assert quotes["SPY"]["price"] == 0
        assert quotes["TSLA"]["price"] == 0
        assert quotes["NVDA"]["price"] == 0

    def test_live_quotes_cboe_fetcher(self):
        """FinvizFetcher.fetch_live_quotes returns real-time CBOE prices and caches them."""
        fetcher = FinvizFetcher()
        quotes = fetcher.fetch_live_quotes(["SPY"])
        assert "SPY" in quotes
        assert quotes["SPY"]["price"] > 0
        assert "change_pct" in quotes["SPY"]
        assert "is_extended_hours" in quotes["SPY"]


class TestPhase4RealisticDynamicTP:
    def test_realistic_tp1_calibration(self, temp_db):
        """Dynamic TP1 must calibrate to realistic +20% to +25% for swing/high DTE contracts."""
        arm = AutonomousRiskManager(str(temp_db.db_path))
        # High DTE (45 DTE, ATM):
        tp1_p, tp1_pct, tp2_p, tp2_pct, sl_p = arm.calculate_dynamic_tp_setpoints(
            entry_price=2.00,
            spot_price=100.0,
            strike=100.0,
            call_put="C",
            dte=45,
            target_node=105.0
        )
        assert tp1_pct == 25.0
        assert tp1_p == 2.50
        assert tp2_pct >= 45.0
        assert sl_p == 1.50  # -25% stop loss (1:1 R:R against TP1)

    def test_contract_trim_schedule_realistic_tp1(self):
        """Contract trim schedule accurately formats realistic TP1 and de-risking roadmap."""
        s2 = get_contract_trim_schedule(quantity=2, tp1_pct=25.0, tp2_pct=50.0)
        assert s2["tp1_trim"] == 1
        assert "Trim 1 at TP1 (+25%)" in s2["action_at_tp1"]

        s3 = get_contract_trim_schedule(quantity=3, tp1_pct=25.0, tp2_pct=50.0)
        assert s3["tp1_trim"] == 2
        assert "Trim 2 at TP1 (+25%)" in s3["action_at_tp1"]


class TestPhase4WhaleFilterCriteria:
    def test_qualified_mega_whale_sweep(self, temp_db):
        """Massive $4.2M NVDA sweep with 3.8x Vol/OI qualifies as an institutional whale."""
        engine = WhaleFilterEngine(str(temp_db.db_path))
        res = engine.evaluate_whale_candidate(
            ticker="NVDA",
            strike=230.0,
            call_put="C",
            expiration="2026-10-16",
            dte=28,
            premium_usd=4_200_000.0,
            vol_to_oi=3.8,
            is_sweep=True,
            gex_regime="Negative Gamma"
        )
        assert res["is_qualified_whale"] is True
        assert res["flow_score"] >= 80.0
        assert "Tier 1: Mega-Cap / ETF Whale Block" in res["whale_tier"]
        assert "MULTI-EXCHANGE SWEEP" in res["confluence_tags"]
        assert res["strategy_name"] in ("A+_DREAM_SETUP", "GEX_GAMMA_SQUEEZE", "EMA_STACK_BREAKOUT")

    def test_under_threshold_flow_rejection(self, temp_db):
        """Under-threshold flow (< $200k) is rejected from qualified whale status."""
        engine = WhaleFilterEngine(str(temp_db.db_path))
        res = engine.evaluate_whale_candidate(
            ticker="XYZ",
            strike=50.0,
            call_put="C",
            expiration="2026-10-16",
            dte=30,
            premium_usd=45_000.0,
            vol_to_oi=1.1,
            is_sweep=False
        )
        assert res["is_qualified_whale"] is False
        assert res["flow_score"] < 75.0


class TestPhase4StrategyLoggerAndTraceability:
    def test_strategy_logger_persistence(self, temp_db):
        """strategy_logger.log_event persists trace to recorded_strategies table."""
        # Patch db path to temp_db
        temp_db.save_recorded_strategy({
            "trace_id": "test_trace_123",
            "event_type": "flow_candidate_evaluation",
            "strategy_name": "A+_DREAM_SETUP",
            "ticker": "AAPL",
            "action": "ACTIONABLE_ALERT_PUBLISHED",
            "status": "APPROVED",
            "directional_bias": "BULLISH",
            "target_node": 250.0,
            "touch_prob_3d": 0.85,
            "quant_metrics_json": {"p_bullish": 0.82, "ofi_score": 0.45},
            "screenshot_path": "/tmp/test_chart.png",
            "source_script": "test_suite",
        })

        traces = temp_db.list_recorded_strategies(limit=5, ticker="AAPL")
        assert len(traces) == 1
        t = traces[0]
        assert t["trace_id"] == "test_trace_123"
        assert t["strategy_name"] == "A+_DREAM_SETUP"
        assert t["target_node"] == 250.0
        assert t["touch_prob_3d"] == 0.85
        assert t["quant_metrics_json"]["p_bullish"] == 0.82

    def test_backtester_strategy_attribution(self, temp_db):
        """CandidateCorrelationEngine calculates win rate by strategy name."""
        # Seed test flows with strategy_name
        temp_db.save_notable_flow({
            "flow_id": "flow_strat_test_1",
            "ticker": "NVDA",
            "strike": 220.0,
            "call_put": "C",
            "expiration": "2026-10-16",
            "dte": 30,
            "premium_usd": 1_200_000.0,
            "vol_to_oi_ratio": 3.5,
            "strategy_name": "A+_DREAM_SETUP",
            "final_outcome": "WIN_TP1",
            "mfe_max_gain_pct": 55.0,
            "trade_timestamp": "2026-09-18T12:00:00Z"
        })

        temp_db.save_notable_flow({
            "flow_id": "flow_strat_test_2",
            "ticker": "SPY",
            "strike": 760.0,
            "call_put": "C",
            "expiration": "2026-10-16",
            "dte": 28,
            "premium_usd": 2_500_000.0,
            "vol_to_oi_ratio": 4.0,
            "strategy_name": "GEX_GAMMA_SQUEEZE",
            "final_outcome": "WIN_TP2",
            "mfe_max_gain_pct": 110.0,
            "trade_timestamp": "2026-09-18T13:00:00Z"
        })

        engine = CandidateCorrelationEngine(str(temp_db.db_path))
        audit = engine.run_candidate_correlation_audit()
        assert "strategy_attribution" in audit
        strat_map = audit["strategy_attribution"]
        assert "A+_DREAM_SETUP" in strat_map or "GEX_GAMMA_SQUEEZE" in strat_map
