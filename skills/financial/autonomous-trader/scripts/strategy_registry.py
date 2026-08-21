#!/usr/bin/env python3
"""
strategy_registry.py - Strategy Loader, Registry & Schema Manager.
Manages modular strategy definition files in skills/financial/autonomous-trader/strategies/
"""

import os
import json
from datetime import datetime

STRATEGIES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../strategies"))


def get_strategies_dir() -> str:
    os.makedirs(STRATEGIES_DIR, exist_ok=True)
    return STRATEGIES_DIR


def list_strategies() -> list[dict]:
    """Discover and return all active strategy definition files."""
    s_dir = get_strategies_dir()
    strategies = []
    for f in sorted(os.listdir(s_dir)):
        if f.endswith(".json"):
            path = os.path.join(s_dir, f)
            try:
                with open(path, "r") as fp:
                    data = json.load(fp)
                    data["_file_path"] = path
                    strategies.append(data)
            except Exception:
                pass
    return strategies


def load_strategy(strategy_id: str) -> dict | None:
    """Load a specific strategy definition by strategy_id (e.g. GEX_0DTE, VEX_SWING, FLOW_SWEEP)."""
    strategy_id_clean = strategy_id.upper().strip()
    for strat in list_strategies():
        if strat.get("strategy_id", "").upper() == strategy_id_clean:
            return strat
        # Fallback check file name
        base_name = os.path.basename(strat.get("_file_path", "")).lower()
        if strategy_id_clean.lower() in base_name:
            return strat
    return None


def save_strategy(strategy_data: dict) -> bool:
    """Save an updated strategy definition back to disk with updated timestamp."""
    s_id = strategy_data.get("strategy_id")
    if not s_id:
        return False
    path = strategy_data.get("_file_path")
    if not path:
        file_name = f"{s_id.lower()}.json"
        path = os.path.join(get_strategies_dir(), file_name)

    # Remove temporary internal keys before saving
    clean_data = {k: v for k, v in strategy_data.items() if not k.startswith("_")}
    clean_data["last_updated"] = datetime.now().isoformat()

    try:
        with open(path, "w") as fp:
            json.dump(clean_data, fp, indent=2)
        try:
            import trading_store
            trading_store.sync_strategy_to_db(clean_data)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"Error saving strategy {s_id}: {e}")
        return False


def tune_strategy_parameter(strategy_id: str, updates: dict) -> dict | None:
    """Tune parameters on a strategy definition file and save to disk."""
    strat = load_strategy(strategy_id)
    if not strat:
        return None

    for k, v in updates.items():
        if k in ("conviction_threshold", "allocated_capital"):
            strat[k] = type(strat.get(k, v))(v)
        elif k in ("target_price_rule", "stop_loss_rule", "optimization_status"):
            strat[k] = str(v)
        elif k.startswith("weights."):
            w_key = k.split(".", 1)[1]
            if "weights" not in strat:
                strat["weights"] = {}
            strat["weights"][w_key] = float(v)
        elif k.startswith("rules."):
            r_key = k.split(".", 1)[1]
            if "rules" not in strat:
                strat["rules"] = {}
            strat["rules"][r_key] = v
        else:
            strat[k] = v

    if save_strategy(strat):
        return strat
    return None


if __name__ == "__main__":
    print(f"Strategy Registry: Discovered {len(list_strategies())} strategies in {STRATEGIES_DIR}")
    for s in list_strategies():
        print(f"  • [{s.get('strategy_id')}] {s.get('name')} (v{s.get('version')}) - Threshold: {s.get('conviction_threshold')}")
