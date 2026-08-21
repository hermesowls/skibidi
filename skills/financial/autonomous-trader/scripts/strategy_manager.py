#!/usr/bin/env python3
"""
strategy_manager.py - Strategy Parameter Manager & Tuning CLI.
Allows users and automated learning loops to view, tune, or auto-optimize strategy parameters.
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Path setup for strategy_registry & learning DB
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import strategy_registry

LEARNING_DB_PATH = os.path.expanduser("~/.hermes/trading_learning_db.json")


def load_json(path, default_val):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default_val


def cmd_list():
    strats = strategy_registry.list_strategies()
    print("\n📋 ==================== ACTIVE STRATEGY REGISTRY ====================")
    print(f"Directory: {strategy_registry.get_strategies_dir()}\n")

    for s in strats:
        print(f"🔹 Strategy ID   : {s.get('strategy_id')}")
        print(f"   Name          : {s.get('name')} (v{s.get('version')})")
        print(f"   Horizon       : {s.get('horizon')} | Risk: {s.get('risk_profile')}")
        print(f"   Conviction Gate: {s.get('conviction_threshold')}/100 | Capital: ${s.get('allocated_capital',0):,.2f}")
        print(f"   Target Rule   : {s.get('target_price_rule')} | Stop Loss: {s.get('stop_loss_rule')}")
        print(f"   Weights       : {s.get('weights')}")
        print(f"   Status        : {s.get('optimization_status')}")
        print(f"   File          : {s.get('_file_path')}\n")

    print("====================================================================\n")


def cmd_show(strategy_id: str):
    strat = strategy_registry.load_strategy(strategy_id)
    if not strat:
        print(f"❌ Strategy '{strategy_id}' not found in registry.")
        sys.exit(1)
    clean_strat = {k: v for k, v in strat.items() if not k.startswith("_")}
    print(json.dumps(clean_strat, indent=2))


def cmd_tune(strategy_id: str, updates: dict):
    strat = strategy_registry.tune_strategy_parameter(strategy_id, updates)
    if not strat:
        print(f"❌ Failed to tune strategy '{strategy_id}'. Check ID and parameter names.")
        sys.exit(1)

    print(f"✅ Strategy '{strat.get('strategy_id')}' successfully updated and saved!")
    print(f"   New Threshold  : {strat.get('conviction_threshold')}")
    print(f"   New Capital    : ${strat.get('allocated_capital',0):,.2f}")
    print(f"   New Target Rule: {strat.get('target_price_rule')}")
    print(f"   New Stop Rule  : {strat.get('stop_loss_rule')}")
    print(f"   File Location  : {strat.get('_file_path')}")


def cmd_auto_optimize():
    learning_db = load_json(LEARNING_DB_PATH, {})
    strats = strategy_registry.list_strategies()
    print("\n🧠 Running Strategy Learning Auto-Optimizer...\n")

    updated_count = 0
    for strat in strats:
        s_id = strat.get("strategy_id")
        history = learning_db.get(s_id, {})
        total = history.get("total_trades", 0)
        wins = history.get("wins", 0)
        win_rate = (wins / total * 100) if total > 0 else 75.0

        updates = {}
        if win_rate >= 80.0 and total >= 3:
            updates["optimization_status"] = f"🔥 Excellent Win Rate ({win_rate:.1f}%). Sizing increased +15%."
            updates["allocated_capital"] = round(strat.get("allocated_capital", 200) * 1.15, 2)
            updated_count += 1
        elif win_rate < 50.0 and total >= 3:
            updates["optimization_status"] = f"🛡️ Sub-optimal Win Rate ({win_rate:.1f}%). Conviction threshold tightened to 85."
            updates["conviction_threshold"] = 85
            updated_count += 1
        else:
            updates["optimization_status"] = f"Active ({win_rate:.1f}% Win Rate across {total} trades)"

        if updates:
            strategy_registry.tune_strategy_parameter(s_id, updates)
            print(f"   • Updated {s_id}: {updates['optimization_status']}")

    print(f"\nAuto-Optimization Complete. Updated {updated_count} strategy definition files.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strategy Parameter Manager & Tuning CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all registered strategies and parameter values.")

    # show
    show_p = subparsers.add_parser("show", help="Show detailed JSON definition for a strategy.")
    show_p.add_argument("--strategy", required=True, help="Strategy ID (e.g. GEX_0DTE, VEX_SWING, FLOW_SWEEP)")

    # tune
    tune_p = subparsers.add_parser("tune", help="Tune parameter values on a strategy.")
    tune_p.add_argument("--strategy", required=True, help="Strategy ID to tune.")
    tune_p.add_argument("--threshold", type=int, help="New conviction threshold (0 - 100).")
    tune_p.add_argument("--capital", type=float, help="New allocated capital per trade.")
    tune_p.add_argument("--target", type=str, help="New target price rule description.")
    tune_p.add_argument("--stop-loss", type=str, help="New stop loss rule description.")

    # auto-optimize
    subparsers.add_parser("auto-optimize", help="Auto-tune strategy parameters based on Learning DB performance.")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "show":
        cmd_show(args.strategy)
    elif args.command == "tune":
        updates = {}
        if args.threshold is not None: updates["conviction_threshold"] = args.threshold
        if args.capital is not None: updates["allocated_capital"] = args.capital
        if args.target: updates["target_price_rule"] = args.target
        if args.stop_loss: updates["stop_loss_rule"] = args.stop_loss
        cmd_tune(args.strategy, updates)
    elif args.command == "auto-optimize":
        cmd_auto_optimize()
