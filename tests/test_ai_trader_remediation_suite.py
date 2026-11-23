"""
Comprehensive Remediation Test Suite for AI Trader Independent Review Findings.
Covers:
- Priority 1: Removal of synthetic outcome fabrication & ingestion fallbacks (L1, F1)
- Priority 2: Options accounting (put PnL), price validation, idempotency, atomic ledger, sequential TP1->TP2 monitoring (L6, L7, F2, F3, F4)
- Priority 3: Strategy logger lineage, append-only persistence, full telemetry retention (L8, F8)
- Priority 4: Historical TA point-in-time filtering, sample size gate, Factor G direction alignment, free-roll math (L2, L3, L4, L5, F10)
- Priority 5: Truthful API error responses, honest quote metadata, truthful UI stats (Review 3 P1, F9)
- Priority 6: Strict HERMES_HOME resolution and chart path confinement (Review 3 P1, F7, F11)
"""

import os
import sys
import math
import shutil
import tempfile
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def isolated_env(tmp_path):
    """Hermetic test environment setting isolated HOME and HERMES_HOME."""
    home_dir = tmp_path / "user_home"
    hermes_home = tmp_path / "hermes_isolated"
    home_dir.mkdir(parents=True, exist_ok=True)
    hermes_home.mkdir(parents=True, exist_ok=True)
    (hermes_home / "data").mkdir(parents=True, exist_ok=True)
    (hermes_home / "charts").mkdir(parents=True, exist_ok=True)
    (hermes_home / "flow_charts").mkdir(parents=True, exist_ok=True)
    (hermes_home / ".env").write_text("DISCORD_BOT_TOKEN=mock_test_token\nTELEGRAM_BOT_TOKEN=mock_test_token\n")

    old_env = os.environ.copy()
    os.environ["HOME"] = str(home_dir)
    os.environ["HERMES_HOME"] = str(hermes_home)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["DISCORD_BOT_TOKEN"] = "mock_test_token"
    os.environ["TELEGRAM_BOT_TOKEN"] = "mock_test_token"
    os.environ["TELEGRAM_ALLOWED_USERS"] = "12345"

    # TEST-only external boundaries. Dummy tokens are not network permission.
    response = MagicMock(status=200, status_code=200)
    response.json.return_value = {'ok': True, 'id': 'TEST-discord-receipt'}
    response.read.return_value = b'{"ok":true,"result":{"message_id":"TEST-telegram-receipt"}}'
    response.__enter__.return_value = response
    with patch('urllib.request.urlopen', return_value=response), \
         patch('requests.sessions.Session.request', return_value=response), \
         patch('plugins.analyst_trader.finviz_fetcher.FinvizFetcher.fetch_ticker_metrics', return_value={}):
        yield {"home": home_dir, "hermes_home": hermes_home}

    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def temp_db(isolated_env):
    """Returns an isolated AnalystDatabase."""
    from plugins.analyst_trader.db import AnalystDatabase
    db_path = isolated_env["hermes_home"] / "data" / "analyst_trading.db"
    db = AnalystDatabase(db_path)
    return db


# ==============================================================================
# PRIORITY 1: REMOVE SYNTHETIC OUTCOMES & FABRICATED EVIDENCE (L1, F1)
# ==============================================================================

def test_p1_candidate_correlation_engine_no_synthetic_outcomes(temp_db):
    """
    Finding L1 / F1: Candidate correlation engine must NEVER invent MFE/MAE or WIN labels
    from flow_score or premium for unobserved trades. Unobserved trades must stay MONITORING.
    """
    from candidate_correlation_engine import CandidateCorrelationEngine

    # Insert an unobserved flow candidate in notable_flow with no market quote
    flow_id = "test_unobserved_flow_001"
    temp_db.save_notable_flow({
        "flow_id": flow_id,
        "ticker": "NVDA",
        "strike": 130.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "dte": 30,
        "premium_usd": 800000.0,
        "vol_to_oi_ratio": 3.5,
        "is_sweep": 1,
        "flow_score": 90.0,
        "final_outcome": "MONITORING",
        "mfe_max_gain_pct": 0.0,
        "mae_max_drawdown_pct": 0.0,
    })

    engine = CandidateCorrelationEngine(str(temp_db.db_path))
    engine.run_candidate_correlation_audit()

    conn = temp_db._get_connection()
    cur = conn.execute("SELECT final_outcome, mfe_max_gain_pct, mae_max_drawdown_pct FROM notable_flow WHERE flow_id = ?", (flow_id,))
    row = cur.fetchone()
    # Must NOT have fabricated a 220% MFE or WIN_TP2 / WIN_RUNNER_7X from the flow_score
    assert row[0] == "MONITORING", f"Expected MONITORING to remain unmutated, got {row[0]}"
    assert row[1] == 0.0 or row[1] is None, f"MFE must not be synthetically invented, got {row[1]}"


def test_p1_flow_ingestion_no_fallback_identities_and_prices(isolated_env, temp_db):
    """
    Finding F1: Flow ingestion engine must not invent fallback strikes (100.0),
    expirations (2026-10-16), or synthetic prices (strike * 0.025). Missing identifiers
    must be marked UNRESOLVED without generating actionable orders.
    """
    from flow_ingestion_engine import FlowIngestionEngine

    engine = FlowIngestionEngine(str(temp_db.db_path))
    # Raw message missing strike and expiration
    raw_msg = {"channel_id": "123", "id": "msg_001", "content": "AAPL massive bull flow detected"}
    res = engine.parse_raw_flow_message(raw_msg)

    # Ingestion should NOT inject a fake strike 100.0 or fake expiration 2026-10-16
    if res:
        assert res.get("strike") is None or res.get("is_resolved") is False, "Unobserved strike must not be defaulted to 100.0"
        assert res.get("expiration") is None or res.get("is_resolved") is False, "Unobserved expiration must not be defaulted"


# ==============================================================================
# PRIORITY 2: OPTIONS ACCOUNTING, IDEMPOTENCY, PRICE VALIDATION & TP1 RUNNER (L7, F2, F3, L6, F4)
# ==============================================================================

def test_p2_put_option_accounting_profit_and_loss(temp_db):
    """
    Finding L7 / F3: Long options (both calls and puts) profit when exit_price > entry_price.
    Buying 2 puts at $4.00 and exiting at $5.00 MUST yield +$200 profit, NOT -$200.
    """
    from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine

    engine = DualPortfolioEngine(temp_db)
    rec = {
        "ticker": "TSLA",
        "strike": 200.0,
        "call_put": "P",
        "direction": "put",
        "expiration": "2026-10-16",
        "entry_price": 4.00,
        "strategy_name": "INSTITUTIONAL_PUT_SWEEP",
        "flow_id": "put_flow_001",
    }
    from step1_fixtures import paper_intent, persist_source, lifecycle_evidence
    rec = paper_intent(rec, quantity=1)
    persist_source(temp_db,rec)
    trade = engine.execute_autonomous_trade(rec, account_tier="growing")
    assert trade is not None
    holding_id = trade["holding_id"]

    # Exit long put at $5.00 (gain of $1.00 per share = +$100.00 per contract)
    # One-contract TP1 is the supported terminal trim, not an arbitrary exit label.
    exit_rep = engine.execute_autonomous_trim(holding_id, current_price=5.00, **lifecycle_evidence(temp_db,holding_id,5,'trim'))
    assert exit_rep is not None
    assert exit_rep["realized_pnl"] == 100.0, f"Expected +100.0 profit on long put, got {exit_rep['realized_pnl']}"

    # Verify portfolio stats reflects the profit
    stats = temp_db.get_portfolio_stats("autonomous_ai")
    assert stats["realized_pnl"] == 100.0


def test_p2_price_validation_and_idempotent_orders(temp_db):
    """
    Finding F2: Reject negative, zero, or non-finite prices.
    Reject duplicate orders with the same flow_id to prevent double-execution.
    """
    from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine

    engine = DualPortfolioEngine(temp_db)

    # 1. Negative price must be rejected
    rec_neg = {
        "ticker": "AAPL",
        "strike": 220.0,
        "call_put": "C",
        "entry_price": -2.00,
        "flow_id": "neg_price_flow",
    }
    from step1_fixtures import paper_intent, persist_source, lifecycle_evidence
    rec_neg = paper_intent(rec_neg)
    with pytest.raises(ValueError, match=r"Out of bounds entry_price"):
        engine.execute_autonomous_trade(rec_neg)

    # 2. NaN / Infinite price must be rejected
    rec_nan = {
        "ticker": "AAPL",
        "strike": 220.0,
        "call_put": "C",
        "entry_price": float("nan"),
        "flow_id": "nan_price_flow",
    }
    rec_nan = paper_intent(rec_nan)
    with pytest.raises(ValueError, match=r"Out of bounds entry_price"):
        engine.execute_autonomous_trade(rec_nan)

    # 3. Duplicate flow_id must be idempotent (must not create two active holdings)
    rec_valid = {
        "ticker": "NVDA",
        "strike": 130.0,
        "call_put": "C",
        "entry_price": 4.00,
        "flow_id": "idempotent_flow_123",
    }
    rec_valid = paper_intent(rec_valid, quantity=1)
    persist_source(temp_db,rec_valid)
    t1 = engine.execute_autonomous_trade(rec_valid, account_tier="growing")
    assert t1 is not None
    t2 = engine.execute_autonomous_trade(rec_valid, account_tier="growing")
    assert t1 == t2
    # Second submission must return existing holding or None, but NOT create second holding
    holdings = temp_db.list_portfolio_holdings("autonomous_ai", status="ACTIVE")
    assert len([h for h in holdings if h.get("flow_id") == "idempotent_flow_123"]) == 1


def test_p2_sequential_tp1_to_tp2_monitoring(temp_db):
    """
    Finding L6 / F4: Scheduled monitor_and_update_positions must TRIM position at TP1,
    move stop to breakeven, and subsequent monitor passes must close runner at breakeven stop.
    It must never close an unrelated contract with different expiration.
    """
    from autonomous_risk_manager import AutonomousRiskManager
    from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine

    arm = AutonomousRiskManager(db_path=str(temp_db.db_path))
    engine = DualPortfolioEngine(temp_db)

    # 1. Ingest holding with 2 contracts in autonomous_ai portfolio
    flow_id = "amd_flow_pass"
    rec = {
        "ticker": "AMD",
        "strike": 150.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "entry_price": 4.00,
        "tp1_price": 5.00,
        "tp2_price": 6.00,
        "stop_loss_price": 3.00,
        "flow_id": flow_id,
    }
    from step1_fixtures import paper_intent, persist_source, lifecycle_evidence
    rec = paper_intent(rec)
    persist_source(temp_db,rec)
    trade = engine.execute_autonomous_trade(rec, account_tier="growing")
    holding_id = trade["holding_id"]

    # Also insert an unrelated holding with same ticker/strike/right but DIFFERENT expiration
    rec_unrelated = {
        "ticker": "AMD",
        "strike": 150.0,
        "call_put": "C",
        "expiration": "2027-01-15",
        "entry_price": 4.00,
        "flow_id": "amd_unrelated_flow",
    }
    rec_unrelated = paper_intent(rec_unrelated)
    persist_source(temp_db,rec_unrelated)
    trade_unrelated = engine.execute_autonomous_trade(rec_unrelated, account_tier="growing")
    unrelated_holding_id = trade_unrelated["holding_id"]

    # Insert notable_flow row for the monitored trade
    # Research price alone is nonexecutable. Explicit TEST bid evidence follows.
    temp_db.save_notable_flow({
        "flow_id": flow_id,
        "ticker": "AMD",
        "strike": 150.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "dte": 20,
        "entry_contract_price": 4.00,
        "current_contract_price": 5.30,
        "flow_score": 85.0,
        "final_outcome": "MONITORING",
        "premium_usd": 300000.0,
    })

    # Pass 1: Run production monitor_and_update_positions
    from datetime import datetime, timezone, timedelta
    clock = datetime.now(timezone.utc)
    quote = dict(rec['quote'], holding_id=holding_id, quote_id='TEST-monitor-1',
                 bid=5.035, ask=5.30, observed_at=clock.isoformat())
    arm.quote_max_age_seconds = 60
    arm.clock = lambda: clock
    arm.quote_reader = lambda holding: dict(quote)
    updates = arm.monitor_and_update_positions()
    assert any(u["flow_id"] == flow_id and u["outcome"] == "WIN_TP1" for u in updates)

    # Holding must be in TRIMMED status with stop at breakeven ($4.00)
    h_mid = temp_db.get_portfolio_holding(holding_id)
    assert h_mid["status"] == "TRIMMED"
    assert h_mid["target_sl"] == 4.00
    assert h_mid["quantity"] == 1.0

    # Unrelated holding must NOT have been touched!
    h_unrelated = temp_db.get_portfolio_holding(unrelated_holding_id)
    assert h_unrelated["status"] == "OPEN"
    assert h_unrelated["quantity"] == 2.0

    # Pass 2: observed TEST bid is exactly breakeven; never a haircut of mid.
    clock += timedelta(seconds=1)
    quote.update(quote_id='TEST-monitor-2', bid=4.00, ask=4.10, observed_at=clock.isoformat())
    conn = temp_db._get_connection()
    conn.execute("UPDATE notable_flow SET current_contract_price = 4.00 WHERE flow_id = ?", (flow_id,))
    conn.commit()

    # Run production monitor_and_update_positions again
    updates2 = arm.monitor_and_update_positions()
    assert any(u["flow_id"] == flow_id and u["outcome"] == "CLOSED_BREAKEVEN" for u in updates2)

    h_final = temp_db.get_portfolio_holding(holding_id)
    assert h_final["status"] == "CLOSED"
    assert h_final["quantity"] == 0.0

    # Unrelated holding must STILL be open and untouched!
    h_unrelated_final = temp_db.get_portfolio_holding(unrelated_holding_id)
    assert h_unrelated_final["status"] == "OPEN"


def test_p2_concurrent_entry_and_closed_replay(temp_db):
    """
    Finding Review 2: Concurrency & Idempotency.
    1. Concurrent entries with same flow_id must result in exactly 1 holding and correct cash debit.
    2. Resubmitting a flow_id after it has been closed must NOT create a new holding.
    """
    import threading
    from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine

    engine = DualPortfolioEngine(temp_db)
    rec = {
        "ticker": "MSFT",
        "strike": 400.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "entry_price": 4.00,
        "flow_id": "msft_concurrent_flow",
    }

    # Concurrent race: 2 threads attempting to enter same flow_id simultaneously
    from step1_fixtures import paper_intent, persist_source, lifecycle_evidence
    rec = paper_intent(rec)
    persist_source(temp_db,rec)
    results = []
    def _worker():
        eng = DualPortfolioEngine(temp_db)
        res = eng.execute_autonomous_trade(rec, account_tier="growing")
        results.append(res)

    t1 = threading.Thread(target=_worker)
    t2 = threading.Thread(target=_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify only 1 holding was created in the database across history
    conn = temp_db._get_connection()
    cur = conn.execute("SELECT COUNT(*) FROM portfolio_holdings WHERE portfolio_id = 'autonomous_ai' AND flow_id = 'msft_concurrent_flow'")
    row = cur.fetchone()
    assert row[0] == 1, f"Expected exactly 1 holding created under concurrency, got {row[0]}"

    # Verify cash was debited only once (2 contracts * $4.00 * 100 = $800, cash balance $99,200)
    p = temp_db.get_portfolio("autonomous_ai")
    assert p["cash_balance"] == 99200.0

    # Now close the holding
    holding_id = results[0]["holding_id"]
    engine.execute_autonomous_exit(holding_id, current_price=3.00, outcome_label="LOSS_STOP_HIT", **lifecycle_evidence(temp_db,holding_id,3))
    closed_h = temp_db.get_portfolio_holding(holding_id)
    assert closed_h["status"] == "CLOSED"

    # Now resubmit the same closed flow_id: Must NOT create a second holding!
    replay_res = engine.execute_autonomous_trade(rec, account_tier="growing")
    assert replay_res is not None
    assert replay_res["holding_id"] == holding_id

    cur2 = conn.execute("SELECT COUNT(*) FROM portfolio_holdings WHERE portfolio_id = 'autonomous_ai' AND flow_id = 'msft_concurrent_flow'")
    assert cur2.fetchone()[0] == 1, "Replaying a closed flow_id must not create duplicate holdings in history"


# ==============================================================================
# PRIORITY 3: LINEAGE & APPEND-ONLY STRATEGY JOURNALING (L8, F8)
# ==============================================================================

def test_p3_strategy_journal_full_lineage_retention(temp_db):
    """
    Finding L8 / F8: Strategy logger must preserve holding_id, flow_id, entry_price,
    exit_price, quantity, realized_pnl, outcome_label, and full payload append-only without overwrite.
    """
    from plugins.analyst_trader.strategy_logger import log_event

    trace_1 = log_event(
        event_type="autonomous_trade_executed",
        payload={
            "holding_id": "hold_1001",
            "flow_id": "flow_1001",
            "ticker": "MSFT",
            "strategy_name": "A+_DREAM_SETUP",
            "quantity": 2,
            "entry_price": 5.00,
            "realized_pnl": 0.0,
            "outcome_label": "OPEN",
        },
        source="unit_test",
        db_path=str(temp_db.db_path),
    )
    assert trace_1 is not None

    trace_2 = log_event(
        event_type="autonomous_trade_closed",
        payload={
            "holding_id": "hold_1001",
            "flow_id": "flow_1001",
            "parent_trace_id": trace_1,
            "ticker": "MSFT",
            "strategy_name": "A+_DREAM_SETUP",
            "quantity": 2,
            "entry_price": 5.00,
            "exit_price": 6.50,
            "realized_pnl": 300.0,
            "outcome_label": "WIN_TP2",
        },
        source="unit_test",
        db_path=str(temp_db.db_path),
    )
    assert trace_2 is not None
    assert trace_1 != trace_2, "Each event must receive a distinct immutable trace_id"

    # Verify both records exist append-only in SQLite
    events = temp_db.list_recorded_strategies(limit=10)
    assert len(events) == 2
    close_event = next(e for e in events if e.get("event_type") == "autonomous_trade_closed")
    assert close_event.get("realized_pnl") == 300.0
    assert close_event.get("outcome_label") == "WIN_TP2"
    assert close_event.get("holding_id") == "hold_1001"


# ==============================================================================
# PRIORITY 4: ELIMINATE LOOKAHEAD & UNSUPPORTED CLAIMS (L2, L3, L5, F10)
# ==============================================================================

def test_p4_ta_point_in_time_filtering_and_no_lookahead(temp_db):
    """
    Finding L2: Technical indicators must strictly use bars before entry_date (date < entry_date).
    If bars are insufficient or missing, is_above_200_ema must be None/UNKNOWN, not defaulted to True.
    """
    from plugins.analyst_trader.analyst_learning import AnalystLearningEngine

    learner = AnalystLearningEngine(str(temp_db.db_path))

    # Entry date before any historical bars
    mock_bars = [
        {"date": "2026-05-01", "close": 150.0, "volume": 1000000},
        {"date": "2026-05-02", "close": 152.0, "volume": 1100000},
    ]
    with patch.object(learner, "_fetch_cboe_bars", return_value=mock_bars):
        ta = learner._get_ta_at_date(ticker="TEST", date_str="2026-01-01")
        # Must NOT consume future May 2026 bars for January 2026 entry
        assert ta.get("ema_stack_state") == "UNKNOWN" or ta.get("current_price") == 0.0
        # Missing bars must not default is_above_200_ema to True
        assert ta.get("is_above_200_ema") is not True


def test_p4_analyst_edge_sample_gate_and_direction_confluence(temp_db):
    """
    Finding L3 / L5: Analyst edge must require a minimum sample size (e.g. >= 5 closed trades).
    Factor G in flow_classifier must check trade direction (Calls only match Call edge; Puts only match Put edge).
    """
    from flow_classifier import FlowClassifierEngine

    # Create an analyst with only 1 closed trade (insufficient sample)
    conn = temp_db._get_connection()
    conn.execute("""
        INSERT INTO analyst_styles (
            analyst_name, preferred_tickers, win_rate, total_trades, preferred_direction, updated_at
        ) VALUES ('LoneWinner', '["AAPL"]', 100.0, 1, 'CALL', '2026-09-19T00:00:00')
    """)
    conn.commit()

    classifier = FlowClassifierEngine(str(temp_db.db_path))

    # Evaluate an AAPL Call: should NOT receive analyst edge bonus due to sample gate (<5 trades)
    res_call = classifier.classify_and_score_flow(
        ticker="AAPL", strike=220.0, call_put="C", expiration="2026-10-16",
        dte=30, premium_usd=500000.0, spot_price=218.0
    )
    assert not any("ANALYST EDGE: LoneWinner" in t for t in res_call.get("flow_tags", []))

    # Update analyst to 10 trades, but direction CALL only
    conn.execute("""
        UPDATE analyst_styles SET total_trades = 10, preferred_direction = 'CALL' WHERE analyst_name = 'LoneWinner'
    """)
    conn.commit()

    # Evaluate an AAPL PUT: must NOT receive analyst edge bonus from a Call-only analyst!
    res_put = classifier.classify_and_score_flow(
        ticker="AAPL", strike=210.0, call_put="P", expiration="2026-10-16",
        dte=30, premium_usd=500000.0, spot_price=218.0
    )
    assert not any("ANALYST EDGE: LoneWinner" in t for t in res_put.get("flow_tags", []))


def test_p4_free_roll_math_truthfulness():
    """
    Finding F10: Sizing trim schedule must accurately compute capital recovery.
    Trimming 2 of 3 contracts at +25% recovers only 83.3% of outlay, so is_free_roll MUST be False.
    """
    from autonomous_risk_manager import get_contract_trim_schedule

    s3 = get_contract_trim_schedule(quantity=3, tp1_pct=25.0, tp2_pct=50.0)
    assert s3["is_free_roll"] is False, "2 contracts at +25% does not recover 100% of 3-contract outlay"
    assert "83%" in s3.get("action_at_tp1", "") or "De-risks" in s3.get("action_at_tp1", "")


# ==============================================================================
# PRIORITY 5: TRUTHFUL UI & API ERROR STATES (Review 3 P1, F9)
# ==============================================================================

def test_p5_api_portfolio_truthful_error_handling(isolated_env):
    """
    Finding Review 3 P1: API endpoints must NOT conceal database failures by returning
    ok: true with invented $100k balances. On DB failure, it must return HTTP 500 with ok: false / error details.
    """
    from hermes_cli.web_server import app, _SESSION_TOKEN
    from starlette.testclient import TestClient

    # Create a corrupted database file
    corrupt_db_path = isolated_env["hermes_home"] / "data" / "corrupted_test.db"
    corrupt_db_path.write_bytes(b"NOT_A_VALID_SQLITE_DATABASE_CORRUPTED_BYTES")

    client = TestClient(app)
    auth_headers = {"X-Hermes-Session-Token": _SESSION_TOKEN}

    with patch("hermes_cli.web_server._analyst_db_path", return_value=corrupt_db_path):
        resp = client.get("/api/analyst-trader/portfolio", headers=auth_headers)
        assert resp.status_code == 500, f"Expected HTTP 500 on database failure, got {resp.status_code}"
        data = resp.json()
        assert not data.get("ok", False) or "detail" in data
        assert "error" in str(data).lower() or "detail" in str(data).lower()


def test_p5_ui_notable_flow_no_hardcoded_win_rates():
    """
    Finding L4 / F6: NotableFlowPage.tsx must not contain hardcoded win rates (83.3%, 77.8%, etc.).
    Strategy cards must dynamically derive empirical performance from telemetry or show awaiting data.
    """
    page_path = Path(__file__).resolve().parent.parent / "web" / "src" / "pages" / "NotableFlowPage.tsx"
    assert page_path.exists()
    content = page_path.read_text(encoding="utf-8")

    hardcoded_strings = [
        "83.3% Win Rate",
        "77.8% Win Rate",
        "75.0% Win Rate",
        "72.4% Win Rate",
    ]
    for hc in hardcoded_strings:
        assert hc not in content, f"NotableFlowPage.tsx must not contain hardcoded statistic: '{hc}'"
    assert "getStrategyStats" in content, "NotableFlowPage.tsx must compute stats dynamically via getStrategyStats"


# ==============================================================================
# PRIORITY 6: PROFILE ISOLATION & CHART CONFINEMENT (Review 3 P1)
# ==============================================================================

def test_p6_db_path_respects_hermes_home(isolated_env):
    """
    Finding Review 3 P1: get_db_path() must resolve under HERMES_HOME, NOT hardcoded Path.home().
    """
    from plugins.analyst_trader.db import get_db_path

    resolved_path = get_db_path().resolve()
    expected_root = isolated_env["hermes_home"].resolve()
    assert str(resolved_path).startswith(str(expected_root)), f"DB path {resolved_path} must resolve inside HERMES_HOME {expected_root}"


def test_p6_chart_file_serving_strict_confinement(isolated_env, temp_db):
    """
    Finding Review 3 P1: Chart endpoint must be confined to HERMES_HOME/charts.
    Attempting to access ~/.hermes/.env or config.yaml must be rejected with 403.
    Legitimate charts inside charts dir must return HTTP 200.
    """
    from hermes_cli.web_server import app, _SESSION_TOKEN
    from starlette.testclient import TestClient

    client = TestClient(app)
    auth_headers = {"X-Hermes-Session-Token": _SESSION_TOKEN}

    # 1. Valid chart in charts directory
    charts_dir = isolated_env["hermes_home"] / "charts"
    valid_chart = charts_dir / "valid_flow_chart.png"
    valid_chart.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")

    temp_db.save_notable_flow({
        "flow_id": "valid_chart_flow",
        "ticker": "AAPL",
        "strike": 220.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "premium_usd": 500000.0,
        "local_chart_path": str(valid_chart),
    })

    with patch("hermes_cli.web_server._analyst_db_path", return_value=temp_db.db_path):
        resp_valid = client.get("/api/analyst-trader/flow-chart/valid_chart_flow", headers=auth_headers)
        assert resp_valid.status_code == 200, f"Expected 200 for valid chart, got {resp_valid.status_code}"

    # 2. Path traversal / outside file attempt
    env_file = isolated_env["hermes_home"] / ".env"
    env_file.write_text("SECRET_API_KEY=leak_attempt")

    temp_db.save_notable_flow({
        "flow_id": "exploit_chart_leak",
        "ticker": "SPY",
        "strike": 500.0,
        "call_put": "C",
        "expiration": "2026-10-16",
        "premium_usd": 500000.0,
        "local_chart_path": str(env_file),
    })

    with patch("hermes_cli.web_server._analyst_db_path", return_value=temp_db.db_path):
        resp_leak = client.get("/api/analyst-trader/flow-chart/exploit_chart_leak", headers=auth_headers)
        assert resp_leak.status_code == 403, f"Access to .env file via chart endpoint must be rejected with 403, got {resp_leak.status_code}"


def test_p1_reversible_quarantine_script(temp_db):
    """
    Finding F1 / L1: Synthetic and fallback historical records must be reversibly quarantined,
    with zero silent deletions. Applying quarantine flags them; reverting clears the flag.
    """
    from scripts.quarantine_synthetic_data import quarantine_data

    # A contract value alone is not evidence of synthetic provenance.
    temp_db.save_notable_flow({
        'flow_id': 'TEST-valid-contract', 'ticker': 'AAPL', 'strike': 100,
        'call_put': 'C', 'expiration': '2026-10-16', 'premium_usd': 200000,
        'raw_message_id': 'TEST-observed-message',
    })
    from scripts.quarantine_synthetic_data import KNOWN_SCANNER_FIXTURES
    flow_id, (source, timestamp) = next(iter(KNOWN_SCANNER_FIXTURES.items()))
    temp_db.save_notable_flow({
        'flow_id': flow_id, 'ticker': 'TEST', 'strike': 230,
        'call_put': 'C', 'expiration': '2026-10-16', 'premium_usd': 200000,
        'source': source, 'trade_timestamp': timestamp,
    })
    dry = quarantine_data(temp_db.db_path)
    assert dry['notable_flow_to_quarantine'] == 1
    before = temp_db.get_notable_flow(flow_id)
    applied = quarantine_data(temp_db.db_path, apply=True)
    assert applied['notable_flow_quarantined'] == 1
    assert temp_db.get_notable_flow(flow_id)['is_quarantined'] == 1
    assert not temp_db.get_notable_flow('TEST-valid-contract')['is_quarantined']
    with pytest.raises(ValueError):
        quarantine_data(temp_db.db_path, apply=True, revert=True)
    restored = quarantine_data(temp_db.db_path, apply=True, revert=True, batch_id=applied['batch_id'])
    assert restored['status'] == 'success'
    after = temp_db.get_notable_flow(flow_id)
    assert after['is_quarantined'] == before['is_quarantined']
    assert after['quarantine_reason'] == before['quarantine_reason']
