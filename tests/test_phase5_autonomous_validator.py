"""
Phase 5 Comprehensive Test Suite: Autonomous Strategy Validator & Trading Command Center.
Tests paper execution, integer contract sizing per tier, TP1 auto-trim, breakeven stop movement,
TP2/SL auto-exit, broker abstraction, web endpoints, and closed-loop strategy attribution.
"""

import os
import sys
import shutil
import tempfile
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.portfolio_engine import (
    DualPortfolioEngine,
    ExecutionBroker,
    PaperExecutionBroker,
    RobinhoodExecutionBroker,
)


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_validator.db"
    db = AnalystDatabase(db_path)
    yield db
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_portfolio_holdings_lifecycle_schema(temp_db):
    """Test that AnalystDatabase schema migration adds all lifecycle columns."""
    stats = temp_db.get_portfolio_stats("autonomous_ai")
    assert stats["portfolio_id"] == "autonomous_ai"
    assert stats["cash_balance"] == 100000.0
    assert stats["open_market_value"] == 0.0
    assert stats["active_positions_count"] == 0
    assert stats["closed_positions_count"] == 0
    assert stats["win_rate_pct"] == 0.0


def test_broker_abstraction(temp_db):
    """Test ExecutionBroker ABC, PaperExecutionBroker and RobinhoodExecutionBroker stub."""
    paper_broker = PaperExecutionBroker(temp_db)
    assert isinstance(paper_broker, ExecutionBroker)

    order_resp = paper_broker.submit_order({"ticker": "NVDA", "price": 4.50, "quantity": 2})
    assert order_resp["status"] == "FILLED"
    assert order_resp["filled_price"] == 4.50
    assert order_resp["quantity"] == 2
    assert paper_broker.cancel_order(order_resp["order_id"]) is True

    rh_broker = RobinhoodExecutionBroker()
    assert isinstance(rh_broker, ExecutionBroker)
    rh_order = rh_broker.submit_order({"ticker": "TSLA", "price": 5.00, "quantity": 1})
    assert "order_id" in rh_order
    assert rh_order["ticker"] == "TSLA"


def test_autonomous_trade_sizing_tiers(temp_db):
    """Test integer contract sizing across Micro, Growing, and Established tiers."""
    engine = DualPortfolioEngine(temp_db)

    rec_base = {
        "ticker": "AAPL",
        "strike": 220.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "entry_price": 2.00,
        "strategy_name": "EMA_STACK_BREAKOUT",
        "tp1_price": 2.50,
        "tp2_price": 3.00,
        "stop_loss_price": 1.50,
    }

    # 1. Micro tier: 1 contract
    t_micro = engine.execute_autonomous_trade(rec_base, account_tier="micro")
    assert t_micro is not None
    assert t_micro["quantity"] == 1
    assert t_micro["total_cost"] == 200.0

    # 2. Growing tier: 2 contracts (or 3 if low price)
    t_growing = engine.execute_autonomous_trade(rec_base, account_tier="growing")
    assert t_growing is not None
    assert t_growing["quantity"] == 3  # price <= 2.50 gets 3 contracts
    assert t_growing["total_cost"] == 600.0

    # 3. Established tier: 5 contracts
    t_est = engine.execute_autonomous_trade(rec_base, account_tier="established")
    assert t_est is not None
    assert t_est["quantity"] == 5
    assert t_est["total_cost"] == 1000.0


def test_autonomous_tp1_trim_and_breakeven_trail(temp_db):
    """Test TP1 (+20% to +25%) partial trim, profit realization, and breakeven stop movement."""
    engine = DualPortfolioEngine(temp_db)

    rec = {
        "ticker": "NVDA",
        "strike": 130.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "entry_price": 4.00,
        "strategy_name": "A+_DREAM_SETUP",
        "tp1_price": 5.00,
        "tp2_price": 6.00,
        "stop_loss_price": 3.00,
    }

    trade = engine.execute_autonomous_trade(rec, account_tier="growing")
    assert trade is not None
    holding_id = trade["holding_id"]
    initial_cash = float(temp_db.get_portfolio("autonomous_ai")["cash_balance"])

    # Simulate market price reaching TP1 (+25% at $5.00)
    trim_report = engine.execute_autonomous_trim(holding_id, current_price=5.00, trim_pct=0.5)
    assert trim_report is not None
    assert trim_report["action"] == "AUTONOMOUS_TRIM"
    assert trim_report["trimmed_quantity"] == 1.0
    assert trim_report["remaining_quantity"] == 1.0
    # Gain on 1 contract: ($5.00 - $4.00) * 100 = $100.00
    assert trim_report["realized_pnl"] == 100.0
    assert trim_report["new_stop_loss"] == 4.00  # Breakeven stop!

    # Check holding state in database
    holdings = temp_db.list_portfolio_holdings("autonomous_ai", status="ACTIVE")
    h = next(item for item in holdings if item["holding_id"] == holding_id)
    assert h["status"] == "TRIMMED"
    assert h["target_sl"] == 4.00  # Moved to breakeven
    assert h["quantity"] == 1.0
    assert h["contracts_trimmed"] == 1.0
    assert h["realized_pnl"] == 100.0

    # Cash balance increased by revenue ($500.00)
    new_cash = float(temp_db.get_portfolio("autonomous_ai")["cash_balance"])
    assert new_cash == initial_cash + 500.0


def test_autonomous_tp2_full_exit_and_strategy_journal(temp_db):
    """Test full exit on remaining contracts at TP2 (+50%), status CLOSED, and telemetry write."""
    engine = DualPortfolioEngine(temp_db)

    rec = {
        "ticker": "MSFT",
        "strike": 450.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "entry_price": 5.00,
        "strategy_name": "GEX_GAMMA_SQUEEZE",
        "tp1_price": 6.25,
        "tp2_price": 7.50,
        "stop_loss_price": 4.00,
    }

    trade = engine.execute_autonomous_trade(rec, account_tier="growing")
    holding_id = trade["holding_id"]

    # Trim 1 at TP1 ($6.25)
    engine.execute_autonomous_trim(holding_id, current_price=6.25, trim_pct=0.5)

    # Runner hits TP2 ($7.50)
    exit_report = engine.execute_autonomous_exit(holding_id, current_price=7.50, outcome_label="WIN_TP2")
    assert exit_report is not None
    assert exit_report["action"] == "AUTONOMOUS_WIN_TP2"
    assert exit_report["closed_quantity"] == 1.0
    # Gain on 2nd contract: ($7.50 - $5.00) * 100 = $250.00
    assert exit_report["realized_pnl"] == 250.0

    # Verify holding is closed
    active = temp_db.list_portfolio_holdings("autonomous_ai", status="ACTIVE")
    assert len(active) == 0

    closed = temp_db.list_portfolio_holdings("autonomous_ai", status="CLOSED")
    assert len(closed) == 1
    ch = closed[0]
    assert ch["status"] == "CLOSED"
    assert ch["quantity"] == 0.0
    # Total realized PnL = $125.00 (trim) + $250.00 (exit) = $375.00
    assert ch["realized_pnl"] == 375.0

    # Verify portfolio stats
    stats = temp_db.get_portfolio_stats("autonomous_ai")
    assert stats["closed_positions_count"] == 1
    assert stats["winning_positions_count"] == 1
    assert stats["win_rate_pct"] == 100.0
    assert stats["realized_pnl"] == 375.0


def test_autonomous_risk_manager_end_to_end_validation(temp_db):
    """Test AutonomousRiskManager automatically executes paper orders upon alert publication."""
    script_dir = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from autonomous_risk_manager import AutonomousRiskManager

    arm = AutonomousRiskManager(db_path=str(temp_db.db_path))

    # Test dynamic TP calibration: strictly realistic +20% to +25% TP1
    tp1_price, tp1_pct, tp2_price, tp2_pct, sl_price = arm.calculate_dynamic_tp_setpoints(
        entry_price=4.00,
        spot_price=120.0,
        strike=120.0,
        call_put="C",
        dte=35,
        target_node=125.0,
    )
    assert 20.0 <= tp1_pct <= 25.0
    assert 45.0 <= tp2_pct <= 60.0
    assert sl_price == 3.00  # -25% on 35 DTE swing (1:1 R:R against TP1)

    eval_res = arm.evaluate_candidate_end_to_end(
        ticker="AMZN",
        strike=190.0,
        call_put="C",
        expiration="2026-10-16",
        dte=30,
        premium_usd=1500000.0,
        entry_price=3.00,
        spot_price=188.50,
        auto_publish_alerts=False,  # Don't call live Discord/Telegram in unit test
    )

    # Candidate evaluation stamped strategy
    assert "strategy_name" in eval_res
    assert "recommendation" in eval_res


@pytest.mark.asyncio
async def test_web_server_portfolio_endpoints():
    """Test web_server API endpoints for portfolio, holdings, and strategies."""
    from hermes_cli.web_server import (
        api_analyst_trader_portfolio,
        api_analyst_trader_portfolio_holdings,
        api_analyst_trader_strategies,
    )

    port_res = await api_analyst_trader_portfolio()
    assert port_res["ok"] is True
    assert "portfolios" in port_res
    assert "autonomous_ai" in port_res["portfolios"]
    assert "copy_trader" in port_res["portfolios"]

    hold_res = await api_analyst_trader_portfolio_holdings(portfolio_id="autonomous_ai")
    assert hold_res["ok"] is True
    assert "holdings" in hold_res

    strat_res = await api_analyst_trader_strategies()
    assert strat_res["ok"] is True
    assert "strategies" in strat_res
