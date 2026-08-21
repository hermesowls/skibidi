#!/usr/bin/env python3
"""
strategy_watchdog.py - Real-Time Financial Strategy & Action Watchdog Monitor.
Monitors Hermes background workflows, signal evaluations, trigger gate decisions,
modular strategy parameters, and Alpaca paper trading executions.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

# Path setup for sibling strategy_registry
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    import strategy_registry
except ImportError:
    strategy_registry = None

JOURNAL_PATH = os.path.expanduser("~/.hermes/paper_trading_journal.json")
LEARNING_DB_PATH = os.path.expanduser("~/.hermes/trading_learning_db.json")
PORTFOLIOS_DB_PATH = os.path.expanduser("~/.hermes/strategy_portfolios_db.json")


def load_json(path, default_val):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default_val


def fmt_card(event: dict) -> str:
    """Format a strategy or trading event into a human-readable visual card."""
    ts = event.get("timestamp", datetime.now().isoformat())[:19].replace("T", " ")
    evt_type = event.get("event_type", event.get("action", "STRATEGY_EVENT")).upper()
    ticker = event.get("ticker", "SYS")
    mode = event.get("mode", "VEX")
    score = event.get("conviction_score", "N/A")
    action = event.get("action", "N/A")
    alloc = event.get("allocated_capital", 0.0)
    status = event.get("status", "OPEN")
    fz = event.get("finviz_metrics", {})
    price = fz.get("price", "N/A")
    chg = fz.get("change_pct", "N/A")
    sma50 = fz.get("sma50", "N/A")
    sma200 = fz.get("sma200", "N/A")
    sympathy = ", ".join(event.get("sympathy_nodes", [])) if event.get("sympathy_nodes") else "None"
    synthesis = event.get("synthesis", "No synthesis log.")

    card = [
        f"┌── 🛡️  [WATCHDOG EVENT LOG] ──────────────────────────────────────────┐",
        f"│ Timestamp      : {ts}",
        f"│ Event Type     : {evt_type}",
        f"│ Target Ticker  : {ticker} | Price: ${price} ({chg})",
        f"│ Strategy Mode  : {mode} | Conviction Score: {score}/100",
        f"│ Action Taken   : {action} (Capital: ${alloc:,.2f})",
        f"│ Moving Averages: SMA50: {sma50} | SMA200: {sma200}",
        f"│ Sympathy Nodes : {sympathy}",
        f"│ Status         : {status}",
        f"│ Synthesis      : {synthesis[:80]}...",
        f"└────────────────────────────────────────────────────────────────────┘",
    ]
    return "\n".join(card)


def render_summary():
    journal = load_json(JOURNAL_PATH, {"trades": [], "active_positions": {}})
    portfolios = load_json(PORTFOLIOS_DB_PATH, {})
    learning_db = load_json(LEARNING_DB_PATH, {})

    print("\n🔍 ==================== FINANCIAL WATCHDOG SYSTEM SUMMARY ====================")
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S PST')}\n")

    # 1. Registered Modular Strategy Definitions
    print("📁 REGISTERED MODULAR STRATEGIES (strategies/*.json):")
    if strategy_registry:
        strats = strategy_registry.list_strategies()
        for s in strats:
            print(f"   • [{s.get('strategy_id')}] {s.get('name')} (v{s.get('version')})")
            print(f"     Conviction Gate: {s.get('conviction_threshold')}/100 | Capital: ${s.get('allocated_capital',0):,.2f}")
            print(f"     Target Rule    : {s.get('target_price_rule')} | Stop Loss: {s.get('stop_loss_rule')}")
            print(f"     Status         : {s.get('optimization_status')}")
    else:
        print("   (Strategy registry unavailable)")

    # 2. Portfolios Overview
    print("\n📊 STRATEGY PORTFOLIOS OVERVIEW:")
    if not portfolios:
        print("   (No portfolios initialized yet)")
    for p_key, p in portfolios.items():
        total_val = p.get("cash_balance", 0) + sum(pos.get("allocated_capital", 0) for pos in p.get("positions", {}).values())
        print(f"   • {p.get('name', p_key)}")
        print(f"     Cash: ${p.get('cash_balance',0):,.2f} | Realized P/L: ${p.get('realized_pl',0):+,.2f} | Win Rate: {p.get('win_rate',0):.1f}%")
        print(f"     Active Positions: {len(p.get('positions', {}))} | Optimization: {p.get('continuous_optimization','Active')}")

    # 3. Active Positions
    active_pos = journal.get("active_positions", {})
    print(f"\n⚡ ACTIVE POSITIONS TRACKER ({len(active_pos)} open):")
    if not active_pos:
        print("   (No open paper positions)")
    for pos_key, pos in active_pos.items():
        ticker = pos.get("ticker", pos_key)
        fz = pos.get("finviz_metrics", {})
        print(f"   • {ticker} | Mode: {pos.get('mode')} | Score: {pos.get('conviction_score')}/100 | Capital: ${pos.get('allocated_capital',0):,.2f}")
        print(f"     Price: ${fz.get('price','N/A')} ({fz.get('change_pct','N/A')}) | Target: {pos.get('target_price')} | Stop: {pos.get('stop_loss')}")

    # 4. Strategy Learning Lessons
    print("\n🧠 STRATEGY LEARNING & CONTINUOUS OPTIMIZATION:")
    for strat, data in learning_db.items():
        if isinstance(data, dict) and "total_trades" in data:
            print(f"   • {strat}: {data.get('wins',0)} Wins / {data.get('losses',0)} Losses (Total: {data.get('total_trades',0)})")
            for lesson in data.get("lessons", [])[-3:]:
                print(f"     - Lesson: {lesson}")

    # 5. Recent Journal Executions
    trades = journal.get("trades", [])
    print(f"\n📜 RECENT EXECUTIONS ({len(trades)} logged):")
    for tr in trades[-3:]:
        print(fmt_card(tr))
        print()

    print("============================================================================\n")


def follow_mode(interval=2.0):
    print(f"🛡️  FINANCIAL WATCHDOG TAIL MODE ACTIVE (Polling interval: {interval}s). Press Ctrl+C to exit.\n")
    seen_ids = set()

    journal = load_json(JOURNAL_PATH, {"trades": []})
    for tr in journal.get("trades", []):
        seen_ids.add(tr.get("timestamp") or str(tr.get("order_id")))

    try:
        while True:
            time.sleep(interval)
            journal = load_json(JOURNAL_PATH, {"trades": []})
            trades = journal.get("trades", [])
            for tr in trades:
                tr_id = tr.get("timestamp") or str(tr.get("order_id"))
                if tr_id not in seen_ids:
                    seen_ids.add(tr_id)
                    print(fmt_card(tr))
                    print()
    except KeyboardInterrupt:
        print("\n👋 Financial Watchdog tail mode stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-Time Financial Strategy & Action Watchdog Monitor")
    parser.add_argument("--summary", action="store_true", help="Print system summary and exit.")
    parser.add_argument("--follow", action="store_true", help="Continuously tail and display live events.")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds for --follow mode.")
    args = parser.parse_args()

    if args.follow:
        follow_mode(args.interval)
    else:
        render_summary()
