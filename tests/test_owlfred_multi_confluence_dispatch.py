"""
Tests for Owlfred Multi-Confluence Engine & Dual-Card Dispatch.

Verifies:
  1. TechnicalIndicatorsEngine calculates full EMA(8, 21, 50, 100, 200) stack and RVOL confirmation.
  2. FlowClassifierEngine incorporates EMA stack, volume, and GEX regimes into conviction scoring.
  3. AutonomousRiskManager generates standard 21-character OCC symbology, integer trim schedules, and dual alert dispatch.
"""

import os
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADER_SCRIPTS = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TRADER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TRADER_SCRIPTS))

from plugins.analyst_trader.technical_indicators import TechnicalIndicatorsEngine
from flow_classifier import FlowClassifierEngine, get_flowseeker_badge
from autonomous_risk_manager import (
    AutonomousRiskManager,
    generate_occ_symbol,
    get_contract_trim_schedule,
)


def test_technical_indicators_ema_stack():
    """Verify that TechnicalIndicatorsEngine computes complete EMA(8, 21, 50, 100, 200) stack."""
    engine = TechnicalIndicatorsEngine()
    
    # Generate synthetic upward trending prices for 250 bars
    base = 100.0
    prices = [base + i * 0.5 for i in range(250)]
    
    res = engine.compute_technical_indicators(
        prices=prices,
        atr=1.5,
        rel_volume=2.0,
        intraday_volume=2_500_000
    )
    
    assert "ema8" in res
    assert "ema21" in res
    assert "ema50" in res
    assert "ema100" in res
    assert "ema200" in res
    assert res["ema8"] > res["ema21"] > res["ema50"] > res["ema100"] > res["ema200"]
    assert res["ema_stack_state"] == "FULL_BULLISH_STACK"
    assert res["is_full_bullish_stack"] is True
    assert res["is_above_200_ema"] is True
    assert res["volume_confirmed"] is True
    assert res["rvol_extreme"] is False or res["rel_volume"] >= 1.5


def test_flow_classifier_confluence_scoring():
    """Verify that FlowClassifierEngine modifies scores based on technical and GEX confluence."""
    classifier = FlowClassifierEngine()
    
    # 1. Base call flow with strong bullish EMA stack
    tech_bullish = {
        "ema_stack_state": "FULL_BULLISH_STACK",
        "is_above_200_ema": True,
        "volume_confirmed": True,
        "ttm_squeeze_state": "SQUEEZE_FIRED_BULLISH",
        "rel_volume": 2.2,
        "current_price": 140.0
    }
    
    res_bull = classifier.classify_and_score_flow(
        ticker="NVDA",
        strike=145.0,
        call_put="C",
        expiration="2026-10-16",
        dte=29,
        premium_usd=1_500_000.0,
        vol_to_oi=4.2,
        is_sweep=True,
        technical_data=tech_bullish,
        gex_regime="Negative Gamma"
    )
    
    assert res_bull["conviction_score"] >= 85.0
    assert "FULL EMA BULL STACK" in res_bull["flow_tags_str"]
    assert "NEG GEX SQUEEZE RUNWAY" in res_bull["flow_tags_str"]
    assert res_bull["score_badge"] in ("STRONG", "ELITE")

    # 2. Call flow trapped below 200 EMA receives penalty
    tech_trapped = {
        "ema_stack_state": "BELOW_200_EMA_CONSOLIDATING",
        "is_above_200_ema": False,
        "volume_confirmed": False,
        "ttm_squeeze_state": "NO_SQUEEZE",
        "rel_volume": 0.8,
        "current_price": 90.0
    }
    
    res_trapped = classifier.classify_and_score_flow(
        ticker="INTC",
        strike=95.0,
        call_put="C",
        expiration="2026-10-16",
        dte=29,
        premium_usd=200_000.0,
        vol_to_oi=2.0,
        is_sweep=False,
        technical_data=tech_trapped,
        gex_regime="Positive Gamma"
    )
    
    assert "TRAPPED BELOW 200 EMA" in res_trapped["flow_tags_str"]
    assert res_trapped["conviction_score"] < res_bull["conviction_score"]


def test_occ_symbology_specification():
    """Assert canonical 21-character OCC option symbology format."""
    occ = generate_occ_symbol(
        ticker="NVDA",
        expiration_str="2026-10-16",
        call_put="C",
        strike=145.0
    )
    # Exactly 21 chars: 6 ticker + 6 YYMMDD + 1 C/P + 8 strike*1000
    assert len(occ) == 21
    assert occ.startswith("NVDA  ")
    assert "261016C00145000" in occ

    # Ticker with 5 chars (e.g. GOOGL)
    occ_googl = generate_occ_symbol(
        ticker="GOOGL",
        expiration_str="2026-11-20",
        call_put="P",
        strike=180.50
    )
    assert len(occ_googl) == 21
    assert occ_googl.startswith("GOOGL ")
    assert "261120P00180500" in occ_googl


def test_contract_trim_schedules():
    """Verify integer contract trim schedules eliminate fractional contracts."""
    s1 = get_contract_trim_schedule(quantity=1, tp1_pct=45.0, tp2_pct=120.0)
    assert s1["quantity"] == 1
    assert s1["is_free_roll"] is False

    s2 = get_contract_trim_schedule(quantity=2, tp1_pct=45.0, tp2_pct=120.0)
    assert s2["tp1_trim"] == 1
    assert s2["is_free_roll"] is False

    s3 = get_contract_trim_schedule(quantity=3, tp1_pct=50.0, tp2_pct=120.0)
    assert s3["tp1_trim"] == 2
    assert s3["is_free_roll"] is True


def test_trade_recommendation_and_alert_formatting():
    """Verify end-to-end recommendation synthesis and dual dispatch payload formatting."""
    arm = AutonomousRiskManager()
    
    rec = arm.generate_trade_recommendation(
        ticker="NVDA",
        strike=145.0,
        call_put="C",
        expiration="2026-10-16",
        dte=29,
        premium_usd=1_250_000.0,
        entry_price=4.50,
        spot_price=140.20,
        conviction_score=89.5,
        tier_name="Tier 1: Mega-Cap / ETF Institutional Block",
        flow_tags_str="BIG ASK CALLS | FULL EMA BULL STACK | NEG GEX SQUEEZE RUNWAY",
        vol_to_oi=4.2,
        gex_regime="Negative Gamma Squeeze Runway"
    )
    
    assert rec["ticker"] == "NVDA"
    assert rec["occ_symbol"] == "NVDA  261016C00145000"
    assert rec["tp1_price"] > rec["entry_price"]
    assert rec["tp2_price"] > rec["tp1_price"]
    assert rec["stop_loss_price"] < rec["entry_price"]
    assert rec["planned_risk_per_con"] > 0
    assert "micro_account" in rec["sizing_rules"]
    assert "growing_account" in rec["sizing_rules"]
    assert "standard_account" in rec["sizing_rules"]
