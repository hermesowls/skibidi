"""Automated Regression Suite for Phase 3: The Holy Grail Learning Flywheel.

Validates:
  1. Data Lake Helper Methods (analyst_styles and flow_candidate_analytics).
  2. AnalystStyleLearner: chat context parsing (theses, tags, sizing) + CBOE chart TA (EMA stack, 200 EMA).
  3. CandidateCorrelationEngine: backfill of notable flow into flow_candidate_analytics with case studies.
  4. FlowClassifierEngine Factor G: Analyst Style Attribution bonus and anti-pattern penalties.
  5. AutonomousRiskManager: Dream Setup analyst edge validation.
  6. Web Server REST Endpoints: /api/analyst-trader/analyst-styles & /api/analyst-trader/flow-candidates.
"""

import os
import sys
import json
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCRIPTS_DIR = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from plugins.analyst_trader.db import AnalystDatabase, get_db_path
from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
from flow_classifier import FlowClassifierEngine  # type: ignore[import-not-found]
from candidate_correlation_engine import CandidateCorrelationEngine, generate_occ_symbol  # type: ignore[import-not-found]
from autonomous_risk_manager import AutonomousRiskManager  # type: ignore[import-not-found]


@pytest.fixture(scope="module")
def db():
    return AnalystDatabase(get_db_path())


def test_db_analyst_styles_methods(db):
    """Verify save_analyst_style, get_analyst_style, and list_analyst_styles."""
    rules = {
        "high_conviction_setups": ["Swing continuation above 200 EMA"],
        "forbidden_setups": ["Sub-200 lottos"],
        "win_rate_pct": 82.5,
    }
    db.save_analyst_style(
        analyst_name="TestAnalyst",
        preferred_tickers=["AAPL", "MSFT"],
        avg_holding_hours=48.0,
        win_rate=82.5,
        avg_roi_pct=45.0,
        preferred_dte_min=21,
        preferred_dte_max=60,
        strategy_summary="Test strategy summary.",
        rules=rules,
    )

    style = db.get_analyst_style("TestAnalyst")
    assert style is not None
    assert style["analyst_name"] == "TestAnalyst"
    assert style["preferred_tickers"] == ["AAPL", "MSFT"]
    assert style["rules_json"]["win_rate_pct"] == 82.5

    styles = db.list_analyst_styles()
    assert any(s["analyst_name"] == "TestAnalyst" for s in styles)


def test_db_flow_candidate_analytics_methods(db):
    """Verify save_flow_candidate_analytics and list_flow_candidate_analytics."""
    record = {
        "analytics_id": "fca_test_flow_999",
        "flow_id": "test_flow_999",
        "ticker": "NVDA",
        "contract_symbol": "NVDA  261016C00150000",
        "flow_tier": "Tier 1: Mega-Cap / ETF Institutional Block",
        "conviction_score": 88.5,
        "entry_price": 5.20,
        "peak_price": 12.50,
        "trough_price": 4.10,
        "mfe_pct": 140.4,
        "mae_pct": 21.2,
        "intraday_vol": 15000,
        "initial_oi": 2000,
        "next_day_oi": 3500,
        "oi_change_pct": 75.0,
        "is_overnight_hold": 1,
        "outcome_label": "WIN_RUNNER_7X",
        "correlations_json": {"case_study_autopsy": "Test autopsy on NVDA call."},
    }

    db.save_flow_candidate_analytics(record)
    results = db.list_flow_candidate_analytics(ticker="NVDA", limit=5)
    assert len(results) >= 1
    found = next((r for r in results if r["analytics_id"] == "fca_test_flow_999"), None)
    assert found is not None
    assert found["ticker"] == "NVDA"
    assert found["mfe_pct"] == 140.4
    assert found["outcome_label"] == "WIN_RUNNER_7X"
    assert "NVDA call" in found["correlations_json"]["case_study_autopsy"]


def test_analyst_style_learner_attribution(db):
    """Verify AnalystStyleLearner parses chat context, computes chart TA, and derives philosophy."""
    learner = AnalystStyleLearner(db)

    # Test Eva (24 closed trades with rich chat notes)
    eva_res = learner.analyze_analyst("Eva")
    assert eva_res["analyst_name"] == "Eva"
    assert eva_res["total_trades"] >= 20
    assert eva_res["win_rate"] > 50.0
    assert len(eva_res["preferred_tickers"]) > 0
    assert "strategy_summary" in eva_res
    assert len(eva_res["rules"]["high_conviction_setups"]) > 0
    assert "ta_requirements" in eva_res["rules"]
    assert "setup_breakdown" in eva_res["rules"]

    # Test AB (10 closed trades)
    ab_res = learner.analyze_analyst("AB")
    assert ab_res["analyst_name"] == "AB"
    assert ab_res["win_rate"] >= 65.0
    assert "CVNA" in ab_res["preferred_tickers"] or "IREN" in ab_res["preferred_tickers"]
    assert "risk-free" in ab_res["rules"]["sizing_discipline"].lower()


def test_candidate_correlation_engine_backfill(db):
    """Verify CandidateCorrelationEngine backfills all notable flow into flow_candidate_analytics."""
    engine = CandidateCorrelationEngine(str(db.db_path))
    audit = engine.run_candidate_correlation_audit()

    assert audit["total_candidates_analyzed"] >= 600
    assert audit["total_runners_detected"] > 0
    assert audit["overnight_holds_detected"] > 0

    analytics = db.list_flow_candidate_analytics(limit=10)
    assert len(analytics) == 10
    for a in analytics:
        assert a["contract_symbol"]
        assert len(a["contract_symbol"]) == 21
        assert a["entry_price"] > 0
        assert a["peak_price"] >= a["entry_price"]
        assert a["correlations_json"].get("case_study_autopsy")


def test_flow_classifier_factor_g_analyst_confluence(db):
    """Verify FlowClassifierEngine Factor G rewards analyst edge and penalizes anti-patterns."""
    clf = FlowClassifierEngine(str(db.db_path))

    # 1. Candidate matching AB's high-win-rate edge on CVNA (30 DTE Call)
    match_res = clf.classify_and_score_flow(
        ticker="CVNA",
        strike=80.0,
        call_put="CALL",
        expiration="2026-10-16",
        dte=30,
        premium_usd=150000.0,
        vol_to_oi=2.5,
        is_sweep=True,
        spot_price=75.0,
        entry_price=2.50,
        technical_data={"ema_stack_state": "FULL_BULLISH_STACK", "is_above_200_ema": True},
    )
    assert any("ANALYST EDGE: AB" in tag for tag in match_res["flow_tags"])
    assert match_res["score_badge"] in ("STRONG", "ELITE")

    # 2. Anti-pattern: Sub-200 EMA 3 DTE Call lotto
    lotto_res = clf.classify_and_score_flow(
        ticker="XYZ",
        strike=50.0,
        call_put="CALL",
        expiration="2026-09-20",
        dte=3,
        premium_usd=80000.0,
        vol_to_oi=1.5,
        is_sweep=False,
        spot_price=45.0,
        entry_price=1.00,
        technical_data={"ema_stack_state": "FULL_BEARISH_STACK", "is_above_200_ema": False},
    )
    assert any("ANTI-PATTERN: SUB-200 LOTTO" in tag for tag in lotto_res["flow_tags"])
    assert lotto_res["conviction_score"] < 50.0
    assert lotto_res["score_badge"] == "SPECULATIVE"


def test_autonomous_risk_manager_analyst_edge(db):
    """Verify AutonomousRiskManager identifies analyst style confluence in dream setup validation."""
    mgr = AutonomousRiskManager(str(db.db_path))
    val = mgr.validate_dream_setup_confluence(
        conviction_score=88.0,
        dte=30,
        vol_to_oi=2.5,
        is_sweep=True,
        gex_regime="Clear Runway",
        ticker="CVNA",
    )
    assert val["is_dream_setup"] is True
    assert val["analyst_edge"] is not None
    assert "AB" in val["analyst_edge"]


@pytest.mark.asyncio
async def test_web_server_endpoints(db, monkeypatch):
    """Verify Web Server exposes analyst styles and flow candidate case studies."""
    from hermes_cli import web_server
    monkeypatch.setattr(web_server, "_analyst_db_path", lambda: db.db_path)

    styles_resp = await web_server.api_analyst_trader_analyst_styles()
    assert styles_resp["ok"] is True
    assert styles_resp["count"] >= 1
    assert any(s["analyst_name"] in ("Eva", "AB", "Jon", "Kian", "Jon & Kian") for s in styles_resp["styles"])

    candidates_resp = await web_server.api_analyst_trader_flow_candidates(limit=20)
    assert candidates_resp["ok"] is True
    assert candidates_resp["count"] >= 1
    assert "case_study_autopsy" in candidates_resp["candidates"][0]["correlations_json"]
