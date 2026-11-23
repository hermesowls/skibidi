#!/usr/bin/env python3
"""
owlfred_engine.py - Unified Production Control Interface for OWLFRED Autonomous Trader.

Usage:
  python owlfred_engine.py start        # Start 24/7 background supervisor daemon
  python owlfred_engine.py stop         # Stop background supervisor daemon
  python owlfred_engine.py status       # Check daemon status, health, and cache stats
  python owlfred_engine.py eval METC    # Run full Shadow Quant & DREAM eval on a ticker
  python owlfred_engine.py audit-oi     # Run pre-market Delta-OI carryover audit
  python owlfred_engine.py dream        # Run nightly feature correlation lab
"""

import os
import sys
import json
import sqlite3
import subprocess
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
TRADER_SCRIPTS = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TRADER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TRADER_SCRIPTS))

PID_FILE = Path.home() / ".hermes" / "owlfred_supervisor.pid"
SUPERVISOR_SCRIPT = TRADER_SCRIPTS / "owlfred_supervisor.py"
PYTHON_BIN = PROJECT_ROOT / "venv" / "bin" / "python"
if not PYTHON_BIN.exists():
    PYTHON_BIN = Path(sys.executable)


def start_daemon():
    """Starts the 24/7 supervisor daemon in the background."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            print(f"⚠️ OWLFRED Supervisor is already running (PID: {pid}).")
            return
        except OSError:
            PID_FILE.unlink(missing_ok=True)

    cmd = [str(PYTHON_BIN), str(SUPERVISOR_SCRIPT)]
    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"🚀 OWLFRED Master Production Supervisor started in background (PID: {proc.pid}).")
    print(f"📝 Telemetry logs available at: ~/.hermes/logs/owlfred_supervisor.log")


def stop_daemon():
    """Stops the supervisor daemon gracefully."""
    if not PID_FILE.exists():
        print("ℹ️ OWLFRED Supervisor is not running.")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 15)  # SIGTERM
        print(f"🛑 Sent graceful termination signal to OWLFRED Supervisor (PID: {pid}).")
        PID_FILE.unlink(missing_ok=True)
    except Exception as e:
        print(f"Error stopping process: {e}")
        PID_FILE.unlink(missing_ok=True)


def check_status():
    """Checks health, process status, and storage metrics."""
    print("\n=======================================================")
    print("📊 OWLFRED PRODUCTION ENGINE SYSTEM STATUS")
    print("=======================================================")
    
    # Process check
    is_running = False
    pid_str = "OFFLINE"
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            is_running = True
            pid_str = f"ONLINE (PID: {pid})"
        except OSError:
            PID_FILE.unlink(missing_ok=True)

    print(f"Supervisor Daemon:       {pid_str}")

    # Database & Storage Check
    from plugins.analyst_trader.db import get_db_path
    db_path = get_db_path()
    cache_db = Path("/Volumes/Macintosh 1 TB HD/hermes_storage/quant_cache/quant_historical_profiles.db")
    
    flow_count = 0
    cached_profiles = 0
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM notable_flow")
            flow_count = cur.fetchone()[0]
            conn.close()
        except Exception:
            pass

    if cache_db.exists():
        try:
            conn = sqlite3.connect(str(cache_db))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ticker_quant_profiles")
            cached_profiles = cur.fetchone()[0]
            conn.close()
        except Exception:
            pass

    print(f"Notable Flow Candidates: {flow_count} records in SQLite")
    print(f"1 TB HD Quant Cache:     {cached_profiles} ticker profiles stored on SATA disk")
    print(f"Storage Path:            {cache_db}")
    print("=======================================================\n")


def eval_ticker(ticker: str, *, db_path=None, flow_id=None, publication=None,
                delivery_transport=None, delivery_destinations=(), delivery_clock=None,
                quant_engine=None, deep_dive_analyzer=None, observation_reader=None,
                learning_context=None, execution_decision=None, research_context=None):
    """Evaluate an explicitly selected persisted source, never an invented ATM trade.

    Publication is a caller's separate policy decision, not permission inferred
    from a ticker or constructor. Bare CLI evaluation remains fail-closed.
    """
    denied = dict(alert_published=False, paper_trade=None,
                  alert_delivery=dict(status='denied', units=[], reason='Explicit source and publication decision required'))
    if (not db_path or not flow_id or not isinstance(publication, dict)
            or (publication.get('publishing_authorized') is not True and research_context is None)
            or publication.get('flow_id') != flow_id):
        return denied
    from plugins.analyst_trader.db import AnalystDatabase
    from plugins.analyst_trader.execution_contract import number
    from datetime import date, datetime, timezone
    db = AnalystDatabase(Path(db_path))
    with db._get_connection() as c:
        row = c.execute('SELECT * FROM notable_flow WHERE flow_id=?', (flow_id,)).fetchone()
        if (row is None or row['ticker'] != ticker or row['is_quarantined'] not in (None, 0)
                or row['final_outcome'] != 'MONITORING'
                or c.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND COALESCE(is_quarantined,0)!=0', (flow_id,)).fetchone()):
            return denied
        source = dict(row)
    try:
        entry = number(source.get('entry_contract_price'), 'observed entry')
        premium = number(source.get('premium_usd'), 'observed premium')
        observations = observation_reader(dict(source)) if observation_reader else {}
        spot = number(observations.get('spot_price'), 'observed underlying spot')
        today = datetime.fromtimestamp(delivery_clock(), timezone.utc).date() if delivery_clock else date.today()
        dte = (date.fromisoformat(source['expiration']) - today).days
    except (ValueError, TypeError):
        return denied
    from autonomous_risk_manager import AutonomousRiskManager
    if learning_context is not None and learning_context.get('source_id') != flow_id:
        raise ValueError('Learning/source identity mismatch')
    if execution_decision is not None and execution_decision.get('flow_id') != flow_id:
        raise ValueError('Execution/source identity mismatch')
    mgr = AutonomousRiskManager(str(db.db_path), delivery_transport=delivery_transport,
        delivery_destinations=delivery_destinations, delivery_clock=delivery_clock,
        quant_engine=quant_engine, deep_dive_analyzer=deep_dive_analyzer)
    return mgr.evaluate_candidate_end_to_end(
        ticker=source['ticker'], strike=source['strike'], call_put=source['call_put'],
        expiration=source['expiration'], dte=dte, premium_usd=premium, entry_price=entry,
        spot_price=spot, auto_publish_alerts=True, image_path=None, publication=publication,
        learning_context=learning_context, execution_decision=execution_decision,
        research_context=research_context)


def resume_publication(publication, *, db_path, delivery_transport=None,
                       delivery_destinations=(), delivery_clock=None, limit=100):
    """Bounded delivery-only resume; no enrichment, new decisions or paper orders."""
    import time
    from plugins.analyst_trader.alert_delivery import AlertOutbox
    return AlertOutbox(db_path, clock=delivery_clock or time.time).resume(
        publication, tuple(delivery_destinations), delivery_transport, limit=limit)


def audit_oi():
    """Runs pre-market OI carryover audit."""
    from premarket_oi_auditor import PremarketOIAuditor
    auditor = PremarketOIAuditor()
    res = auditor.run_premarket_oi_audit()
    print("\n" + "="*50)
    print("🌅 PRE-MARKET ΔOI AUDIT REPORT")
    print("="*50)
    print(f"Total Candidates:   {res['total_audited']}")
    print(f"Carryover Confirmed:{res['carryover_confirmed']}")
    print(f"Single-Day Churn:   {res['single_day_churn']}")
    print("="*50 + "\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    if cmd == "start":
        start_daemon()
    elif cmd == "stop":
        stop_daemon()
    elif cmd == "status":
        check_status()
    elif cmd == "eval" and len(sys.argv) > 2:
        eval_ticker(sys.argv[2])
    elif cmd == "audit-oi":
        audit_oi()
    elif cmd == "dream":
        from candidate_correlation_engine import CandidateCorrelationEngine
        engine = CandidateCorrelationEngine()
        engine.run_full_candidate_correlation_audit()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
